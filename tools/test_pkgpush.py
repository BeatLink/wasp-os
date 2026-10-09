# SPDX-License-Identifier: LGPL-3.0-or-later

"""Tests for the sending half of the package transfer.

The watch half lives in test_pkgmgr.py. These drive pkgpush against a stand-in
session so the framing, the chunking and the checksum check are covered without
a watch.
"""

import base64
import json

import pytest

pkgpush = pytest.importorskip('pkgpush')


class FakeWatch:
    """A session that answers the way the manager does."""

    def __init__(self, corrupt=False):
        self.buffer = ''
        self.corrupt = corrupt
        self.files = {}
        self.lines = []
        self.receiving = None

    def reply(self, **fields):
        fields['t'] = 'pkg'
        self.buffer += json.dumps(fields) + '\r\n'

    def write(self, text):
        for line in text.replace('\r\n', '\n').split('\n'):
            if line:
                self.handle(line)

    def handle(self, line):
        self.lines.append(line)
        if line.startswith('pkg.recv('):
            path, size = line[len('pkg.recv('):-1].split(',')[:2]
            self.receiving = {'path': path.strip().strip("'\""),
                              'size': int(size), 'data': bytearray()}
            self.reply(ok=True, rx=self.receiving['size'])
            return
        if line.startswith('pkg.reindex()'):
            self.reply(ok=True, count=len(self.files))
            return
        if line.startswith('pkg.ls()'):
            self.reply(ok=True, pkgs=[])
            return
        if self.receiving is not None:
            self.receiving['data'] += base64.b64decode(line)
            got = len(self.receiving['data'])
            self.reply(ack=got)
            if got >= self.receiving['size']:
                total = sum(self.receiving['data']) & 0xffffffff
                if self.corrupt:
                    total += 1
                self.files[self.receiving['path']] = bytes(self.receiving['data'])
                self.reply(ok=True, got=got, sum=total)
                self.receiving = None
            return
        self.buffer += '>>> '

    def pump(self, seconds=0.0):
        return self.buffer

    def expect_prompt(self, timeout=20):
        self.buffer = ''


def test_send_file_round_trips_the_bytes():
    watch = FakeWatch()
    data = bytes(range(256)) * 3
    pkgpush.send_file(watch, 'pkg/demo/app.mpy', data)
    assert watch.files['pkg/demo/app.mpy'] == data


def test_send_file_splits_into_windows():
    watch = FakeWatch()
    data = b'x' * 300
    pkgpush.send_file(watch, 'pkg/demo/app.mpy', data, window=96)
    payloads = [line for line in watch.lines if not line.startswith('pkg.')]
    assert len(payloads) == 4
    assert len(base64.b64decode(payloads[0])) == 96
    assert len(base64.b64decode(payloads[-1])) == 300 - 3 * 96


def test_send_file_rejects_a_disagreeing_checksum():
    watch = FakeWatch(corrupt=True)
    with pytest.raises(RuntimeError, match='checksum'):
        pkgpush.send_file(watch, 'pkg/demo/app.mpy', b'hello')


def test_send_file_rejects_a_refused_transfer():
    watch = FakeWatch()
    watch.handle = lambda line: watch.reply(ok=False, err='no room')
    with pytest.raises(RuntimeError, match='refused'):
        pkgpush.send_file(watch, 'pkg/demo/app.mpy', b'hello')


def test_install_sends_every_file_and_reindexes(tmp_path):
    package = tmp_path / 'demo'
    package.mkdir()
    (package / 'app.mpy').write_bytes(b'code')
    (package / 'icon.rle').write_bytes(b'icon')
    (package / 'meta.json').write_text('{"name": "demo"}')

    watch = FakeWatch()
    reply = pkgpush.install(watch, str(package))

    assert reply == {'t': 'pkg', 'ok': True, 'count': 3}
    assert set(watch.files) == {
        'pkg/demo/app.mpy', 'pkg/demo/icon.rle', 'pkg/demo/meta.json'}
    assert watch.files['pkg/demo/meta.json'] == b'{"name": "demo"}'


def test_install_uses_the_directory_name_as_the_package(tmp_path):
    package = tmp_path / 'flashlight'
    package.mkdir()
    (package / 'app.mpy').write_bytes(b'code')
    watch = FakeWatch()
    pkgpush.install(watch, str(package) + '/')
    assert 'pkg/flashlight/app.mpy' in watch.files
