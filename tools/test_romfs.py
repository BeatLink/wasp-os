# SPDX-License-Identifier: LGPL-3.0-or-later

"""Tests for building a ROMFS image and writing it over the REPL.

A stand-in session plays the firmware's vfs.rom_ioctl, so the erase, the
chunking and the checksum are covered without a watch.
"""

import base64
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
        if line == 'wasp.system.schedule(False)':
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


def fake_compile(source):
    with open(source, 'rb') as handle:
        return b'M' + handle.read()


def test_build_image_compiles_python_and_keeps_other_files(tmp_path):
    (tmp_path / 'demo.py').write_text('x = 1\n')
    (tmp_path / 'apps').mkdir()
    (tmp_path / 'apps' / 'icon.rle').write_bytes(b'\x01\x02')
    image = romfs.build_image(str(tmp_path), fake_compile)
    assert image.startswith(b'\xd2\xcd\x31')
    assert b'demo.mpy' in image and b'Mx = 1\n' in image
    assert b'apps' in image and b'icon.rle' in image
    assert b'demo.py' not in image


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
    stop = watch.lines.index('wasp.system.schedule(False)')
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
