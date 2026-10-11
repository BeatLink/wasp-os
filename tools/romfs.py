#!/usr/bin/env python3

# SPDX-License-Identifier: LGPL-3.0-or-later

"""Build a ROMFS image and write it to the watch's internal flash.

The firmware mounts the image at /rom, ahead of the frozen modules, so a module
in it replaces the frozen one of the same name. Its bytecode runs straight from
flash and costs no heap, unlike a .mpy copied to /flash. A package directory in
the image replaces the whole frozen package, not just the files it holds.

The PineTime keeps most of wasp-os in the image, as manifest_romfs.py lists, so
the build puts one in its firmware package and push replaces it on its own.
Push sends the image to /flash with the package manager's raw transfer, then
the frozen romwriter copies it into the partition and resets the watch. On a
watch without a working image, such as one booted in safe mode by holding the
button, push falls back to writing the partition line by line over the REPL,
which is much slower.
"""

import argparse
import binascii
import importlib.util
import os
import sys
import tempfile

TOOLS_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(TOOLS_DIR)

# Bytes per write on the slow path, which keeps a command line inside the radio's receive buffer.
CHUNK_SIZE = 64

# How often to collect garbage while writing on the slow path.
COLLECT_EVERY = 8

# The nRF52's flash page, the smallest piece that can be erased.
PAGE_SIZE = 4096

# What the firmware's prepare command returns: flash takes a word at a time.
MIN_WRITE = 4

# Where the image waits on /flash before romwriter copies it.
STAGING = 'romfs.img'

# Stop the system tick, since code loaded from /rom must not run while the partition changes.
STOP_TICK = 'import watch; watch.schedule = watch.nop'

UNMOUNT = 'exec("try:\\n vfs.umount(\'/rom\')\\nexcept OSError:\\n pass")'


def load_writer():
    """Import MicroPython's ROMFS image writer without the rest of mpremote."""
    path = os.path.join(ROOT_DIR, 'micropython', 'tools', 'mpremote', 'mpremote', 'romfs.py')
    spec = importlib.util.spec_from_file_location('mpremote_romfs', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.VfsRomWriter


def tree_of_directory(source_dir):
    """Map every file under a directory to its path, nesting a dict per subdirectory."""
    tree = {}
    for name in sorted(os.listdir(source_dir)):
        path = os.path.join(source_dir, name)
        if name.startswith('.') or name == '__pycache__':
            continue
        tree[name] = tree_of_directory(path) if os.path.isdir(path) else path
    return tree


def tree_of_files(root, files):
    """Map a list of paths relative to root into the same nested form."""
    tree = {}
    for relative in files:
        node = tree
        parts = relative.split('/')
        for part in parts[:-1]:
            node = node.setdefault(part, {})
        node[parts[-1]] = os.path.join(root, relative)
    return tree


def add_tree(writer, tree, compile_py, prefix=''):
    """Add a tree's files to the image, compiling each .py on the way."""
    for name in sorted(tree):
        entry = tree[name]
        if isinstance(entry, dict):
            writer.opendir(name)
            add_tree(writer, entry, compile_py, prefix + name + '/')
            writer.closedir()
        elif name.endswith('.py'):
            writer.mkfile(name[:-3] + '.mpy', compile_py(entry, prefix + name))
        else:
            with open(entry, 'rb') as handle:
                writer.mkfile(name, handle.read())


def build_image(source_dir, compile_py, files=None):
    """Return the ROMFS image of a directory, or of the listed files under it, compiling .py with compile_py."""
    tree = tree_of_directory(source_dir) if files is None else tree_of_files(source_dir, files)
    writer = load_writer()()
    add_tree(writer, tree, compile_py)
    return writer.finalise()


def manifest_files(path):
    """Read the image list from a board's manifest_romfs.py."""
    board_dir = os.path.dirname(os.path.abspath(path))
    sys.path[:0] = [board_dir, os.path.dirname(board_dir)]
    spec = importlib.util.spec_from_file_location('manifest_romfs', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.image


def mpy_compiler(mpy_cross, opt):
    """Return a function compiling one .py file to .mpy bytes for the watch.

    The .mpy records the path inside the image as its source name, as a frozen
    module does, rather than wherever the build happened to find the file.
    """
    sys.path.insert(0, TOOLS_DIR)
    import mkpkg
    flags = mkpkg.detect_flags(mpy_cross) + [f'-O{opt}']

    def compile_py(source, name):
        with tempfile.TemporaryDirectory() as scratch:
            target = os.path.join(scratch, 'module.mpy')
            mkpkg.compile_module(mpy_cross, flags + ['-s', name], source, target)
            with open(target, 'rb') as handle:
                return handle.read()
    return compile_py


def merge_hex(firmware_hex, image, address, size, output):
    """Write the firmware with the image placed at the partition, for a firmware package."""
    from intelhex import IntelHex
    if len(image) > size:
        raise SystemExit(f'the image is {len(image)} bytes and the partition {size}')
    merged = IntelHex(firmware_hex)
    if merged.maxaddr() >= address:
        raise SystemExit(f'the firmware ends at {merged.maxaddr():#x}, inside the partition at {address:#x}')
    rom = IntelHex()
    rom.frombytes(image, offset=address)
    merged.merge(rom, overlap='error')
    merged.write_hex_file(output)


def page_span(length):
    """Round a length up to whole flash pages."""
    return (length + PAGE_SIZE - 1) // PAGE_SIZE * PAGE_SIZE


def expect(session, line, wanted, timeout=20):
    """Run one line and check what it printed."""
    out = session.cmd(line, timeout)
    if out != wanted:
        raise RuntimeError(f'{line!r} printed {out!r}, wanted {wanted!r}')


def write_image(session, image, progress=None):
    """Erase the partition as far as the image reaches and write the image there, a line at a time."""
    session.cmd('import vfs, gc, ubinascii')
    session.cmd(STOP_TICK)
    size = int(session.cmd('len(vfs.rom_ioctl(2, 0))'))
    if len(image) > size:
        raise RuntimeError(f'the image is {len(image)} bytes and the partition {size}')
    session.cmd(UNMOUNT)

    expect(session, f'vfs.rom_ioctl(3, 0, 0, {page_span(max(len(image), 1))})', str(MIN_WRITE), 60)
    session.cmd('w = lambda o, d: vfs.rom_ioctl(4, 0, o, ubinascii.a2b_base64(d))')
    for index, offset in enumerate(range(0, len(image), CHUNK_SIZE)):
        encoded = binascii.b2a_base64(image[offset:offset + CHUNK_SIZE]).strip()
        expect(session, f'w({offset}, {encoded!r})', '0')
        if index % COLLECT_EVERY == COLLECT_EVERY - 1:
            session.cmd('gc.collect()')
        if progress:
            progress(min(offset + CHUNK_SIZE, len(image)), len(image))
    session.cmd('del w')

    expect(session, f'sum(memoryview(vfs.rom_ioctl(2, 0))[:{len(image)}])', str(sum(image)), 60)
    expect(session, 'vfs.rom_ioctl(5, 0)', '0')


def send_raw(session, path, data, window, progress=None):
    """Send a file to the package manager in raw windows and check the sum it reports."""
    from pkgpush import read_reply
    session.buffer = ''
    session.write(f'pkg.recv({path!r}, {len(data)})\r\n')
    start = read_reply(session)
    if not start.get('ok') or start.get('rx') != len(data):
        raise RuntimeError(f'the watch refused the transfer: {start}')
    for at in range(0, len(data), window):
        end = min(at + window, len(data))
        session.write(data[at:end])
        ack = read_reply(session)
        if ack.get('ack') != end:
            raise RuntimeError(f'wanted an ack for {end} bytes, got {ack}')
        if progress:
            progress(end, len(data))
    done = read_reply(session)
    if not done.get('ok') or done.get('sum') != sum(data) & 0xffffffff:
        raise RuntimeError(f'the transfer failed: {done}')
    session.expect_prompt(20)


def install_image(session, image, progress=None):
    """Stage the image on /flash and have romwriter copy it in; return False if the package manager is missing."""
    from pkgpush import call, read_reply
    if 'Error' in session.cmd('import pkgmgr as pkg'):
        return False
    abi = call(session, 'pkg.abi()')['abi']
    if not abi.get('raw'):
        return False
    send_raw(session, STAGING, image, abi['window'], progress)
    session.buffer = ''
    session.write(f'import romwriter; romwriter.install({STAGING!r})\r\n')
    reply = read_reply(session, timeout=60)
    if not reply.get('ok'):
        raise RuntimeError(f'romwriter failed: {reply}')
    return True


def erase_image(session):
    """Erase the first page, which holds the header, so nothing mounts at /rom."""
    session.cmd('import vfs')
    session.cmd(STOP_TICK)
    session.cmd(UNMOUNT)
    expect(session, f'vfs.rom_ioctl(3, 0, 0, {PAGE_SIZE})', str(MIN_WRITE), 60)


def read_or_build(source, args):
    """Read an image file, or build one from a directory."""
    if os.path.isdir(source):
        sys.path.insert(0, TOOLS_DIR)
        import mkpkg
        compile_py = mpy_compiler(mkpkg.find_mpy_cross(args.mpy_cross), args.opt)
        files = manifest_files(args.manifest) if args.manifest else None
        return build_image(source, compile_py, files)
    with open(source, 'rb') as handle:
        image = handle.read()
    if not image.startswith(load_writer().ROMFS_HEADER):
        raise SystemExit(f'{source} is not a ROMFS image')
    return image


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest='command', required=True)

    build = sub.add_parser('build', help='Build an image from a directory')
    build.add_argument('source', help='Directory to build the image from')
    build.add_argument('-o', '--output', required=True, help='Image file to write')

    merge = sub.add_parser('hex', help='Merge an image into a firmware hex at the partition')
    merge.add_argument('firmware', help='The firmware hex')
    merge.add_argument('image', help='The image file')
    merge.add_argument('--address', required=True, type=lambda x: int(x, 0),
                       help='Where the partition starts')
    merge.add_argument('--size', required=True, type=lambda x: int(x, 0),
                       help='How big the partition is')
    merge.add_argument('-o', '--output', required=True, help='Hex file to write')

    push = sub.add_parser('push', help='Write an image, or a directory built into one, to the watch')
    push.add_argument('source', help='Image file or directory')
    push.add_argument('--slow', action='store_true',
                      help='Write over the REPL without the package manager, as in safe mode')

    erase = sub.add_parser('erase', help='Remove the image from the watch')

    for command in (build, push):
        command.add_argument('--manifest',
                             help='A manifest_romfs.py whose image list picks the files under the directory')
        command.add_argument('--mpy-cross', help='The mpy-cross to compile with')
        command.add_argument('--opt', type=int, default=3,
                             help='Optimisation level, 3 like the frozen modules')
    for command in (push, erase):
        command.add_argument('--address', required=True, help='The watch Bluetooth address')
        command.add_argument('--adapter', default='hci0', help='Which local adapter to use')
        command.add_argument('--address-type', default='random', choices=('random', 'public'))
        command.add_argument('--no-reboot', action='store_true',
                             help='Skip the soft reboot that frees the heap first')
        command.add_argument('--verbose', action='store_true')
    args = parser.parse_args()

    if args.command == 'build':
        image = read_or_build(args.source, args)
        with open(args.output, 'wb') as handle:
            handle.write(image)
        print(f'{args.output}: {len(image)} bytes')
        return

    if args.command == 'hex':
        with open(args.image, 'rb') as handle:
            image = handle.read()
        merge_hex(args.firmware, image, args.address, args.size, args.output)
        print(f'{args.output}: {len(image)} byte image at {args.address:#x}')
        return

    image = read_or_build(args.source, args) if args.command == 'push' else None
    if image is not None:
        print(f'image: {len(image)} bytes')

    sys.path.insert(0, TOOLS_DIR)
    from nus import connect, reboot
    options = {
        'adapter': args.adapter,
        'address_type': args.address_type,
        'verbose': args.verbose,
    }

    def progress(done, total):
        print(f'\r{done}/{total} bytes', end='', flush=True)

    session = (connect if args.no_reboot else reboot)(args.address, **options)
    try:
        if image is None:
            erase_image(session)
        elif not args.slow and install_image(session, image, progress):
            print()
            print('done; the watch is restarting')
            return
        else:
            if not args.slow:
                print('no package manager on the watch, writing over the REPL instead')
            write_image(session, image, progress)
            print()
        # A soft reboot mounts the new image and restarts the system tick.
        session.write('\x04')
        session.pump(2.0)
    finally:
        session.close()
    print('done; the watch is restarting')


if __name__ == '__main__':
    main()
