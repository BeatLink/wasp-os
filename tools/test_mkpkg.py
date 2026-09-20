# SPDX-License-Identifier: LGPL-3.0-or-later

"""Tests for the package builder.

Run with: pytest tools/test_mkpkg.py

Needs pillow and an mpy-cross binary. Point at one with the MPY_CROSS
environment variable when it is not in the usual place under micropython/.
"""

import importlib.util
import json
import os

import pytest

TOOLS_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(TOOLS_DIR)


def load_mkpkg():
    path = os.path.join(TOOLS_DIR, 'mkpkg.py')
    spec = importlib.util.spec_from_file_location('mkpkg', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


mkpkg = load_mkpkg()

pytest.importorskip('PIL', reason='the package builder needs pillow')

try:
    MPY_CROSS = mkpkg.find_mpy_cross(None)
except SystemExit:
    MPY_CROSS = None

needs_mpy_cross = pytest.mark.skipif(
    MPY_CROSS is None, reason='no mpy-cross binary available')


@pytest.fixture(scope='module')
def flags():
    return mkpkg.detect_flags(MPY_CROSS)


@pytest.fixture(scope='module')
def rle():
    return mkpkg.load_rle_encode()


@pytest.fixture
def build(tmp_path, flags, rle):
    def run(source_dir, make_zip=False):
        return mkpkg.build(
            os.path.join(ROOT_DIR, source_dir), str(tmp_path),
            MPY_CROSS, flags, rle, make_zip)
    return run


def test_snake_to_pascal():
    assert mkpkg.snake_to_pascal('music_player') == 'MusicPlayer'
    assert mkpkg.snake_to_pascal('calculator') == 'Calculator'


def test_read_options_defaults(tmp_path):
    options = mkpkg.read_options(str(tmp_path), 'music_player')
    assert options['cls'] == 'MusicPlayerApp'
    assert options['label'] == 'MusicPlayer'
    assert options['kind'] == 'app'
    assert options['resident'] is False


def test_read_options_from_pkg_toml(tmp_path):
    (tmp_path / 'pkg.toml').write_text(
        'label = "Music"\nkind = "app"\nresident = true\nversion = "2.0.0"\n')
    options = mkpkg.read_options(str(tmp_path), 'music_player')
    assert options['label'] == 'Music'
    assert options['resident'] is True
    assert options['version'] == '2.0.0'
    # Anything the file leaves out still comes from the conventions.
    assert options['cls'] == 'MusicPlayerApp'


def test_read_options_rejects_bad_kind(tmp_path):
    (tmp_path / 'pkg.toml').write_text('kind = "widget"\n')
    with pytest.raises(SystemExit):
        mkpkg.read_options(str(tmp_path), 'music_player')


@needs_mpy_cross
def test_build_layout(build, tmp_path):
    result = build('apps/music_player')
    package = tmp_path / 'music_player'

    assert (package / 'app.mpy').exists()
    assert (package / 'icon.rle').exists()
    assert (package / 'meta.json').exists()
    assert result['mpy'] > 0

    # The screenshot and the source are for humans, not for the watch.
    assert not (package / 'screenshot.png').exists()
    assert not (package / 'app.py').exists()


@needs_mpy_cross
def test_build_meta(build, tmp_path):
    build('apps/music_player')
    meta = json.loads((tmp_path / 'music_player' / 'meta.json').read_text())

    assert meta['name'] == 'music_player'
    assert meta['cls'] == 'MusicPlayerApp'
    assert meta['kind'] == 'app'
    assert meta['icon'] is True
    assert meta['abi']['mpy'] > 0


@needs_mpy_cross
def test_compiled_module_is_mpy(build, tmp_path):
    build('apps/music_player')
    header = (tmp_path / 'music_player' / 'app.mpy').read_bytes()[:3]
    assert header[0:1] == b'M'
    # The manifest has to describe the file it was built from.
    meta = json.loads((tmp_path / 'music_player' / 'meta.json').read_text())
    assert meta['abi']['mpy'] == header[1]


@needs_mpy_cross
def test_one_bit_icon_header(build, tmp_path):
    """A 1-bit icon carries its depth and the source image's dimensions.

    The sizes come from the image rather than being written down here, so
    redrawing the icons does not break the test.
    """
    from PIL import Image

    build('apps/music_player')
    icon = (tmp_path / 'music_player' / 'icon.rle').read_bytes()
    source = Image.open(os.path.join(ROOT_DIR, 'apps/music_player/icon.png'))

    assert source.mode == '1'
    assert icon[0] == 1
    assert (icon[1], icon[2]) == source.size
    assert len(icon) > 3


@needs_mpy_cross
def test_two_bit_icon_keeps_its_own_header(build, tmp_path):
    """A full colour icon is encoded at 2 bits and already has the header."""
    build('apps/flashlight')
    icon = (tmp_path / 'flashlight' / 'icon.rle').read_bytes()

    assert icon[0] == 2
    assert 0 < icon[1] <= 255
    assert 0 < icon[2] <= 255


@needs_mpy_cross
def test_an_app_without_an_icon_still_builds(build, tmp_path):
    result = build('apps/template')

    assert result['icon'] == 0
    assert not (tmp_path / 'template' / 'icon.rle').exists()
    meta = json.loads((tmp_path / 'template' / 'meta.json').read_text())
    assert meta['icon'] is False


@needs_mpy_cross
def test_zip_contains_the_package(build, tmp_path):
    import zipfile

    result = build('apps/music_player', make_zip=True)
    with zipfile.ZipFile(result['zip']) as archive:
        names = set(archive.namelist())
    assert 'music_player/app.mpy' in names
    assert 'music_player/meta.json' in names


