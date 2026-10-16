import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import document_selection as ds  # noqa: E402
from source_spans import candidates  # noqa: E402


def test_char_grams_bridge_languages_and_keep_numbers():
    de = set(ds.char_grams("Pestizide 2027"))
    it = set(ds.char_grams("pesticidi 2027"))
    assert "2027" in de and de & it


def test_claim_span_pages_keeps_overview_and_top_spans_verbatim():
    pages = ("", "", "4 Vorlage Alpha In Kürze.", "5 Frage.", "10 Verkehr und Strassen.", "11 Pestizide sind ab 2027 verboten.", "12 Argumente zu Steuern.", "13 Ende.")
    selected = [2, 3, 4, 5, 6, 7]
    spans = candidates(pages)
    reduced, meta = ds.claim_span_pages(pages, selected, "I pesticidi sono vietati dal 2027.", spans, 1)
    assert reduced[2] == pages[2] and reduced[3] == pages[3]
    assert reduced[5] == pages[5] and reduced[4] == "" and reduced[6] == ""
    assert meta["kept_pages"] == [3, 4, 6]
    assert all(text in page or text == "" for text, page in zip(reduced, pages))


def test_claim_pages_keeps_whole_pages_with_neighbours():
    pages = ("", "", "4 Vorlage Alpha In Kürze.", "5 Frage.", "10 Verkehr und Strassen.", "11 Pestizide sind ab 2027 verboten.", "12 Argumente zu Steuern.", "13 Ende.")
    reduced, meta = ds.claim_pages(pages, [2, 3, 4, 5, 6, 7], "I pesticidi sono vietati dal 2027.", candidates(pages), 1)
    assert meta["kept_pages"] == [3, 4, 5, 6, 7]
    assert reduced[4] == pages[4] and reduced[5] == pages[5] and reduced[6] == pages[6] and reduced[7] == ""
