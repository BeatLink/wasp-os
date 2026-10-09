#!/usr/bin/env python3

# SPDX-License-Identifier: LGPL-3.0-or-later

"""Install a package built by mkpkg.py onto a watch over base64.

This sends the same commands the companion app sends, so it checks the watch
side of the protocol without a phone. The manager has to be importable first,
which before it is frozen means uploading it with nus.py --upload.
"""

import argparse
import binascii
import json
import os
import time

from nus import connect, reboot

# Bytes per encoded line. The manager reports its own figure through abi(), and
# this is the value for an unmodified receive ring.
WINDOW = 96


def read_reply(session, timeout=25):
    """Wait for one JSON reply from the manager."""
    deadline = time.time() + timeout
    while True:
        while '\n' in session.buffer:
            line, session.buffer = session.buffer.split('\n', 1)
            line = line.strip()
            if line.startswith('{'):
                return json.loads(line)
        if time.time() > deadline:
            raise TimeoutError(f'no reply, buffer {session.buffer[-200:]!r}')
        session.pump(0.5)


def call(session, command, timeout=25):
    """Run one manager command and return its reply."""
    session.buffer = ''
    session.write(command + '\r\n')
    reply = read_reply(session, timeout)
    session.expect_prompt(timeout)
    return reply


def send_file(session, path, data, window=WINDOW):
    """Push one file and check the checksum the watch reports."""
    session.buffer = ''
    session.write(f'pkg.recv({path!r}, {len(data)}, True)\r\n')
    start = read_reply(session)
    if not start.get('ok') or start.get('rx') != len(data):
        raise RuntimeError(f'{path}: the watch refused the transfer: {start}')

    for at in range(0, len(data), window):
        session.write(binascii.b2a_base64(data[at:at + window]).decode().strip() + '\r\n')
        read_reply(session)

    done = read_reply(session)
    expected = sum(data) & 0xffffffff
    if not done.get('ok') or done.get('sum') != expected:
        raise RuntimeError(f'{path}: checksum {done.get("sum")} wanted {expected}')
    session.expect_prompt(20)
    return done['sum']


def install(session, directory, window=WINDOW):
    """Send every file of a package directory, then rebuild the index."""
    name = os.path.basename(directory.rstrip('/'))
    for entry in sorted(os.listdir(directory)):
        with open(os.path.join(directory, entry), 'rb') as handle:
            data = handle.read()
        total = send_file(session, f'pkg/{name}/{entry}', data, window)
        print(f'  {entry}: {len(data)} bytes, checksum {total:#x} agreed')
    return call(session, 'pkg.reindex()')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', help='A package directory that mkpkg.py wrote')
    parser.add_argument('--address', required=True, help='The watch Bluetooth address')
    parser.add_argument('--adapter', default='hci0', help='Which local adapter to use')
    parser.add_argument('--address-type', default='random', choices=('random', 'public'))
    parser.add_argument('--manager', default='pkgmgr',
                        help='Module to import the manager from')
    parser.add_argument('--no-reboot', action='store_true',
                        help='Skip the soft reboot that frees the heap first')
    parser.add_argument('--verbose', action='store_true')
    args = parser.parse_args()

    options = {
        'adapter': args.adapter,
        'address_type': args.address_type,
        'verbose': args.verbose,
    }
    session = (connect if args.no_reboot else reboot)(args.address, **options)
    try:
        session.cmd("import sys, gc; sys.path.append('/flash'); gc.collect()")
        session.cmd(f'import {args.manager} as pkg')
        print('abi:', call(session, 'pkg.abi()')['abi'])
        print('reindex:', install(session, args.directory))
        print('installed:', call(session, 'pkg.ls()')['pkgs'])
    finally:
        session.close()


if __name__ == '__main__':
    main()
