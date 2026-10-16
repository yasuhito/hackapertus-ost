import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import submission  # noqa: E402
from source_spans import candidates  # noqa: E402


def booklet_case(pages):
    return {"id": "synthetic", "claim": {"text": "Die Reform senkt die Steuern für Familien ab 2027.", "language": "de"},
            "booklet": {"path": "synthetic.pdf", "language": "de"}, "vote": "Steuerreform"}, pages


def metrics():
    return {"input_tokens": 0, "output_tokens": 0, "inference_time_ms": 0}


def test_cited_page_first_then_opening_spread_then_relevance_order():
    pages = ("", "", "4 Steuerreform In Kürze: Die Reform betrifft Familien.", "5 Wollen Sie die Reform annehmen?",
             "10 Im Detail: Unbeteiligter Abschnitt über Verkehr.", "11 Die Steuern für Familien sinken ab 2027.",
             "12 Argumente des Komitees zu Steuern.", "13 Abstimmungstext.")
    case, pages = booklet_case(pages)
    cited = candidates(pages)
    span = next(s for s in cited if s["page"] == 7)
    result = submission.assemble_tool({"label": 0, "candidate_ids": [span["span_id"]]}, case, pages, metrics())
    assert result["label"] == 0
    # Cited page, its neighbours, then paragraph-ranked regions (the claim's
    # own paragraph on page 6 scores higher than the opening spread), then pages.
    assert [item["page"] for item in result["evidence"]] == [7, 8, 6, 3, 5]
    assert all(item["text"] in pages[item["page"] - 1] for item in result["evidence"])


def test_neutral_and_fallback_answers_carry_consulted_pages_without_changing_label():
    pages = ("", "", "4 Steuerreform In Kürze.", "5 Frage.", "10 Detail Steuern Familien 2027.")
    case, pages = booklet_case(pages)
    result = submission.fallback(case, pages, metrics())
    assert result["label"] == 1 and result["label_name"] == "neutral"
    assert [item["page"] for item in result["evidence"]] == [3, 4, 5]


def test_non_neutral_without_citation_is_still_rejected():
    import pytest
    case, pages = booklet_case(("", "4 Steuerreform In Kürze.", "5 Frage."))
    with pytest.raises(ValueError, match="supporting span required"):
        submission.assemble_tool({"label": 2, "candidate_ids": []}, case, pages, metrics())


def test_oversized_pages_are_skipped_and_at_most_five_items():
    pages = ("", "4 Kurz.", "5 Frage.", "x" * 5001, "7 Steuern Familien.", "8 Mehr Steuern.", "9 Noch mehr.", "10 Ende.")
    case, pages = booklet_case(pages)
    result = submission.fallback(case, pages, metrics())
    numbers = [item["page"] for item in result["evidence"]]
    assert len(numbers) == 5 and 4 not in numbers and numbers[:2] == [2, 3]


def test_reference_task_evidence_is_untouched():
    case = {"id": "synthetic", "claim": {"text": "Ja.", "language": "de"}, "reference": {"text": "Ja. Nein.", "language": "de"}}
    pages = (case["reference"]["text"],)
    result = submission.assemble_tool({"label": 1, "candidate_ids": []}, case, pages, metrics())
    assert result["evidence"] == []


def test_duplicate_ids_are_merged_instead_of_rejected():
    pages = ("", "4 Steuerreform In Kürze.", "5 Frage.", "10 Detail Steuern Familien 2027.")
    case, pages = booklet_case(pages)
    span = candidates(pages)[-1]["span_id"]
    result = submission.assemble_tool({"label": 2, "candidate_ids": [span, span]}, case, pages, metrics())
    assert result["label"] == 2 and [i["page"] for i in result["evidence"]][0] == 4


def test_neighbouring_pages_follow_the_citation():
    pages = ("", "", "4 Steuerreform In Kürze.", "5 Frage.", "10 Verkehr.", "11 Steuern Familien 2027.", "12 Fortsetzung.", "13 Ende.")
    case, pages = booklet_case(pages)
    span = next(s for s in candidates(pages) if s["page"] == 6)
    result = submission.assemble_tool({"label": 0, "candidate_ids": [span["span_id"]]}, case, pages, metrics())
    assert [i["page"] for i in result["evidence"]] == [6, 7, 5, 3, 4]


def test_reduced_pages_pad_regions_cited_then_adjacent_then_lexical():
    from source_spans import REGION_BREAK
    pad = ' Dieser Absatz ist lang genug, um als Belegstelle zu gelten.'
    texts = [x + pad for x in ['Opening.', 'Before.', 'Cited.', 'After.', 'Steuern Familien 2027.', 'Other.']]
    pages = (REGION_BREAK.join(texts), 'Unrelated page.')
    case, _ = booklet_case(pages)
    evidence = [{'page': 1, 'text': texts[2]}]
    padded = submission.consulted_pages(evidence, case, pages)
    assert [item['text'] for item in padded[:4]] == [texts[2], texts[1], texts[3], texts[4]]
    assert len(padded) == 5
    assert all(item['text'] in pages[item['page'] - 1] and REGION_BREAK not in item['text'] for item in padded)
    assert len({(x['page'], x['text']) for x in padded}) == 5


def test_region_padding_skips_bare_fragments():
    from source_spans import REGION_BREAK
    page = "4 Steuerreform In Kürze. Die Reform senkt die Steuern für Familien ab 2027." + REGION_BREAK + "2323" + REGION_BREAK + "Argumente des Komitees zu Steuern und Familien, ausführlich dargestellt."
    pages = ("", "", page)
    case, pages = booklet_case(pages)
    result = submission.fallback(case, pages, metrics())
    assert all(len(item["text"].strip()) >= 40 for item in result["evidence"])
    assert len(result["evidence"]) == 2
