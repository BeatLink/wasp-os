#!/usr/bin/env python3

# SPDX-License-Identifier: LGPL-3.0-or-later

"""Build an installable NeoTime app package.

Takes an app source directory such as apps/calculator and produces a package
directory holding the compiled module, the launcher icon and a manifest. See
docs/app-packaging-design.md for the format.
"""

import argparse
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile

try:
    import tomllib
except ImportError:
    import tomli as tomllib

TOOLS_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(TOOLS_DIR)

# Files that describe the app to humans rather than to the watch.
SKIP_RESOURCES = {'app.py', 'icon.png', 'pkg.toml', 'screenshot.png'}

# Flags for the firmware's architecture. The Makefile also passes -mno-unicode,
# which MicroPython 1.29 removed, so it is probed for rather than assumed.
MPY_CROSS_FLAGS = ('-march=armv7m',)
MPY_CROSS_OPTIONAL_FLAGS = ('-mno-unicode',)


def load_rle_encode():
    """Import tools/rle_encode.py, which parses arguments when imported.

    Passing an empty argument list leaves it with nothing to do, so the import
    is silent.
    """
    path = os.path.join(TOOLS_DIR, 'rle_encode.py')
    spec = importlib.util.spec_from_file_location('rle_encode', path)
    module = importlib.util.module_from_spec(spec)
    saved = sys.argv
    sys.argv = ['rle_encode.py']
    try:
        spec.loader.exec_module(module)
    finally:
        sys.argv = saved
    return module


def snake_to_pascal(name):
    return ''.join(word[:1].upper() + word[1:] for word in name.split('_'))


def find_mpy_cross(override):
    """Locate an mpy-cross binary, preferring one the caller named."""
    candidates = []
    if override:
        candidates.append(override)
    env = os.environ.get('MPY_CROSS')
    if env:
        candidates.append(env)
    candidates.append(os.path.join(ROOT_DIR, 'micropython', 'mpy-cross', 'mpy-cross'))
    candidates.append(os.path.join(ROOT_DIR, 'micropython', 'mpy-cross', 'build', 'mpy-cross'))

    for candidate in candidates:
        if candidate and os.path.isfile(candidate) and os.access(candidate, os.X_OK):
            return candidate

    found = shutil.which('mpy-cross')
    if found:
        return found

    raise SystemExit(
        'mpy-cross not found. Build it with "make -C micropython/mpy-cross", '
        'or pass --mpy-cross with a path to it.')


def read_abi(mpy_path):
    """Read the bytecode version and architecture out of a compiled module.

    The .mpy header is a magic byte 'M', the bytecode version, a flags byte
    holding the architecture in its upper bits, then the data.
    """
    with open(mpy_path, 'rb') as f:
        header = f.read(4)
    if len(header) < 3 or header[0:1] != b'M':
        raise SystemExit(f'{mpy_path} is not a .mpy file')
    version = header[1]
    arch = header[2] >> 2
    return {'mpy': version, 'arch': arch}


def read_options(source_dir, name):
    """Read apps/NAME/pkg.toml, falling back to the naming conventions."""
    options = {
        'name': name,
        'cls': snake_to_pascal(name) + 'App',
        'label': snake_to_pascal(name),
        'version': '0.1.0',
        'kind': 'app',
        'resident': False,
        'quick_ring': False,
        'config': [],
    }

    path = os.path.join(source_dir, 'pkg.toml')
    if os.path.exists(path):
        with open(path, 'rb') as f:
            options.update(tomllib.load(f))

    if options['kind'] not in ('app', 'face'):
        raise SystemExit(f"{name}: kind must be 'app' or 'face'")
    return options


def detect_flags(mpy_cross):
    """Work out which optional flags this mpy-cross accepts by trying them."""
    flags = list(MPY_CROSS_FLAGS)
    with tempfile.TemporaryDirectory() as scratch:
        source = os.path.join(scratch, 'probe.py')
        target = os.path.join(scratch, 'probe.mpy')
        with open(source, 'w') as f:
            f.write('x = 1\n')
        for flag in MPY_CROSS_OPTIONAL_FLAGS:
            probe = subprocess.run(
                [mpy_cross, *flags, flag, '-o', target, source],
                capture_output=True)
            if probe.returncode == 0:
                flags.append(flag)
    return flags


def compile_module(mpy_cross, flags, source, target):
    result = subprocess.run(
        [mpy_cross, *flags, '-o', target, source],
        capture_output=True, text=True)
    if result.returncode != 0:
        message = (result.stderr or result.stdout).strip()
        raise SystemExit(f'mpy-cross failed on {source}:\n{message}')


def encode_icon(rle, source, target):
    """Encode an icon into the package's self-describing icon file.

    The file is always a depth byte, a width byte, a height byte, then the
    run-length data. A 2-bit icon already carries that header. A 1-bit icon
    comes back as width, height and pixels, so the header is added here.
    """
    from PIL import Image

    image = Image.open(source)
    if image.mode == '1':
        width, height, pixels = rle.encode(image)
        blob = bytes((1, width, height)) + bytes(pixels)
    else:
        # The 2-bit encoder wants full colour, and its output starts with the
        # depth, width and height already.
        blob = bytes(rle.encode_2bit(image.convert('RGB')))

    with open(target, 'wb') as f:
        f.write(blob)
    return len(blob)


def copy_resources(source_dir, target_dir):
    """Copy anything the app opens at runtime into the package."""
    copied = []
    for entry in sorted(os.listdir(source_dir)):
        if entry in SKIP_RESOURCES or entry.startswith('.'):
            continue
        source = os.path.join(source_dir, entry)
        if os.path.isfile(source):
            shutil.copy(source, os.path.join(target_dir, entry))
            copied.append(entry)
    return copied


def write_zip(package_dir, name, zip_path):
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as archive:
        for root, _, files in os.walk(package_dir):
            for entry in sorted(files):
                full = os.path.join(root, entry)
                rel = os.path.relpath(full, package_dir)
                archive.write(full, os.path.join(name, rel))


def build(source_dir, out_dir, mpy_cross, flags, rle, make_zip):
    source_dir = os.path.normpath(source_dir)
    name = os.path.basename(source_dir)
    app_py = os.path.join(source_dir, 'app.py')
    if not os.path.exists(app_py):
        raise SystemExit(f'{source_dir} has no app.py')

    options = read_options(source_dir, name)
    package_dir = os.path.join(out_dir, name)
    os.makedirs(package_dir, exist_ok=True)

    mpy_path = os.path.join(package_dir, 'app.mpy')
    compile_module(mpy_cross, flags, app_py, mpy_path)

    icon_png = os.path.join(source_dir, 'icon.png')
    icon_bytes = 0
    if os.path.exists(icon_png):
        icon_bytes = encode_icon(rle, icon_png, os.path.join(package_dir, 'icon.rle'))

    resources = copy_resources(source_dir, package_dir)

    meta = dict(options)
    meta['abi'] = read_abi(mpy_path)
    meta['icon'] = bool(icon_bytes)
    with open(os.path.join(package_dir, 'meta.json'), 'w') as f:
        json.dump(meta, f, indent=2, sort_keys=True)
        f.write('\n')

    zip_path = None
    if make_zip:
        zip_path = os.path.join(out_dir, name + '.zip')
        write_zip(package_dir, name, zip_path)

    return {
        'name': name,
        'dir': package_dir,
        'mpy': os.path.getsize(mpy_path),
        'icon': icon_bytes,
        'resources': resources,
        'zip': zip_path,
    }


def main():
    parser = argparse.ArgumentParser(description='Build a NeoTime app package.')
    parser.add_argument('sources', nargs='+',
                        help='App source directories, for example apps/calculator')
    parser.add_argument('-o', '--out', default='build-packages',
                        help='Directory to write packages into')
    parser.add_argument('--mpy-cross', help='Path to the mpy-cross binary')
    parser.add_argument('--zip', action='store_true',
                        help='Also write a .zip beside each package directory')
    args = parser.parse_args()

    mpy_cross = find_mpy_cross(args.mpy_cross)
    flags = detect_flags(mpy_cross)
    rle = load_rle_encode()
    os.makedirs(args.out, exist_ok=True)

    for source in args.sources:
        result = build(source, args.out, mpy_cross, flags, rle, args.zip)
        icon = f"{result['icon']} byte icon" if result['icon'] else 'no icon'
        print(f"{result['name']}: {result['mpy']} byte module, {icon}"
              f", {len(result['resources'])} resources -> {result['dir']}")


if __name__ == '__main__':
    main()
