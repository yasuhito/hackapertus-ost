"""Authoritative deterministic text/tool submission assembly. No semantic repair."""
import json
import math

from predict import LABELS, validate_prediction
from source_spans import candidates, restore

LABEL_MAP = {'0': 0, '1': 1, '2': 2, 'entailment': 0, 'neutral': 1, 'contradiction': 2}
METRIC_KEYS = {'input_tokens', 'output_tokens', 'inference_time_ms'}


def strict_json(raw):
    def pairs(values):
        result = {}
        for key, value in values:
            if key in result:
                raise ValueError('DUPLICATE_JSON_KEY')
            result[key] = value
        return result
    def constant(_):
        raise ValueError('NONFINITE_JSON')
    if not isinstance(raw, str):
        raise ValueError('JSON_TEXT_REQUIRED')
    return json.loads(raw, object_pairs_hook=pairs, parse_constant=constant)


def text_args(raw):
    obj = strict_json(raw)
    if not isinstance(obj, dict) or set(obj) != {'label', 'evidence'}:
        raise ValueError('TEXT_SCHEMA')
    label = obj['label']
    if type(label) is str and label in LABEL_MAP:
        label = LABEL_MAP[label]
    if type(label) is not int or label not in LABELS:
        raise ValueError('LABEL_SCHEMA')
    evidence = obj['evidence']
    if not isinstance(evidence, list) or len(evidence) > 5:
        raise ValueError('EVIDENCE_SCHEMA')
    if all(type(x) is str for x in evidence):
        ids = evidence
    elif all(isinstance(x, dict) and set(x) == {'span_id'} and type(x['span_id']) is str for x in evidence):
        ids = [x['span_id'] for x in evidence]
    else:
        raise ValueError('EVIDENCE_SCHEMA')
    return {'label': label, 'candidate_ids': ids}


def validate(result, case, pages):
    if not isinstance(result, dict) or set(result) != {'id', 'label', 'label_name', 'evidence', 'metrics'}:
        raise ValueError('CANONICAL_KEYS')
    if type(result['id']) not in (str, int) or result['id'] == '' or type(result['id']) is not type(case['id']) or result['id'] != case['id']:
        raise ValueError('CANONICAL_ID')
    metrics = result['metrics']
    if not isinstance(metrics, dict) or set(metrics) != METRIC_KEYS:
        raise ValueError('METRICS_KEYS')
    for key in METRIC_KEYS:
        value = metrics[key]
        types = (int, float) if key == 'inference_time_ms' else (int,)
        if type(value) not in types or not math.isfinite(value) or value < 0:
            raise ValueError('METRICS_VALUE')
    validate_prediction(result, pages, reference='reference' in case)
    return result


def assemble_tool(args, case, pages, metrics):
    if not isinstance(args, dict) or set(args) != {'label', 'candidate_ids'}:
        raise ValueError('TOOL_SCHEMA')
    label, ids = args['label'], args['candidate_ids']
    if type(label) is not int or label not in LABELS:
        raise ValueError('LABEL_SCHEMA')
    if not isinstance(ids, list) or len(ids) > 5 or any(type(x) is not str for x in ids):
        raise ValueError('IDS_SCHEMA')
    if len(set(ids)) != len(ids):
        raise ValueError('DUPLICATE_ID')
    index = {x['span_id'] for x in candidates(pages, 'reference' in case)}
    if any(x not in index for x in ids):
        raise ValueError('UNKNOWN_ID')
    label, evidence = restore(json.dumps({'label': label, 'evidence': [{'span_id': x} for x in ids]}), pages, 'reference' in case)
    return validate({'id': case['id'], 'label': label, 'label_name': LABELS[label], 'evidence': evidence, 'metrics': dict(metrics)}, case, pages)


def assemble_text(raw, case, pages, metrics):
    return assemble_tool(text_args(raw), case, pages, metrics)


def fallback(case, pages, metrics):
    """Canonical placeholder. Caller MUST persist NO_ACCEPTED_SUBMIT sidecar."""
    return assemble_tool({'label': 1, 'candidate_ids': []}, case, pages, metrics)
