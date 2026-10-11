#!/usr/bin/env python3

# SPDX-License-Identifier: LGPL-3.0-or-later

"""Build a ROMFS image and write it to the watch's internal flash.

The firmware mounts the image at /rom, ahead of the frozen modules, so a module
in it replaces the frozen one of the same name. Its bytecode runs straight from
flash and costs no heap, unlike a .mpy copied to /flash. A package directory in
the image replaces the whole frozen package, not just the files it holds.

Writing goes over the REPL with gatttool, the same transport as nus.py. Code
running from /rom must not run while its flash is rewritten, so the tool stops
the system tick first and soft reboots the watch afterwards. Hold the button
while the watch boots to start it without /rom.
"""

import argparse
import binascii
import importlib.util
import os
import sys
import tempfile

TOOLS_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(TOOLS_DIR)

# Bytes per write, which keeps a command line inside the radio's receive buffer.
CHUNK_SIZE = 64

# How often to collect garbage while writing.
COLLECT_EVERY = 8

# The nRF52's flash page, the smallest piece that can be erased.
PAGE_SIZE = 4096

# What the firmware's prepare command returns: flash takes a word at a time.
MIN_WRITE = 4


def load_writer():
    """Import MicroPython's ROMFS image writer without the rest of mpremote."""
    path = os.path.join(ROOT_DIR, 'micropython', 'tools', 'mpremote', 'mpremote', 'romfs.py')
    spec = importlib.util.spec_from_file_location('mpremote_romfs', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.VfsRomWriter


def add_directory(writer, source_dir, compile_py):
    """Add a directory's files to the image, compiling each .py on the way."""
    for name in sorted(os.listdir(source_dir)):
        path = os.path.join(source_dir, name)
        if name.startswith('.') or name == '__pycache__':
            continue
        if os.path.isdir(path):
            writer.opendir(name)
            add_directory(writer, path, compile_py)
            writer.closedir()
        elif name.endswith('.py'):
            writer.mkfile(name[:-3] + '.mpy', compile_py(path))
        else:
            with open(path, 'rb') as handle:
                writer.mkfile(name, handle.read())


def build_image(source_dir, compile_py):
    """Return the ROMFS image of a directory, its .py files compiled with compile_py."""
    writer = load_writer()()
    add_directory(writer, source_dir, compile_py)
    return writer.finalise()


def mpy_compiler(mpy_cross, opt):
    """Return a function compiling one .py file to .mpy bytes for the watch."""
    sys.path.insert(0, TOOLS_DIR)
    import mkpkg
    flags = mkpkg.detect_flags(mpy_cross) + [f'-O{opt}']

    def compile_py(source):
        with tempfile.TemporaryDirectory() as scratch:
            target = os.path.join(scratch, 'module.mpy')
            mkpkg.compile_module(mpy_cross, flags, source, target)
            with open(target, 'rb') as handle:
                return handle.read()
    return compile_py


def page_span(length):
    """Round a length up to whole flash pages."""
    return (length + PAGE_SIZE - 1) // PAGE_SIZE * PAGE_SIZE


def expect(session, line, wanted, timeout=20):
    """Run one line and check what it printed."""
    out = session.cmd(line, timeout)
    if out != wanted:
        raise RuntimeError(f'{line!r} printed {out!r}, wanted {wanted!r}')


def write_image(session, image, progress=None):
    """Erase the partition as far as the image reaches and write the image there."""
    session.cmd('import wasp, vfs, gc, ubinascii')
    # Code loaded from /rom points into the flash about to change, so nothing may run it.
    session.cmd('wasp.system.schedule(False)')
    size = int(session.cmd('len(vfs.rom_ioctl(2, 0))'))
    if len(image) > size:
        raise RuntimeError(f'the image is {len(image)} bytes and the partition {size}')
    session.cmd('exec("try:\\n vfs.umount(\'/rom\')\\nexcept OSError:\\n pass")')

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


def erase_image(session):
    """Erase the first page, which holds the header, so nothing mounts at /rom."""
    session.cmd('import wasp, vfs')
    session.cmd('wasp.system.schedule(False)')
    session.cmd('exec("try:\\n vfs.umount(\'/rom\')\\nexcept OSError:\\n pass")')
    expect(session, f'vfs.rom_ioctl(3, 0, 0, {PAGE_SIZE})', str(MIN_WRITE), 60)


def read_or_build(source, args):
    """Read an image file, or build one from a directory."""
    if os.path.isdir(source):
        sys.path.insert(0, TOOLS_DIR)
        import mkpkg
        compile_py = mpy_compiler(mkpkg.find_mpy_cross(args.mpy_cross), args.opt)
        return build_image(source, compile_py)
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

    push = sub.add_parser('push', help='Write an image, or a directory built into one, to the watch')
    push.add_argument('source', help='Image file or directory')

    erase = sub.add_parser('erase', help='Remove the image from the watch')

    for command in (build, push):
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

    image = read_or_build(args.source, args) if args.command == 'push' else None
    if image is not None:
        print(f'image: {len(image)} bytes')

    from nus import connect, reboot
    options = {
        'adapter': args.adapter,
        'address_type': args.address_type,
        'verbose': args.verbose,
    }
    session = (connect if args.no_reboot else reboot)(args.address, **options)
    try:
        if image is None:
            erase_image(session)
        else:
            def progress(done, total):
                print(f'\r{done}/{total} bytes', end='', flush=True)
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
