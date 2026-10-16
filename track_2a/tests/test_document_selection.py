import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import document_selection as ds  # noqa: E402


def booklet():
    """Synthetic three-vote German booklet: cover, contents, overview spreads, detail pages, imprint."""
    return (
        "Volksabstimmung Volksinitiative «Alpha» Erste Vorlage Bundesgesetz Beta Zweite Vorlage Gesetz Gamma Dritte Vorlage",
        "",
        "3 Volksinitiative «Alpha» In Kürze 4 Im Detail 10 Bundesgesetz Beta In Kürze 6 Im Detail 14 Gesetz Gamma In Kürze 8 Erste Vorlage Zweite Vorlage Dritte Vorlage",
        "Volksinitiative «Alpha» 4 Erste Vorlage: Alpha Vorlage im Detail 10 Die Initiative Alpha verlangt etwas.",
        "5 Wollen Sie die Volksinitiative «Alpha» annehmen? Nein Bundesrat und Parlament lehnen die Initiative ab.",
        "Bundesgesetz Beta 6 Zweite Vorlage: Beta Vorlage im Detail 14 Das Gesetz Beta regelt etwas anderes.",
        "7 Wollen Sie das Bundesgesetz Beta annehmen? Ja",
        "Gesetz Gamma 8 Dritte Vorlage: Gamma Vorlage im Detail 18 Gamma ändert etwas.",
        "9 Wollen Sie das Gesetz Gamma annehmen? Ja",
        "10 Erste Vorlage: Alpha Im Detail Ausgangslage der Initiative Alpha.",
        "11 Fortsetzung der Initiative Alpha ohne Kopfzeile.",
        "12 Erste Vorlage: Alpha Argumente Initiativkomitee.",
        "13 Argumente Bundesrat und Parlament zur Initiative Alpha.",
        "14 Zweite Vorlage: Beta Im Detail Ausgangslage des Gesetzes Beta.",
        "15 Fortsetzung Beta.",
        "16 § Zweite Vorlage: Beta Abstimmungstext Bundesgesetz Beta Art. 1",
        "17 § Art. 2 weiterer Gesetzestext.",
        "18 Dritte Vorlage: Gamma Im Detail Gamma.",
        "19 Fortsetzung Gamma.",
        "Erläuterungen des Bundesrates Herausgegeben von der Bundeskanzlei",
    )


def test_page_ordinals_read_running_headers_and_skip_cover_and_contents():
    pages = booklet()
    assert ds.page_ordinals(pages[0]) == [] and ds.page_ordinals(pages[1]) == [] and ds.page_ordinals(pages[2]) == []
    assert ds.page_ordinals(pages[3]) == [1] and ds.page_ordinals(pages[5]) == [2] and ds.page_ordinals(pages[7]) == [3]
    assert ds.page_ordinals(pages[4]) == []
    assert ds.page_ordinals("24 Deuxième et troisième objets : AVS 21 En détail") == [2, 3]
    assert ds.page_ordinals("14 Primo e secondo oggetto: Acqua potabile e divieto di pesticidi") == [1, 2]
    assert ds.page_ordinals("8 In Kürze Dritte Vorlage: Covid-19-Gesetz Das Coronavirus bleibt unberechenbar.") == [3]


def test_vote_pages_selects_overview_spread_and_detail_section():
    pages = booklet()
    selected, meta = ds.vote_pages(pages, "Bundesgesetz Beta")
    assert meta["ordinal"] == 2
    assert meta["selected_pages"] == [6, 7, 14, 15, 16, 17]
    selected, meta = ds.vote_pages(pages, "Volksinitiative «Alpha»")
    assert meta["selected_pages"] == [4, 5, 10, 11, 12, 13]
    selected, meta = ds.vote_pages(pages, "Gesetz Gamma")
    assert meta["selected_pages"] == [8, 9, 18, 19, 20]


def test_shared_pages_belong_to_both_votes_but_do_not_decide_the_match():
    pages = list(booklet())
    pages[9] = "10 Erste und zweite Vorlage: Alpha und Beta Vergleich der Initiative Alpha mit dem Gesetz Beta."
    selected, meta = ds.vote_pages(pages, "Bundesgesetz Beta")
    assert meta["ordinal"] == 2 and 10 in meta["selected_pages"]
    selected, meta = ds.vote_pages(pages, "Volksinitiative «Alpha»")
    assert meta["ordinal"] == 1 and 10 in meta["selected_pages"]


def test_vote_known_only_from_shared_pages_is_still_found():
    pages = [
        "Cover Premier objet Deuxième objet Troisième objet",
        "4 Premier objet : élevage intensif Initiative populaire « Non à l’élevage intensif »",
        "5 suite",
        "6 Deuxième et troisième objets : AVS 21 Financement additionnel de l’AVS par le biais d’un relèvement de la TVA et Modification de la loi fédérale sur l’assurance-vieillesse et survivants",
        "7 suite AVS",
    ]
    selected, meta = ds.vote_pages(pages, "Modification de la loi fédérale sur l’assurance-vieillesse et survivants (AVS 21)")
    assert meta["ordinal"] == 2 and meta["selected_pages"] == [4, 5]


def test_booklet_without_headers_or_weak_title_match_returns_everything():
    pages = ("Einzelne Vorlage ohne Kopfzeilen", "Seite zwei", "Seite drei")
    selected, meta = ds.vote_pages(pages, "Irgendeine Vorlage")
    assert selected == [0, 1, 2] and meta["fallback"] == "no running headers"
    selected, meta = ds.vote_pages(booklet(), "Völlig anderer Titel über Zölle")
    assert selected == list(range(len(booklet()))) and meta["fallback"] == "weak vote match"


def test_selected_context_renders_only_selected_pages():
    text, meta = ds.selected_context(booklet(), {"vote": "Gesetz Gamma"}, "vote_pages")
    assert text.startswith("[PAGE 8]\n") and "[PAGE 4]" not in text and meta["ordinal"] == 3
