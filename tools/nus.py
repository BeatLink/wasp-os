#!/usr/bin/env python3

# SPDX-License-Identifier: LGPL-3.0-or-later

"""Drive the watch REPL over the Nordic UART Service using gatttool.

The tools built on BlueZ's GATT layer, wasptool among them, need the watch to
report its services. Some watches connect and never do, which looks like a hung
tool rather than a refusal. gatttool speaks ATT over its own socket and gets
through, so this is the fallback transport when nothing else reaches the watch.
"""

import argparse
import binascii
import re
import sys
import time

import pexpect

# The Nordic UART Service as wasp-os lays it out: notifications come from the
# first handle, writes go to the second.
TX_VALUE = '0x0010'
TX_CCCD = '0x0011'
RX_VALUE = '0x0013'

# One write carries twenty bytes.
WRITE_SIZE = 20

# Bytes per chunk when uploading, which keeps a command line inside the small
# buffer between the radio and Python.
CHUNK_SIZE = 64

# How often to collect garbage while uploading. The watch runs out of heap part
# way through a long upload without this.
COLLECT_EVERY = 8

NOTIFY = re.compile(rf'Notification handle = {TX_VALUE} value: ([0-9a-f ]+)')
PROMPT = '>>> '


class Timeout(Exception):
    """The watch did not answer in time."""


class Nus:
    """A REPL session on one watch."""

    def __init__(self, address, adapter='hci0', address_type='random', verbose=False):
        self.verbose = verbose
        self.buffer = ''
        self.child = pexpect.spawn(
            f'gatttool -i {adapter} -b {address} -t {address_type} -I', encoding='latin-1')
        self.child.expect(r'\[LE\]>')
        self.child.sendline('connect')
        self.child.expect('Connection successful', timeout=30)
        self.child.sendline(f'char-write-req {TX_CCCD} 0100')
        self.child.expect('Characteristic value was written successfully', timeout=20)

    def pump(self, seconds=1.0):
        """Collect whatever the watch says for a while."""
        deadline = time.time() + seconds
        while time.time() < deadline:
            try:
                self.child.expect(NOTIFY, timeout=max(0.05, deadline - time.time()))
            except (pexpect.TIMEOUT, pexpect.EOF):
                break
            text = bytes.fromhex(self.child.match.group(1).replace(' ', '')).decode('latin-1')
            if self.verbose:
                sys.stdout.write(text)
                sys.stdout.flush()
            self.buffer += text
        return self.buffer

    def write(self, data):
        """Send raw bytes, as many writes as it takes."""
        if isinstance(data, str):
            data = data.encode('latin-1')
        for start in range(0, len(data), WRITE_SIZE):
            chunk = data[start:start + WRITE_SIZE]
            self.child.sendline(f'char-write-cmd {RX_VALUE} {chunk.hex()}')
            self.child.expect(r'\[LE\]>', timeout=10)

    def expect_prompt(self, timeout=20):
        """Read until the watch offers its prompt again."""
        deadline = time.time() + timeout
        while not self.buffer.endswith(PROMPT):
            if time.time() > deadline:
                raise Timeout(f'no prompt after: {self.buffer[-200:]!r}')
            self.pump(0.3)
        return self.buffer

    def sync(self, tries=6):
        """Knock with a bare newline until the watch answers.

        main.py calls wasp.system.schedule(), which installs a background tick
        and returns, so the watch offers a prompt while it is running normally.
        Never send an interrupt to get one: that lands inside the tick and the
        watch draws the traceback on its screen.
        """
        for _ in range(tries):
            self.buffer = ''
            self.write('\r\n')
            self.pump(2.0)
            if self.buffer.endswith(PROMPT):
                return
        raise Timeout('the watch never offered a prompt')

    def cmd(self, line, timeout=20):
        """Run one line and return what it printed."""
        self.buffer = ''
        self.write(line + '\r\n')
        self.expect_prompt(timeout)
        out = self.buffer
        if '\r\n' in out:
            out = out.split('\r\n', 1)[1]
        return out[:-len(PROMPT)].strip('\r\n')

    def upload(self, source, target, progress=None):
        """Copy a local file to the watch, base64 a chunk at a time."""
        with open(source, 'rb') as handle:
            data = handle.read()
        self.cmd('import gc, ubinascii')
        self.cmd(f'f = open("{target}", "wb")')
        # A lambda keeps the per-chunk command short and avoids the "..." prompt.
        self.cmd('w = lambda d: f.write(ubinascii.a2b_base64(d))')
        for index, start in enumerate(range(0, len(data), CHUNK_SIZE)):
            encoded = binascii.b2a_base64(data[start:start + CHUNK_SIZE]).strip()
            self.cmd(f'w({encoded!r})')
            if index % COLLECT_EVERY == COLLECT_EVERY - 1:
                self.cmd('gc.collect()')
            if progress:
                progress(min(start + CHUNK_SIZE, len(data)), len(data))
        self.cmd('f.close()')
        self.cmd('del w, f')
        self.cmd('gc.collect()')
        return len(data)

    def close(self):
        self.child.sendline('disconnect')
        self.child.sendline('exit')
        self.child.close(force=True)


def reboot(address, settle=10, **kwargs):
    """Soft reboot the watch and come back on a new link.

    Ctrl-D restarts MicroPython, which takes the radio down with it, so the
    session has to be rebuilt rather than waited on. This is also the only way
    back once the heap is full, because by then an import cannot allocate.
    """
    session = Nus(address, **kwargs)
    session.write('\x03')
    session.pump(1.0)
    session.write('\x04')
    session.pump(3.0)
    session.close()
    time.sleep(settle)
    return connect(address, **kwargs)


def connect(address, tries=8, **kwargs):
    """Open a session, retrying while the watch settles."""
    last = None
    for _ in range(tries):
        session = None
        try:
            session = Nus(address, **kwargs)
            session.sync()
            return session
        except Exception as error:
            last = error
            if session:
                try:
                    session.close()
                except Exception:
                    pass
            time.sleep(4)
    raise Timeout(f'could not reach {address}: {last}')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('line', nargs='*', help='REPL lines to run in order')
    parser.add_argument('--address', required=True, help='The watch Bluetooth address')
    parser.add_argument('--adapter', default='hci0', help='Which local adapter to use')
    parser.add_argument('--address-type', default='random', choices=('random', 'public'))
    parser.add_argument('--reboot', action='store_true',
                        help='Soft reboot first, which frees the heap')
    parser.add_argument('--upload', nargs=2, metavar=('SOURCE', 'TARGET'),
                        help='Copy a local file to the watch')
    parser.add_argument('--verbose', action='store_true')
    args = parser.parse_args()

    options = {
        'adapter': args.adapter,
        'address_type': args.address_type,
        'verbose': args.verbose,
    }
    session = (reboot if args.reboot else connect)(args.address, **options)
    try:
        if args.upload:
            def progress(done, total):
                print(f'\r{done}/{total} bytes', end='', flush=True)
            session.upload(args.upload[0], args.upload[1], progress)
            print()
        for line in args.line:
            print(session.cmd(line, timeout=30))
    finally:
        session.close()


if __name__ == '__main__':
    main()
