# SPDX-License-Identifier: LGPL-3.0-or-later

"""Tests for the on-watch package manager.

Run with: pytest tools/test_pkgmgr.py

The manager is written for MicroPython but uses nothing CPython lacks, so it
runs here against a temporary directory standing in for /flash.
"""

import base64
import importlib.util
import io
import json
import os

import pytest

TOOLS_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(TOOLS_DIR)


def load_pkgmgr():
    path = os.path.join(ROOT_DIR, 'wasp', 'pkgmgr.py')
    spec = importlib.util.spec_from_file_location('pkgmgr', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


pkgmgr = load_pkgmgr()


@pytest.fixture
def flash(tmp_path, monkeypatch):
    """Run each test with the working directory standing in for /flash."""
    monkeypatch.chdir(tmp_path)
    return tmp_path


@pytest.fixture
def replies(monkeypatch):
    """Capture the JSON objects the manager writes to stdout."""
    captured = []

    def fake_reply(**kwargs):
        kwargs['t'] = 'pkg'
        captured.append(kwargs)

    monkeypatch.setattr(pkgmgr, '_reply', fake_reply)
    return captured


def make_package(flash, name, version='1.0.0', **meta):
    path = flash / 'pkg' / name
    path.mkdir(parents=True)
    body = {'name': name, 'label': name.title(), 'cls': name.title() + 'App',
            'kind': 'app', 'resident': False, 'quick_ring': False,
            'version': version}
    body.update(meta)
    (path / 'meta.json').write_text(json.dumps(body))
    (path / 'app.mpy').write_bytes(b'M\x06\x00\x1f')
    (path / 'icon.rle').write_bytes(b'\x02\x20\x20icon-data')
    return path


def test_reindex_finds_packages(flash, replies):
    make_package(flash, 'calculator')
    make_package(flash, 'gallery')

    index = pkgmgr.reindex()

    assert set(index) == {'calculator', 'gallery'}
    assert index['calculator']['cls'] == 'CalculatorApp'
    assert index['calculator']['enabled'] is False
    assert (flash / 'pkg' / 'index.json').exists()


def test_reindex_keeps_enabled_state(flash, replies):
    make_package(flash, 'calculator')
    pkgmgr.reindex()
    pkgmgr.enable('calculator')

    index = pkgmgr.reindex()

    assert index['calculator']['enabled'] is True


def test_reindex_ignores_a_package_with_no_manifest(flash, replies):
    make_package(flash, 'calculator')
    (flash / 'pkg' / 'broken').mkdir()

    index = pkgmgr.reindex()

    assert set(index) == {'calculator'}


def test_load_index_rebuilds_when_absent(flash, replies):
    make_package(flash, 'calculator')

    index = pkgmgr.load_index()

    assert 'calculator' in index


def test_enable_and_disable(flash, replies):
    make_package(flash, 'calculator')
    pkgmgr.reindex()

    pkgmgr.enable('calculator')
    assert pkgmgr.load_index()['calculator']['enabled'] is True

    pkgmgr.disable('calculator')
    assert pkgmgr.load_index()['calculator']['enabled'] is False


def test_enable_an_unknown_package_reports_an_error(flash, replies):
    pkgmgr.reindex()
    replies.clear()

    pkgmgr.enable('nope')

    assert replies[-1]['ok'] is False


def test_rm_removes_the_directory_and_the_entry(flash, replies):
    make_package(flash, 'calculator')
    make_package(flash, 'gallery')
    pkgmgr.reindex()

    pkgmgr.rm('calculator')

    assert not (flash / 'pkg' / 'calculator').exists()
    assert set(pkgmgr.load_index()) == {'gallery'}


def test_rm_an_unknown_package_reports_an_error(flash, replies):
    pkgmgr.rm('nope')
    assert replies[-1]['ok'] is False


def test_ls_lists_versions_and_state(flash, replies):
    make_package(flash, 'calculator', version='2.1.0')
    pkgmgr.reindex()
    pkgmgr.enable('calculator')
    replies.clear()

    pkgmgr.ls()

    packages = replies[-1]['pkgs']
    assert packages == [{'name': 'calculator', 'version': '2.1.0',
                         'enabled': True, 'kind': 'app'}]


def test_cfg_writes_settings(flash, replies):
    make_package(flash, 'calculator')
    pkgmgr.reindex()

    pkgmgr.cfg('calculator', {'precision': 4})

    assert pkgmgr.config_of('calculator') == {'precision': 4}


def test_config_of_is_empty_when_unset(flash, replies):
    make_package(flash, 'calculator')
    assert pkgmgr.config_of('calculator') == {}


def test_icon_of_returns_flat_bytes_for_a_two_bit_icon(flash, replies):
    make_package(flash, 'calculator')
    assert pkgmgr.icon_of('calculator') == b'\x02\x20\x20icon-data'


def test_icon_of_returns_a_triple_for_a_one_bit_icon(flash, replies):
    path = make_package(flash, 'symbolic')
    (path / 'icon.rle').write_bytes(bytes((1, 48, 48)) + b'pixels')

    assert pkgmgr.icon_of('symbolic') == (48, 48, b'pixels')


def test_icon_of_ignores_a_truncated_file(flash, replies):
    path = make_package(flash, 'broken')
    (path / 'icon.rle').write_bytes(b'\x01')

    assert pkgmgr.icon_of('broken') is None


def test_icon_of_missing_package_is_none(flash, replies):
    assert pkgmgr.icon_of('nope') is None


def test_module_of():
    assert pkgmgr.module_of('calculator') == 'pkg.calculator.app'


def test_recv_base64(flash, replies, monkeypatch):
    payload = bytes(range(256)) * 2
    chunks = [payload[i:i + 96] for i in range(0, len(payload), 96)]
    lines = iter([base64.b64encode(c).decode() for c in chunks])
    monkeypatch.setattr('builtins.input', lambda: next(lines))

    pkgmgr.recv('pkg/calculator/app.mpy', len(payload), b64=True)

    written = (flash / 'pkg' / 'calculator' / 'app.mpy').read_bytes()
    assert written == payload
    final = replies[-1]
    assert final['ok'] is True
    assert final['got'] == len(payload)
    assert final['sum'] == sum(payload)


def test_recv_creates_missing_directories(flash, replies, monkeypatch):
    payload = b'hello'
    lines = iter([base64.b64encode(payload).decode()])
    monkeypatch.setattr('builtins.input', lambda: next(lines))

    pkgmgr.recv('pkg/deep/nested/file.bin', len(payload), b64=True)

    assert (flash / 'pkg' / 'deep' / 'nested' / 'file.bin').read_bytes() == payload


def test_recv_acknowledges_each_chunk(flash, replies, monkeypatch):
    payload = b'x' * 200
    chunks = [payload[i:i + 96] for i in range(0, len(payload), 96)]
    lines = iter([base64.b64encode(c).decode() for c in chunks])
    monkeypatch.setattr('builtins.input', lambda: next(lines))

    pkgmgr.recv('pkg/a/app.mpy', len(payload), b64=True)

    acks = [r['ack'] for r in replies if 'ack' in r]
    assert acks == [96, 192, 200]


def test_recv_reports_a_short_transfer(flash, replies, monkeypatch):
    lines = iter([base64.b64encode(b'short').decode(), ''])
    monkeypatch.setattr('builtins.input', lambda: next(lines))

    pkgmgr.recv('pkg/a/app.mpy', 500, b64=True)

    assert replies[-1]['ok'] is False
    assert replies[-1]['got'] == 5


def test_recv_raw_rejected_without_stdin_buffer(flash, replies, monkeypatch):
    monkeypatch.setattr(pkgmgr.sys, 'stdin', io.StringIO())

    pkgmgr.recv('pkg/a/app.mpy', 10, b64=False)

    assert replies[-1]['ok'] is False
    assert 'b64' in replies[-1]['err']


def test_recv_raw_reads_from_stdin_buffer(flash, replies, monkeypatch):
    payload = bytes(range(200))

    class FakeStdin:
        buffer = io.BytesIO(payload)

    monkeypatch.setattr(pkgmgr.sys, 'stdin', FakeStdin())
    monkeypatch.setattr(pkgmgr, 'micropython', None)

    pkgmgr.recv('pkg/a/app.mpy', len(payload), b64=False)

    assert (flash / 'pkg' / 'a' / 'app.mpy').read_bytes() == payload
    assert replies[-1]['ok'] is True


def test_abi_reports_transfer_support(flash, replies, monkeypatch):
    monkeypatch.setattr(pkgmgr.sys, 'stdin', io.StringIO())

    pkgmgr.abi()

    info = replies[-1]['abi']
    assert info['raw'] is False
    assert info['window'] == pkgmgr.WINDOW


def test_forget_clears_every_module_level(flash, replies):
    import sys as real_sys

    for name in ('pkg', 'pkg.calculator', 'pkg.calculator.app'):
        real_sys.modules[name] = object()

    pkgmgr._forget('calculator')

    for name in ('pkg', 'pkg.calculator', 'pkg.calculator.app'):
        assert name not in real_sys.modules


def test_cfg_accepts_a_json_string(flash, replies):
    make_package(flash, 'calculator')
    pkgmgr.reindex()

    pkgmgr.cfg('calculator', '{"loud": true, "steps": 3}')

    assert pkgmgr.config_of('calculator') == {'loud': True, 'steps': 3}


def test_cfg_rejects_bad_json(flash, replies):
    make_package(flash, 'calculator')
    pkgmgr.reindex()

    pkgmgr.cfg('calculator', '{not json')

    assert replies[-1]['ok'] is False
    assert replies[-1]['err'] == 'bad json'
