import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import document_selection as ds  # noqa: E402


@pytest.mark.parametrize("claim,kind", [
    ("Le résumé précise qu’en 2021, 58 % des votants ont approuvé l’initiative.", "summary"),
    ("Laut der Zusammenfassung sieht die Vorlage eine Senkung vor.", "summary"),
    ("Nel riassunto si sostiene che la legge entra in vigore nel 2027.", "summary"),
    ("Das Komitee vertritt die Auffassung, dass die Steuern steigen.", "committee"),
    ("Il comitato afferma che l’iniziativa danneggia l’economia.", "committee"),
    ("Le Conseil fédéral préconise que la Suisse ratifie l’accord.", "council"),
    ("Der Bundesrat spricht sich dafür aus, die Vorlage abzulehnen.", "council"),
    ("Stando al testo di voto, il Consiglio federale copre i costi.", "votetext"),
    ("Laut dem Abstimmungstext empfiehlt die Bundesversammlung die Ablehnung.", "votetext"),
    ("Selon le texte soumis au vote, l’article 1 est modifié.", "votetext"),
    ("Wird die Abstimmung angenommen, ist der Import verboten.", "ifadopted"),
    ("Se il voto viene accettato, l’età di pensionamento sale.", "ifadopted"),
    ("Die Schweiz importiert drei Viertel ihrer Energie.", "other"),
])
def test_claim_kind_from_attributive_opening(claim, kind):
    assert ds.claim_kind(claim) == kind


def booklet():
    return ("Umschlag", "3 Inhalt",
            "4 Erste Vorlage: Alpha In Kürze Die Vorlage senkt Steuern.",
            "5 Wollen Sie die Vorlage annehmen?",
            "10 Erste Vorlage: Alpha Argumente Initiativkomitee 1 4 Argumente Bundesrat und Parlament 1 6 Abstimmungstext 1 8 AlphaIm Detail Ausgangslage.",
            "11 Fortsetzung der Ausgangslage ohne Kopfzeile.",
            "14 Erste Vorlage: Alpha\nInitiativkomitee\nDie Steuern steigen massiv.",
            "15 Weitere Argumente des Komitees.",
            "16\nBundesrat und Parlament\nDie Steuern sinken für Familien.",
            "17 Weitere Argumente von Bundesrat und Parlament.",
            "18 § Erste Vorlage: Alpha Abstimmungstext Bundesgesetz Art. 1",
            "§ 19 Art. 2 Die Abgabe beträgt 2 Prozent.")


def test_page_sections_use_last_marker_and_inherit():
    labels = ds.page_sections(booklet(), list(range(2, 12)))
    assert [labels[i] for i in range(2, 12)] == [
        "overview", "overview", "detail", "detail", "committee", "committee", "council", "council", "votetext", "votetext"]


def test_section_prior_prefers_the_claimed_speaker():
    pages = booklet()
    selected = list(range(2, 12))
    paras = ds.paragraphs(pages, selected)
    sections = ds.page_sections(pages, selected)
    committee = ds.rank_paragraphs("Das Komitee vertritt die Auffassung, dass die Steuern steigen.", paras, None, None, sections, "committee", "first")
    council = ds.rank_paragraphs("Der Bundesrat vertritt die Ansicht, dass die Steuern sinken.", paras, None, None, sections, "council", "first")
    assert sections[paras[committee[0]]["page"] - 1] in ("committee", "detail", "overview", "arguments")
    assert sections[paras[council[0]]["page"] - 1] in ("council", "detail", "overview", "arguments")
    assert all(sections[paras[i]["page"] - 1] != "council" for i in committee[:3])


def test_paragraph_context_without_prior_is_unchanged_api():
    pages = booklet()
    reduced, meta = ds.paragraph_context(pages, list(range(2, 12)), "Laut dem Abstimmungstext beträgt die Abgabe 2 Prozent.", 2, section_prior=True)
    assert 12 in meta["kept_pages"] or 11 in meta["kept_pages"]
    assert all(text == "" or any(part in pages[i] for part in text.split("\n\n\n")) for i, text in enumerate(reduced))


def test_toc_sections_map_printed_numbers_to_physical_pages():
    pages = ("Umschlag", "3 Inhalt",
             "8 Dritte Vorlage: Alpha In Kürze.", "9 Frage.",
             "32 Dritte Vorlage: Alpha Im Detail\nArgumente Initiativkomitee 3 6\nArgumente Bundesrat und Parlament 3 8\nAbstimmungstext 4 0\nAusgangslage.",
             "33 Fortsetzung.", "34 Dritte Vorlage: Alpha Weiter.", "35",
             "36 Dritte Vorlage: Alpha\nText ohne Kopfzeile des Komitees.", "37 Fortsetzung.",
             "38 Dritte Vorlage: Alpha\nText ohne Kopfzeile von Bundesrat und Parlament.", "39 Fortsetzung.",
             "40 Dritte Vorlage: Alpha Abstimmungstext Bundesbeschluss", "41 Art. 2")
    selected = [2, 3] + list(range(4, 14))
    assert {k: v + 1 for k, v in ds.toc_sections(pages, selected).items()} == {"committee": 9, "council": 11, "votetext": 13}
    labels = ds.page_sections(pages, selected)
    assert [labels[i] for i in selected] == ["overview", "overview", "detail", "detail", "detail", "detail",
                                            "committee", "committee", "council", "council", "votetext", "votetext"]


def test_heading_lines_drop_running_header_and_contents():
    text = "36 Dritte Vorlage: Alpha\nArgumente Initiativkomitee 1 4\nAbstimmungstext 1 8\nArgumente Initiativkomitee\nJa, folgende Frage."
    assert ds.heading_lines(text)[0] == "argumente initiativkomitee"
