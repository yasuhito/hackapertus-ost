"""Synthetic-only selection and preparation guards. Never contacts a provider."""
import copy
from pathlib import Path
import socket
import sys
import pytest

sys.path.insert(0, str(Path(__file__).parent))
import prepare_role_review_data as d


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError('network forbidden in fictional preparation test')
    monkeypatch.setattr(socket, 'socket', forbidden)
    monkeypatch.setattr(socket, 'create_connection', forbidden)


def rows(n=180):
    return [{'booklet_publish_date': '2026-01-01', 'booklet_url': f'https://www.bk.admin.ch/fake/{i//4}.pdf',
             'claim': f'Claim {i}', 'claim_language': 'de', 'reference_string': f'Source {i}',
             'reference_language': 'fr', 'vote': f'Vote {i}', 'entailment_label': i % 3, 'baseline_score': .5}
            for i in range(n)]


class NoGold(dict):
    def __getitem__(self, key):
        if key in ('entailment_label', 'baseline_score', 'prediction'):
            raise AssertionError('selection accessed forbidden score/label')
        return super().__getitem__(key)


def test_selection_is_input_only_repeatable_and_reserves_confirmation():
    value = [NoGold(r) for r in rows()]
    before = copy.deepcopy(value)
    a = d.select_inputs(value, {0, 1})
    assert a == d.select_inputs(value, {0, 1}) and value == before
    assert len(a) == 60 and [p['section'] for p in a] == ['dev']*30 + ['confirm']*30
    assert len({p['group_digests']['claim'] for p in a}) == 60
    assert len({p['group_digests']['reference'] for p in a}) == 60
    assert [p['rank_sha256'] for p in a] == sorted(p['rank_sha256'] for p in a)
    assert all(p['source_index'] not in {0, 1} for p in a)
    for p in a:
        assert p['case_ids'] == [f'ost-role-review-{p["section"]}-{p["source_index"]:04d}-{t}' for t in ('A','B')]


def test_labels_predictions_and_confidence_cannot_change_selection():
    a = rows(); b = copy.deepcopy(a)
    for r in b:
        r['entailment_label'] = object(); r['baseline_score'] = object(); r['prediction'] = object()
    assert d.select_inputs(a, {0}) == d.select_inputs(b, {0})


def test_known_claim_and_reference_groups_are_excluded():
    value = rows()
    value[2]['claim'] = '  CLAIM  0  '
    value[3]['reference_string'] = 'source\u00ad 0'
    pins = d.select_inputs(value, {0})
    assert not {0, 2, 3}.intersection(p['source_index'] for p in pins)


def test_duplicate_claim_and_reference_never_cross_development_and_confirmation():
    value = rows()
    value[2]['claim'] = value[1]['claim']
    value[4]['reference_string'] = value[3]['reference_string']
    pins = d.select_inputs(value, set())
    assert len({p['group_digests']['claim'] for p in pins}) == 60
    assert len({p['group_digests']['reference'] for p in pins}) == 60


def test_insufficient_pool_stops_without_replacement():
    with pytest.raises(ValueError, match='INSUFFICIENT_INPUT_ONLY_POOL'):
        d.select_inputs(rows(59), set())


def test_exclusive_write_does_not_overwrite(tmp_path):
    path = tmp_path / 'record.json'
    d.exclusive(path, {'a': 1})
    before = path.read_bytes()
    with pytest.raises(FileExistsError):
        d.exclusive(path, {'a': 2})
    assert path.read_bytes() == before
    assert path.stat().st_mode & 0o777 == 0o600


def test_source_hash_mismatch_stops_before_parsing(tmp_path, monkeypatch):
    target = tmp_path / 'track_2a/data/source.jsonl'
    target.parent.mkdir(parents=True)
    target.write_bytes(b'not a dataset')
    monkeypatch.setattr(d, 'ROOT', tmp_path)
    with pytest.raises(ValueError, match='SOURCE_CHANGED'):
        d.source_rows()


def test_partial_or_complete_bundle_is_not_resumed(tmp_path, monkeypatch):
    monkeypatch.setattr(d, 'DEST', tmp_path)
    (tmp_path / 'preparation-start.json').write_text('{}')
    with pytest.raises(ValueError, match='PARTIAL_PREPARATION_NO_IMPLICIT_RESUME'):
        d.complete()
    (tmp_path / 'selection-manifest.json').write_text('{}')
    with pytest.raises(ValueError, match='COMPLETE_BUNDLE_ALREADY_EXISTS'):
        d.complete()


def test_only_http_proven_cache_records_are_eligible():
    proof = {'status': 200, 'headers': {}, 'url': 'fake'}
    assert d.http_receipt({'original_receipt': {'original_receipt': proof}}) == proof
    assert d.http_receipt({'verified': True, 'sha256': 'hash-only'}) is None
