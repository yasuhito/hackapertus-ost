import json
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))
from source_spans import candidates, restore, MAX_SPAN, speaker_heading


def response(span_ids, label=0):
    return json.dumps({"label": label, "evidence": [{"span_id": i} for i in span_ids]})


def test_exact_original_unicode_page_and_offsets():
    pages = ("", "Nein.\nDas gilt nicht. Café ﬁ 12–14 ³\n")
    spans = candidates(pages)
    label, evidence = restore(response([spans[0]["span_id"]]), pages)
    assert label == 0
    assert evidence == [{"page": 2, "text": pages[1]}]
    assert pages[1][spans[0]["start"]:spans[0]["end"]] == spans[0]["text"]


def test_complete_coverage_and_quote_cap():
    text = ("Une phrase française.\nUne seconde phrase.\n\n" * 200) + "X" * 1500
    spans = candidates((text,))
    assert "".join(s["text"] for s in spans) == text
    assert all(0 < len(s["text"]) <= MAX_SPAN <= 5000 for s in spans)
    assert candidates((text,)) == spans


def test_b_has_null_page_without_copying_model_text():
    pages = ("La proposition est refusée.",)
    span = candidates(pages, reference=True)[0]
    assert restore(response([span["span_id"]], 2), pages, True) == (2, [{"page": None, "text": pages[0]}])


@pytest.mark.parametrize("bad", ["unknown", "", 1, None])
def test_invalid_id(bad):
    with pytest.raises(ValueError):
        restore(json.dumps({"label": 0, "evidence": [{"span_id": bad}]}), ("Original.",))


def test_wrong_page_stale_source_and_unprovided_page():
    pages = ("Original page one.", "A different page.")
    first = candidates(pages)[0]["span_id"]
    with pytest.raises(ValueError):
        restore(response([first.replace("p0001", "p0002")]), pages)
    with pytest.raises(ValueError):
        restore(response([first]), ("Changed page one.", pages[1]))
    second = candidates(pages)[1]["span_id"]
    with pytest.raises(ValueError):
        restore(response([second]), (pages[0], ""))


@pytest.mark.parametrize("reference", [False, True])
@pytest.mark.parametrize("label", [0, 2])
def test_missing_support_is_failure(label, reference):
    with pytest.raises(ValueError, match="supporting span"):
        restore(response([], label), ("Original.",), reference)


def test_neutral_can_omit_evidence():
    assert restore(response([], 1), ("Original.",)) == (1, [])


def test_model_cannot_supply_page_offset_or_text():
    span = candidates(("Original.",))[0]["span_id"]
    for extra in [{"text": "Fabricated"}, {"page": 2}, {"start": 9}]:
        with pytest.raises(ValueError):
            restore(json.dumps({"label": 0, "evidence": [{"span_id": span, **extra}]}), ("Original.",))


def test_duplicates_and_excessive_evidence_fail():
    pages = ("Original.",)
    span = candidates(pages)[0]["span_id"]
    for ids in [[span, span], [span] * 6]:
        with pytest.raises(ValueError):
            restore(response(ids), pages)


@pytest.mark.parametrize("obj", [{"label": True, "evidence": []}, {"label": 3, "evidence": []},
                                  {"label": 1, "evidence": [], "extra": 1},
                                  {"label": 1, "evidence": {}}, []])
def test_strict_schema(obj):
    with pytest.raises(ValueError):
        restore(json.dumps(obj), ("Original.",))


def test_empty_or_whitespace_source_cannot_supply_ids():
    assert candidates(("", " \n ")) == []
    with pytest.raises(ValueError):
        restore(response(["p0001-o0000000-e0000001-000000000000"]), ("",))


def test_reference_closure_retains_antecedent_and_attribution():
    source = "Le comité estime que le contrat doit être résilié.\n" + "Texte explicatif. " * 90 + "\nDans ce cas, les autres accords cessent."
    span = candidates((source,), True)[-1]
    assert restore(response([span['span_id']]), (source,), True)[1] == [{'page':None,'text':source}]


def test_physical_page_closure_keeps_following_purpose():
    source = "Die Kantone dürfen vorbeugen. " + "Weitere Erklärung. " * 85 + "Der Zweck ist der Schutz der Herden."
    span = candidates((source,))[0]
    assert restore(response([span['span_id']]), (source,))[1] == [{'page':1,'text':source}]


def test_speaker_block_keeps_recommendation_and_distinct_opponent():
    pages=('Gli Comitato referendario\nWir lehnen die Privatisierung ab.',
           'Il comitato referendario raccomanda di votare: No.',
           'Consiglio federale e Parlamento\nWir unterstützen die Vorlage.',
           'Consiglio federale e Parlamento raccomandano: Sì.')
    spans=candidates(pages)
    output=restore(response([spans[0]['span_id'],spans[3]['span_id']],2),pages)[1]
    assert output == [{'page':n,'text':pages[n-1]} for n in (1,2,3,4)]
    assert speaker_heading('Im Text wird das Komitee erwähnt.') is None


def test_context_closure_never_reads_masked_page():
    pages=('Comitato referendario\nArgomento.', '', 'Consiglio federale e Parlamento\nAltro.')
    output=restore(response([candidates(pages)[0]['span_id']]),pages)[1]
    assert output == [{'page':1,'text':pages[0]}]


def test_closure_limits_fail_instead_of_truncating():
    pages=tuple('Comitato referendario\nA.' if n%2==0 else 'Conclusione.' for n in range(6))
    spans=candidates(pages)
    with pytest.raises(ValueError,match='five'):
        restore(response([spans[n]['span_id'] for n in (0,2,4)]),pages)
    large=('A'*5001,)
    with pytest.raises(ValueError,match='5000'):
        restore(response([candidates(large)[0]['span_id']]),large)


def test_regions_restore_and_absolute_offsets():
    from source_spans import REGION_BREAK
    first = 'Original first. ' * 100
    second = 'Original second.'
    pages = (first + REGION_BREAK + second,)
    spans = candidates(pages)
    assert all(REGION_BREAK not in s['text'] and pages[0][s['start']:s['end']] == s['text'] for s in spans)
    assert restore(response([spans[0]['span_id']]), pages)[1] == [{'page': 1, 'text': first}]
    assert restore(response([spans[-1]['span_id']]), pages)[1] == [{'page': 1, 'text': second}]
    oversized = ('Long sentence. ' * 400) + REGION_BREAK + second
    span = candidates((oversized,))[0]
    assert restore(response([span['span_id']]), (oversized,))[1] == [{'page': 1, 'text': span['text']}]
