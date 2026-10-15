"""Recovery tests use only fictional captures, with sockets and credentials blocked."""
import copy
import os
from pathlib import Path
import socket
import stat
import sys
from unittest.mock import Mock

import pytest

sys.path.insert(0, str(Path(__file__).parent))
import provider_schema_probe_recovery as r


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def forbidden(*_a, **_k):
        raise AssertionError('NETWORK_OR_CREDENTIAL_READ')
    monkeypatch.setattr(socket, 'socket', forbidden)
    monkeypatch.setattr(socket, 'create_connection', forbidden)
    runner = r.old.root_runner()
    monkeypatch.setattr(runner.legacy.c, 'read_key', forbidden)
    monkeypatch.setattr(r.old, 'root_runner', lambda: runner)
    monkeypatch.setattr(r.old, 'Transport', forbidden)


def test_original_replace_bug_red(tmp_path):
    path = tmp_path / 'context.json'
    r.old.save(path, {'old': True})
    with pytest.raises(FileNotFoundError):
        r.old.save(path, {'new': True}, replace=True)
    assert r.old.load(path) == {'new': True}


def test_replacement_green_private_and_fsynced(tmp_path, monkeypatch):
    path = tmp_path / 'context.json'
    path.write_text('{}')
    real_fsync = os.fsync
    kinds = []
    def fsync(fd):
        kinds.append(stat.S_IFMT(os.fstat(fd).st_mode))
        real_fsync(fd)
    monkeypatch.setattr(os, 'fsync', fsync)
    r.save(path, {'new': True}, replace=True)
    assert r.old.load(path) == {'new': True}
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    assert kinds == [stat.S_IFREG, stat.S_IFDIR]
    assert list(tmp_path.iterdir()) == [path]


def test_exclusive_publication_and_symlink_refusal(tmp_path):
    path = tmp_path / 'report.json'
    r.save(path, {})
    with pytest.raises(FileExistsError):
        r.save(path, {'overwrite': True})
    link = tmp_path / 'link'
    link.symlink_to(path)
    with pytest.raises(ValueError, match='SYMLINK_REFUSED'):
        r.save(link, {}, replace=True)
    assert not list(tmp_path.glob('.pending-*'))


def test_replace_failure_propagates(tmp_path, monkeypatch):
    path = tmp_path / 'context.json'
    path.write_text('{}')
    def fail(*_):
        raise OSError('replacement failed')
    monkeypatch.setattr(os, 'replace', fail)
    with pytest.raises(OSError, match='replacement failed'):
        r.save(path, {'new': True}, replace=True)
    assert r.old.load(path) == {}
    assert not list(tmp_path.glob('.pending-*'))


def test_original_pinsets_and_artifacts():
    frozen = r.protocol()
    assert frozen['original_control_sha256'] == r.old.sha(r.old.CONTROL.read_bytes())
    assert len(frozen['original_artifacts']) == 26
    for original, archive in r.ARCHIVES.items():
        assert r.old.sha(archive.read_bytes()) == r.old.load(r.old.CONTROL)['sources'][original]


@pytest.mark.parametrize('target', ['archive', 'original', 'new', 'artifact'])
def test_changed_pin_rejected_before_scoring(tmp_path, monkeypatch, target):
    control = tmp_path / 'protocol.json'
    r.save(control, r.protocol())
    monkeypatch.setattr(r, 'CONTROL', control)
    scorer = Mock(side_effect=AssertionError('SCORING_BEFORE_PIN_VALIDATION'))
    monkeypatch.setattr(r.old, 'check', scorer)
    if target in ('archive', 'original'):
        original = r.old.load(r.old.CONTROL)
        original = copy.deepcopy(original)
        key = next(iter(r.ARCHIVES)) if target == 'archive' else str(r.ROOT / '.auto/provider_schema_probe.py')
        original['sources'][key] = '0' * 64
        old_control = tmp_path / 'old-control.json'
        r.save(old_control, original)
        monkeypatch.setattr(r.old, 'CONTROL', old_control)
    elif target == 'new':
        changed = tmp_path / 'changed.py'
        changed.write_text('changed')
        monkeypatch.setattr(r, 'SOURCES', r.SOURCES + [changed])
    else:
        data = r.old.load(control)
        key = next(iter(data['original_artifacts']))
        data['original_artifacts'][key] = '0' * 64
        r.save(control, data, replace=True)
    with pytest.raises(ValueError, match='SOURCE_CHANGED|PROTOCOL_OR_SOURCE_CHANGED'):
        r.execute_report()
    scorer.assert_not_called()


def test_offline_report_and_recheck_nonzero_is_valid(tmp_path, monkeypatch, capsys):
    before = r.digests(sorted(r.old.JOB.iterdir()))
    monkeypatch.setattr(r, 'CONTROL', tmp_path / 'recovery-protocol.json')
    monkeypatch.setattr(r, 'JOB', tmp_path / 'recovery')
    monkeypatch.setattr(r.old, 'CONTEXT', tmp_path / 'context.json')
    r.save(r.old.CONTEXT, {'old': True})
    r.save(r.CONTROL, r.protocol())
    report = r.execute_report()
    assert r.check() == report
    result = report['result']
    assert result['schema_contract_violations'] == 3
    assert result['total_tokens'] == 1970
    assert result['prompt_tokens'] == 1520
    assert result['completion_tokens'] == 450
    assert result['missing_field'] == 2 and result['truncation'] == 1
    assert result['exact_copy_mismatch'] == 0
    assert [result['per_model_arm'][model + '/' + arm]['violations']
            for model in r.old.load(r.old.CONTROL)['models']
            for arm in ('simple', 'conditional')] == [0, 0, 0, 3]
    assert result['phase_wall_seconds'] == 17.943960991920903
    assert result['request_wall_seconds'] == 16.553048715926707
    r.print_report(report)
    output = capsys.readouterr().out
    assert 'METRIC schema_contract_violations=3' in output
    assert 'METRIC model70b_conditional_violations=3' in output
    assert 'METRIC requests=12' in output
    with pytest.raises(FileExistsError):
        r.execute_report()
    assert r.digests(sorted(r.old.JOB.iterdir())) == before
    altered = copy.deepcopy(report)
    altered['result']['schema_contract_violations'] = 0
    r.save(r.JOB / 'report.json', altered, replace=True)
    r.save(r.old.CONTEXT, r.context(), replace=True)
    with pytest.raises(ValueError, match='RECOVERY_RESULT_CHANGED'):
        r.check()
