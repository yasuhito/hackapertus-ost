"""Offline format contracts. Historical evidence uses source only, never gold."""
import hashlib
import json
from pathlib import Path
import sys

import pytest

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / 'track_2a/src'))
import predict
import source_spans
import submission

CASE = {'id': 'test', 'reference': {'text': 'Original.'}, 'claim': {'text': 'Original.'}}
PAGES = ('Original.',)
ID = source_spans.candidates(PAGES, True)[0]['span_id']
METRICS = {'input_tokens': 20, 'output_tokens': 8, 'inference_time_ms': 1.5}


def test_saved_33_reproduce_then_normalize_27_reject_6():
    directory = REPO / 'output/cscs/dev54-v2'
    if not directory.exists():
        pytest.skip('saved source-only evidence not installed')
    manifest = json.loads((directory / 'manifest.json').read_text())
    rows = json.loads((REPO / 'output/cscs/format-error-diagnostics.json').read_text())['rows']
    accepted = rejected = 0
    assert len(rows) == 33
    for row in rows:
        path = REPO / row['path']
        assert hashlib.sha256(path.read_bytes()).hexdigest() == row['sha256']
        raw = json.loads(path.read_text())['raw_output']
        item = manifest['frozen'][row['index']]
        with pytest.raises(ValueError, match='evidence ID object'):
            predict.decode(raw, item['pages'], 'reference' in item['case'])
        try:
            result = submission.assemble_text(raw, item['case'], item['pages'], METRICS)
            submission.validate(result, item['case'], item['pages'])
            accepted += 1
        except ValueError:
            rejected += 1
    assert (accepted, rejected) == (27, 6)


@pytest.mark.parametrize('label', [0, 1, 2, '0', '1', '2', 'entailment', 'neutral', 'contradiction'])
def test_exact_label_mapping(label):
    result = submission.assemble_text(json.dumps({'label': label, 'evidence': [ID]}), CASE, PAGES, METRICS)
    assert result['label'] == submission.LABEL_MAP.get(label, label)


@pytest.mark.parametrize('raw', [
    '{"label":0,"label":1,"evidence":[]}',
    '{"label":1,"evidence":[{"span_id":"x","span_id":"y"}]}',
    '```json\n{"label":1,"evidence":[]}\n```',
    'Here is {"label":1,"evidence":[]}',
    '{"label":1,"evidence":[]} {}',
    '{"label":1,"evidence":[],"extra":0}',
] + [json.dumps({'label': x, 'evidence': []}) for x in [True, False, 1.0, None, 'Neutral', ' 1', 'unknown']])
def test_reject_malformed(raw):
    with pytest.raises(ValueError):
        submission.assemble_text(raw, CASE, PAGES, METRICS)


@pytest.mark.parametrize('evidence', [[ID, {'span_id': ID}], [ID, ID], ['unknown'], [{'span_id': ID, 'text': 'Original.'}], [False]])
def test_reject_evidence(evidence):
    with pytest.raises(ValueError):
        submission.assemble_text(json.dumps({'label': 0, 'evidence': evidence}), CASE, PAGES, METRICS)


def test_tool_and_text_same_authoritative_assembler():
    a = submission.assemble_text(json.dumps({'label': 'entailment', 'evidence': [ID]}), CASE, PAGES, METRICS)
    b = submission.assemble_tool({'label': 0, 'candidate_ids': [ID]}, CASE, PAGES, METRICS)
    assert a == b
    for args in [{'label': '0', 'candidate_ids': [ID]}, {'label': True, 'candidate_ids': []}, {'label': 0, 'candidate_ids': [ID], 'extra': 1}]:
        with pytest.raises(ValueError):
            submission.assemble_tool(args, CASE, PAGES, METRICS)


@pytest.mark.parametrize('mutate', [lambda r: r.update(id='other'), lambda r: r.update(extra=1), lambda r: r['metrics'].update(extra=0), lambda r: r['metrics'].update(input_tokens=True), lambda r: r['metrics'].update(output_tokens=1.5), lambda r: r['metrics'].update(inference_time_ms=float('nan'))])
def test_full_canonical_schema(mutate):
    result = submission.assemble_tool({'label': 0, 'candidate_ids': [ID]}, CASE, PAGES, METRICS)
    mutate(result)
    with pytest.raises(ValueError):
        submission.validate(result, CASE, PAGES)
