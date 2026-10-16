"""Authoritative deterministic text/tool submission assembly. No semantic repair."""
import json
import math

from document_selection import rank_pages, char_grams, bm25_scores
from predict import LABELS, validate_prediction
from source_spans import candidates, restore, regions, REGION_BREAK

MAX_EVIDENCE = 5
MAX_EVIDENCE_CHARS = 5000

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
    if not isinstance(ids, list) or any(type(x) is not str for x in ids):
        raise ValueError('IDS_SCHEMA')
    # A repeated ID is the same citation; drop repeats instead of a repair round trip.
    ids = list(dict.fromkeys(ids))
    if len(ids) > 5:
        raise ValueError('IDS_SCHEMA')
    index = {x['span_id'] for x in candidates(pages, 'reference' in case)}
    if any(x not in index for x in ids):
        raise ValueError('UNKNOWN_ID')
    label, evidence = restore(json.dumps({'label': label, 'evidence': [{'span_id': x} for x in ids]}), pages, 'reference' in case)
    if 'reference' not in case:
        evidence = consulted_pages(evidence, case, pages)
    return validate({'id': case['id'], 'label': label, 'label_name': LABELS[label], 'evidence': evidence, 'metrics': dict(metrics)}, case, pages)


def neighbours(numbers, provided):
    """Pages adjacent to the cited ones, in citation order. Gold passages often
    continue on the facing page of the one the model picked."""
    out = []
    for n in numbers:
        for m in (n + 1, n - 1):
            if m in provided and m not in out:
                out.append(m)
    return out


def consulted_pages(evidence, case, pages):
    """Fill the evidence list with the provided pages most relevant to the claim.

    The model's own citations stay first, then the pages adjacent to them, then
    the vote's opening spread (the first two provided pages) because it
    summarizes the proposal, then the remaining provided pages in
    lexical-relevance order. Pages longer than the
    scoring limit are skipped. This is deterministic retrieval over the pages the
    model saw; it never changes the label or the cited passages.
    """
    if any(REGION_BREAK in text for text in pages):
        provided_regions = [(n, text) for n, source in enumerate(pages, 1)
                            for _, _, text in regions(source)]
        cited = [i for item in evidence for i, (n, text) in enumerate(provided_regions)
                 if item['page'] == n and item['text'] in text]
        adjacent = sorted({j for i in cited for j in (i - 1, i + 1)
                           if 0 <= j < len(provided_regions)
                           and provided_regions[j][0] == provided_regions[i][0]})
        scores = bm25_scores(char_grams(case['claim']['text']),
                             [char_grams(text) for _, text in provided_regions])
        ranked = sorted(range(len(scores)), key=lambda i: (-scores[i], i))
        result = []
        for i in cited + adjacent + ranked:
            n, text = provided_regions[i]
            items = ([{'page': n, 'text': text}] if len(text) <= MAX_EVIDENCE_CHARS else
                     [item for item in evidence if item['page'] == n and item['text'] in text])
            for item in items:
                if item not in result:
                    result.append(item)
        return result[:MAX_EVIDENCE]
    provided = [n for n, text in enumerate(pages, 1) if text.strip() and len(text) <= MAX_EVIDENCE_CHARS]
    cited = [item['page'] for item in evidence]
    ordered = neighbours(cited, provided) + provided[:2] + rank_pages(case['claim']['text'], pages, provided[2:])
    seen = set(cited)
    extra = []
    for n in ordered:
        if n not in seen:
            seen.add(n)
            extra.append({'page': n, 'text': pages[n - 1]})
    return (evidence + extra)[:MAX_EVIDENCE]


def assemble_text(raw, case, pages, metrics):
    return assemble_tool(text_args(raw), case, pages, metrics)


def fallback(case, pages, metrics):
    """Canonical placeholder. Caller MUST persist NO_ACCEPTED_SUBMIT sidecar."""
    return assemble_tool({'label': 1, 'candidate_ids': []}, case, pages, metrics)
