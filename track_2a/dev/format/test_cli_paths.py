"""CLI-only repeat/path regression tests. Never sends a request or reads a key."""
import json
from pathlib import Path
import socket
import sys

import pytest

sys.path.insert(0, str(Path(__file__).parent))
import run_comparison as r


@pytest.fixture(autouse=True)
def no_remote(monkeypatch):
    def denied(*a, **kw):
        raise AssertionError('credential/remote call forbidden')
    monkeypatch.setattr(r.legacy.c, 'read_key', denied)
    monkeypatch.setattr(r.Transport, 'request', denied)
    monkeypatch.setattr(socket, 'socket', denied)
    monkeypatch.setattr(socket, 'create_connection', denied)


def cli(monkeypatch, *args):
    monkeypatch.setattr(sys, 'argv', ['run_comparison.py', *args])
    r.main()


def test_repeat_five_prepare_real_context(monkeypatch, tmp_path, capsys):
    job = tmp_path / 'parent/../r5'
    cli(monkeypatch, '--prepare-only', '--strategy', 'C', '--repeat', '5', '--job', str(job))
    out = json.loads(capsys.readouterr().out)
    assert out['repeat'] == 5 and out['prepared_cases'] == 54
    assert out['credential_reads'] == out['remote_calls'] == 0
    assert out['job'] == str(job.resolve())
    assert not (tmp_path / 'r5').exists()


@pytest.mark.parametrize('value', ['0', '-1'])
def test_invalid_repeat(monkeypatch, value):
    with pytest.raises(SystemExit) as error:
        cli(monkeypatch, '--prepare-only', '--strategy', 'C', '--repeat', value)
    assert error.value.code == 2


@pytest.mark.parametrize('value', ['r4.', 'r5 ', 'parent./job', 'parent /job'])
def test_ambiguous_path_rejected_before_prepare(monkeypatch, tmp_path, value):
    def forbidden(*a):
        raise AssertionError('prepare must not be called')
    monkeypatch.setattr(r, 'prepare', forbidden)
    with pytest.raises(SystemExit) as error:
        cli(monkeypatch, '--prepare-only', '--strategy', 'C', '--job', str(tmp_path / value))
    assert error.value.code == 2
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize('fence', ['inflight.json', 'state.pending', 'STOP.json'])
def test_prepare_preserves_existing_fences(monkeypatch, tmp_path, fence, capsys):
    job = tmp_path / 'existing'
    job.mkdir()
    path = job / fence
    path.write_bytes(b'protected fence')
    before = {p.name: p.read_bytes() for p in job.iterdir()}
    cli(monkeypatch, '--prepare-only', '--strategy', 'C', '--repeat', '5', '--job', str(job))
    assert json.loads(capsys.readouterr().out)['remote_calls'] == 0
    assert {p.name: p.read_bytes() for p in job.iterdir()} == before
