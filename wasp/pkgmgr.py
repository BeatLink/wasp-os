# SPDX-License-Identifier: LGPL-3.0-or-later
"""Package manager
~~~~~~~~~~~~~~~~~~

Installs, removes, enables and configures app packages held on the external
flash. The companion app drives it over the REPL, one command per line, and
every reply is a single JSON object tagged ``pkg``.

The format and the protocol are described in docs/app-packaging-design.md.

Paths are relative, so this assumes the working directory is ``/flash`` as it
is during a normal boot.
"""

import json
import os
import sys

try:
    import binascii
except ImportError:
    import ubinascii as binascii

try:
    import micropython
except ImportError:
    micropython = None

PKG_DIR = 'pkg'
INDEX = 'pkg/index.json'

# Bytes to take per read in raw mode. The buffer between the radio and Python
# is small, and a flash write can stall for milliseconds, so stay under it.
WINDOW = 96

# Fields the index keeps, so that nothing needs importing before the launcher
# can draw.
_INDEXED = ('name', 'label', 'cls', 'kind', 'resident', 'quick_ring')


def _reply(**kwargs):
    kwargs['t'] = 'pkg'
    json.dump(kwargs, sys.stdout)
    sys.stdout.write('\r\n')


def _is_dir(path):
    try:
        return bool(os.stat(path)[0] & 0x4000)
    except OSError:
        return False


def _exists(path):
    try:
        os.stat(path)
        return True
    except OSError:
        return False


def _mkdirs(path):
    """Create every missing directory along a path."""
    parts = path.split('/')[:-1]
    grown = ''
    for part in parts:
        if not part:
            continue
        grown = grown + part if not grown else grown + '/' + part
        if not _exists(grown):
            os.mkdir(grown)


def _rmtree(path):
    for entry in os.listdir(path):
        full = path + '/' + entry
        if _is_dir(full):
            _rmtree(full)
        else:
            os.remove(full)
    os.rmdir(path)


def _load(path, default=None):
    try:
        with open(path) as f:
            return json.load(f)
    except (OSError, ValueError):
        return default if default is not None else {}


def _save(path, data):
    _mkdirs(path)
    with open(path, 'w') as f:
        json.dump(data, f)


def load_index():
    """Return the installed package index, rebuilding it if it is missing."""
    index = _load(INDEX, {})
    if not index:
        index = reindex(quiet=True)
    return index


def reindex(quiet=False):
    """Rebuild the index by reading each package's manifest."""
    index = {}
    enabled = set()
    for entry in _load(INDEX, {}).values():
        if entry.get('enabled'):
            enabled.add(entry['name'])

    try:
        names = os.listdir(PKG_DIR)
    except OSError:
        names = []

    for name in names:
        path = PKG_DIR + '/' + name
        if not _is_dir(path):
            continue
        meta = _load(path + '/meta.json', {})
        if not meta:
            continue
        entry = {}
        for field in _INDEXED:
            if field in meta:
                entry[field] = meta[field]
        entry['name'] = name
        entry['version'] = meta.get('version', '?')
        entry['enabled'] = name in enabled
        index[name] = entry

    _save(INDEX, index)
    if not quiet:
        _reply(ok=True, count=len(index))
    return index


def abi():
    """Report what this firmware can load, so the phone can check a package."""
    info = {}
    try:
        info['mpy'] = sys.implementation._mpy & 0xff
        info['arch'] = (sys.implementation._mpy >> 10) & 0x3f
    except AttributeError:
        info['mpy'] = None
        info['arch'] = None
    info['raw'] = hasattr(sys.stdin, 'buffer')
    info['window'] = WINDOW
    _reply(ok=True, abi=info)


def ls():
    """List what is installed."""
    index = load_index()
    packages = [
        {'name': e['name'], 'version': e.get('version', '?'),
         'enabled': e.get('enabled', False), 'kind': e.get('kind', 'app')}
        for e in index.values()
    ]
    _reply(ok=True, pkgs=packages)


def recv(path, size, b64=False):
    """Receive a file of exactly size bytes.

    In raw mode the interrupt character is disabled so that a 0x03 byte in the
    payload is not mistaken for Ctrl-C. In base64 mode the phone sends one
    encoded line per chunk, which needs no such care and works on a firmware
    built without ``sys.stdin.buffer``.
    """
    if not b64 and not hasattr(sys.stdin, 'buffer'):
        _reply(ok=False, err='raw unavailable, use b64')
        return

    _mkdirs(path)
    got = 0
    checksum = 0

    if not b64 and micropython:
        micropython.kbd_intr(-1)
    try:
        _reply(ok=True, rx=size)
        with open(path, 'wb') as f:
            while got < size:
                if b64:
                    chunk = binascii.a2b_base64(input())
                else:
                    chunk = sys.stdin.buffer.read(min(WINDOW, size - got))
                if not chunk:
                    break
                f.write(chunk)
                got += len(chunk)
                for byte in chunk:
                    checksum += byte
                checksum &= 0xffffffff
                _reply(ack=got)
    finally:
        if not b64 and micropython:
            micropython.kbd_intr(3)

    _reply(ok=(got == size), got=got, sum=checksum)


def rm(name):
    """Remove an installed package."""
    path = PKG_DIR + '/' + name
    if not _is_dir(path):
        _reply(ok=False, err='not installed')
        return
    _rmtree(path)
    index = load_index()
    index.pop(name, None)
    _save(INDEX, index)
    _forget(name)
    _reply(ok=True, removed=name)


def _set_enabled(name, state):
    index = load_index()
    if name not in index:
        _reply(ok=False, err='not installed')
        return
    index[name]['enabled'] = state
    _save(INDEX, index)
    _reply(ok=True, name=name, enabled=state)


def enable(name):
    _set_enabled(name, True)


def disable(name):
    _set_enabled(name, False)


def cfg(name, values):
    """Store a package's settings, as sent by the companion app.

    The phone sends a JSON string rather than a literal, because Python and
    JSON spell their booleans and their null differently.
    """
    path = PKG_DIR + '/' + name
    if not _is_dir(path):
        _reply(ok=False, err='not installed')
        return
    if isinstance(values, str):
        try:
            values = json.loads(values)
        except ValueError:
            _reply(ok=False, err='bad json')
            return
    _save(path + '/config.json', values)
    _reply(ok=True, name=name)


def config_of(name):
    """Read a package's stored settings, for the app or the launcher."""
    return _load(PKG_DIR + '/' + name + '/config.json', {})


def icon_of(name):
    """Read a package's launcher icon without importing its code.

    A 1-bit icon is returned as the width, height and pixels triple that
    rleblit takes. A 2-bit icon is returned as the flat bytes that blit takes.
    Both are what an app's own ICON would have been.
    """
    try:
        with open(PKG_DIR + '/' + name + '/icon.rle', 'rb') as f:
            blob = f.read()
    except OSError:
        return None
    if len(blob) < 3:
        return None
    if blob[0] == 1:
        return (blob[1], blob[2], blob[3:])
    return blob


def module_of(name):
    """The import path of a package's code."""
    return '{}.{}.app'.format(PKG_DIR, name)


def _forget(name):
    """Drop a package's modules so a reinstall picks up the new code.

    Importing pkg.NAME.app leaves all three levels in sys.modules, and
    register() only removes the one it asked for.
    """
    for module in (module_of(name), '{}.{}'.format(PKG_DIR, name), PKG_DIR):
        if module in sys.modules:
            del sys.modules[module]
