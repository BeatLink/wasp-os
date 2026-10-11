# SPDX-License-Identifier: LGPL-3.0-or-later

"""Tests for building a ROMFS image and writing it over the REPL.

A stand-in session plays the firmware's vfs.rom_ioctl, so the erase, the
chunking and the checksum are covered without a watch.
"""

import base64
import json
import re

import pytest

romfs = pytest.importorskip('romfs')


class FakeWatch:
    """A REPL that answers the ROMFS commands the way the firmware does."""

    def __init__(self, size=0x4000, corrupt=False):
        self.flash = bytearray(b'\xa5' * size)
        self.corrupt = corrupt
        self.lines = []
        self.scheduling = True
        self.erased = []

    def cmd(self, line, timeout=20):
        self.lines.append(line)
        if line == romfs.STOP_TICK:
            self.scheduling = False
        if line == 'len(vfs.rom_ioctl(2, 0))':
            return str(len(self.flash))
        match = re.fullmatch(r'vfs\.rom_ioctl\(3, 0, 0, (\d+)\)', line)
        if match:
            span = int(match.group(1))
            assert span % romfs.PAGE_SIZE == 0
            self.flash[:span] = b'\xff' * span
            self.erased.append(span)
            return '4'
        match = re.fullmatch(r"w\((\d+), b'(.*)'\)", line)
        if match:
            assert not self.scheduling
            offset = int(match.group(1))
            data = base64.b64decode(match.group(2))
            assert all(byte == 0xff for byte in self.flash[offset:offset + len(data)])
            self.flash[offset:offset + len(data)] = data
            return '0'
        match = re.fullmatch(r'sum\(memoryview\(vfs\.rom_ioctl\(2, 0\)\)\[:(\d+)\]\)', line)
        if match:
            return str(sum(self.flash[:int(match.group(1))]) + self.corrupt)
        if line == 'vfs.rom_ioctl(5, 0)':
            return '0'
        return ''


def fake_compile(source, name):
    with open(source, 'rb') as handle:
        return b'M' + name.encode() + b':' + handle.read()


def test_build_image_compiles_python_and_keeps_other_files(tmp_path):
    (tmp_path / 'demo.py').write_text('x = 1\n')
    (tmp_path / 'apps').mkdir()
    (tmp_path / 'apps' / 'icon.rle').write_bytes(b'\x01\x02')
    image = romfs.build_image(str(tmp_path), fake_compile)
    assert image.startswith(b'\xd2\xcd\x31')
    assert b'demo.mpy' in image and b'Mdemo.py:x = 1\n' in image
    assert b'apps' in image and b'icon.rle' in image
    assert b'\x07demo.py' not in image


def test_write_image_round_trips_the_bytes():
    watch = FakeWatch()
    image = bytes(range(256)) * 5
    romfs.write_image(watch, image)
    assert bytes(watch.flash[:len(image)]) == image
    assert watch.erased == [romfs.PAGE_SIZE]


def test_write_image_erases_whole_pages_up_to_the_end():
    watch = FakeWatch()
    romfs.write_image(watch, b'x' * (romfs.PAGE_SIZE + 1))
    assert watch.erased == [2 * romfs.PAGE_SIZE]


def test_write_image_stops_the_tick_before_writing():
    watch = FakeWatch()
    romfs.write_image(watch, b'abc')
    stop = watch.lines.index(romfs.STOP_TICK)
    first_write = next(i for i, line in enumerate(watch.lines) if line.startswith('w('))
    assert stop < first_write


def test_write_image_refuses_an_image_bigger_than_the_partition():
    watch = FakeWatch(size=romfs.PAGE_SIZE)
    with pytest.raises(RuntimeError, match='partition'):
        romfs.write_image(watch, b'x' * (romfs.PAGE_SIZE + 1))
    assert watch.erased == []


def test_write_image_rejects_a_disagreeing_checksum():
    watch = FakeWatch(corrupt=True)
    with pytest.raises(RuntimeError, match='sum'):
        romfs.write_image(watch, b'hello')


def test_erase_image_erases_the_header_page():
    watch = FakeWatch()
    romfs.erase_image(watch)
    assert watch.erased == [romfs.PAGE_SIZE]


def test_build_image_takes_only_the_listed_files(tmp_path):
    (tmp_path / 'apps').mkdir()
    (tmp_path / 'apps' / 'clock.py').write_text('c = 1\n')
    (tmp_path / 'apps' / 'left_out.py').write_text('l = 1\n')
    (tmp_path / 'wasp.py').write_text('w = 1\n')
    image = romfs.build_image(str(tmp_path), fake_compile, ['apps/clock.py', 'wasp.py'])
    assert b'clock.mpy' in image and b'wasp.mpy' in image
    assert b'Mapps/clock.py:' in image
    assert b'left_out' not in image


def test_manifest_files_reads_the_image_list(tmp_path):
    board = tmp_path / 'demo'
    board.mkdir()
    (tmp_path / 'shared_list.py').write_text("manifest = ('apps/a.py',)\n")
    (board / 'manifest_romfs.py').write_text(
        "import shared_list\nimage = shared_list.manifest + ('wasp.py',)\n")
    assert romfs.manifest_files(str(board / 'manifest_romfs.py')) == ('apps/a.py', 'wasp.py')


def test_merge_hex_places_the_image_at_the_partition(tmp_path):
    intelhex = pytest.importorskip('intelhex')
    firmware = intelhex.IntelHex()
    firmware.frombytes(b'\x01\x02\x03\x04', offset=0x19000)
    firmware.write_hex_file(str(tmp_path / 'firmware.hex'))
    romfs.merge_hex(str(tmp_path / 'firmware.hex'), b'\xd2\xcd\x31\x00', 0x58000, 0x20000,
                    str(tmp_path / 'merged.hex'))
    merged = intelhex.IntelHex(str(tmp_path / 'merged.hex'))
    assert merged.tobinstr(0x19000, 0x19003) == b'\x01\x02\x03\x04'
    assert merged.tobinstr(0x58000, 0x58003) == b'\xd2\xcd\x31\x00'


def test_merge_hex_refuses_a_firmware_reaching_the_partition(tmp_path):
    intelhex = pytest.importorskip('intelhex')
    firmware = intelhex.IntelHex()
    firmware.frombytes(b'\x00' * 8, offset=0x57ffc)
    firmware.write_hex_file(str(tmp_path / 'firmware.hex'))
    with pytest.raises(SystemExit, match='inside the partition'):
        romfs.merge_hex(str(tmp_path / 'firmware.hex'), b'x', 0x58000, 0x20000,
                        str(tmp_path / 'merged.hex'))


class FakeManager:
    """A REPL with the package manager and romwriter, as a watch with a working image has."""

    def __init__(self, window=512, has_manager=True):
        self.buffer = ''
        self.window = window
        self.has_manager = has_manager
        self.receiving = None
        self.files = {}
        self.installed = None

    def reply(self, **fields):
        self.buffer += json.dumps(fields) + '\r\n'

    def cmd(self, line, timeout=20):
        if line == 'import pkgmgr as pkg':
            return '' if self.has_manager else "ImportError: no module named 'pkgmgr'"
        return ''

    def write(self, data):
        if self.receiving is not None:
            self.receiving['data'] += data
            got = len(self.receiving['data'])
            self.reply(t='pkg', ack=got)
            if got == self.receiving['size']:
                self.files[self.receiving['path']] = bytes(self.receiving['data'])
                self.reply(t='pkg', ok=True, got=got, sum=sum(self.receiving['data']) & 0xffffffff)
                self.receiving = None
                self.buffer += '>>> '
            return
        line = data.strip()
        if line == 'pkg.abi()':
            self.reply(t='pkg', ok=True, abi={'raw': True, 'window': self.window})
        elif line.startswith('pkg.recv('):
            path, size = line[len('pkg.recv('):-1].split(', ')
            self.receiving = {'path': path.strip("'"), 'size': int(size), 'data': bytearray()}
            self.reply(t='pkg', ok=True, rx=int(size))
            return
        elif line.startswith('import romwriter'):
            self.installed = self.files[romfs.STAGING]
            self.reply(t='rom', ok=True, size=len(self.installed))
        self.buffer += '>>> '

    def pump(self, seconds=0.0):
        return self.buffer

    def expect_prompt(self, timeout=20):
        self.buffer = ''


def test_install_image_stages_the_image_and_runs_romwriter():
    watch = FakeManager(window=512)
    image = bytes(range(256)) * 9
    assert romfs.install_image(watch, image)
    assert watch.installed == image


def test_install_image_declines_without_the_package_manager():
    watch = FakeManager(has_manager=False)
    assert not romfs.install_image(watch, b'image')
    assert watch.installed is None
