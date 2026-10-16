"""Deterministic audit of booklet page selection against dataset reference passages.

No model calls. Uses the public dataset rows (reference_string, vote, booklet) and
locally available PDFs. Reports, per selector, how often every page carrying the
reference passage is inside the selected pages, plus context size. Rows listed in
--exclude-indices (sealed confirmation rows) are skipped.
"""
import argparse
import collections
import hashlib
import json
import re
import sys
import unicodedata
from pathlib import Path

from rapidfuzz import fuzz

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import document_selection as ds  # noqa: E402
sys.path.insert(0, str(Path(__file__).resolve().parent))
import legacy_page_section  # noqa: E402


def normalize(text):
    text = unicodedata.normalize("NFKC", text).replace("\u00ad", "")
    text = re.sub(r"(\w) ?-\s*\n\s*(\w)", r"\1\2", text)
    return re.sub(r"\s+", " ", text).strip().lower()


def pdf_pages(path):
    from pypdf import PdfReader
    return [page.extract_text() or "" for page in PdfReader(path).pages]


def words(text):
    return set(re.findall(r"\w{4,}", text))


def gold_pages(norm_pages, page_words, reference, min_ratio=90):
    """Pages whose text fuzzy-contains the reference, as the official evaluator matches.

    A cheap word-overlap prefilter skips pages that cannot reach the ratio."""
    ref = normalize(reference)
    ref_words = words(ref)
    result = []
    for i, (page, pw) in enumerate(zip(norm_pages, page_words)):
        if not page or (ref_words and len(ref_words & pw) / len(ref_words) < 0.5):
            continue
        if fuzz.partial_ratio(page, ref, score_cutoff=min_ratio) >= min_ratio:
            result.append(i + 1)
    return result


SELECTORS = {
    "legacy": lambda pages, vote: legacy_page_section.page_section(pages, vote),
    "headers": lambda pages, vote: ds.vote_pages(pages, vote),
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=Path("track_2a/data/source.jsonl"))
    parser.add_argument("--booklet-dirs", nargs="+", type=Path, required=True)
    parser.add_argument("--exclude-indices", type=Path, help="JSON list of source indices to skip")
    parser.add_argument("--selectors", nargs="+", default=list(SELECTORS))
    parser.add_argument("--details", action="store_true")
    parser.add_argument("--limit", type=int)
    args = parser.parse_args()
    excluded = set(json.loads(args.exclude_indices.read_text())) if args.exclude_indices else set()
    rows = [json.loads(line) for line in args.source.open(encoding="utf-8")]
    local = {}
    for directory in args.booklet_dirs:
        for pdf in directory.glob("*.pdf"):
            local.setdefault(pdf.name, pdf)
    cache = {}
    stats = {name: collections.Counter() for name in args.selectors}
    chars = {name: [] for name in args.selectors}
    details = []
    gold_cache = {}
    for index, row in enumerate(rows):
        if index in excluded or not row.get("reference_string"):
            continue
        if args.limit and index >= args.limit:
            break
        name = hashlib.sha256(row["booklet_url"].encode()).hexdigest()[:16] + ".pdf"
        if name not in local:
            stats_key = "booklet_unavailable"
            for s in stats.values():
                s[stats_key] += 1
            continue
        if name not in cache:
            raw = pdf_pages(str(local[name]))
            norm = [normalize(p) for p in raw]
            cache[name] = (raw, norm, [words(p) for p in norm])
        pages, norm_pages, page_words = cache[name]
        gold_key = (name, row["reference_string"])
        if gold_key not in gold_cache:
            gold_cache[gold_key] = gold_pages(norm_pages, page_words, row["reference_string"])
        gold = gold_cache[gold_key]
        if not gold:
            for s in stats.values():
                s["gold_unmatched"] += 1
            continue
        for selector in args.selectors:
            selected, meta = SELECTORS[selector](pages, row["vote"])
            chosen = {i + 1 for i in selected}
            covered = all(p in chosen for p in gold)
            stats[selector]["covered" if covered else "missed"] += 1
            if meta.get("fallback"):
                stats[selector]["fallback_" + str(meta["fallback"])] += 1
            chars[selector].append(sum(len(pages[i]) for i in selected))
            if args.details and not covered:
                details.append({"index": index, "selector": selector, "booklet": name, "vote": row["vote"][:60],
                                "gold_pages": gold, "selected": sorted(chosen), "meta": {k: v for k, v in meta.items() if k != "selected_pages"}})
    report = {}
    for selector in args.selectors:
        c = sorted(chars[selector])
        report[selector] = {**stats[selector], "rows": len(c),
                            "chars_median": c[len(c) // 2] if c else None, "chars_max": max(c) if c else None,
                            "chars_mean": round(sum(c) / len(c)) if c else None}
    print(json.dumps({"booklets_available": len(local), "report": report}, ensure_ascii=False, indent=2))
    for d in details:
        print(json.dumps(d, ensure_ascii=False))


if __name__ == "__main__":
    main()
