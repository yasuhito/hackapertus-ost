"""Gold-page coverage of claim-driven page/span retrieval inside the selected vote pages.

No model calls. For every public row with a reference passage (excluding the
sealed indices), find the booklet pages that fuzzy-contain the passage, select
the vote's pages with the running-header selector, then rank those pages and
their 1200-char spans by lexical relevance to the claim. Reports how often a
gold page is inside the top-k and the resulting context size, overall and per
language pair, so a retrieval budget can be chosen without touching models.
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
from source_spans import candidates  # noqa: E402


def normalize(text):
    text = unicodedata.normalize("NFKC", text).replace("\u00ad", "")
    text = re.sub(r"(\w) ?-\s*\n\s*(\w)", r"\1\2", text)
    return re.sub(r"\s+", " ", text).strip().lower()


def words(text):
    return set(re.findall(r"\w{4,}", text))


def pdf_pages(path):
    from pypdf import PdfReader
    return [page.extract_text() or "" for page in PdfReader(path).pages]


def gold_pages(norm_pages, page_words, reference):
    ref = normalize(reference)
    rw = words(ref)
    out = []
    for i, (page, pw) in enumerate(zip(norm_pages, page_words)):
        if not page or (rw and len(rw & pw) / len(rw) < 0.5):
            continue
        if fuzz.partial_ratio(page, ref, score_cutoff=90) >= 90:
            out.append(i + 1)
    return out


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=Path("track_2a/data/source.jsonl"))
    parser.add_argument("--booklet-dirs", nargs="+", type=Path, required=True)
    parser.add_argument("--exclude-indices", type=Path)
    parser.add_argument("--ks", nargs="+", type=int, default=[1, 2, 3, 4, 6])
    args = parser.parse_args()
    excluded = set(json.loads(args.exclude_indices.read_text())) if args.exclude_indices else set()
    rows = [json.loads(line) for line in args.source.open(encoding="utf-8")]
    local = {}
    for directory in args.booklet_dirs:
        for pdf in directory.glob("*.pdf"):
            local.setdefault(pdf.name, pdf)
    cache, gold_cache = {}, {}
    hits = collections.Counter()
    pair_hits = collections.defaultdict(collections.Counter)
    chars = collections.defaultdict(list)
    total = 0
    for index, row in enumerate(rows):
        if index in excluded or not row.get("reference_string"):
            continue
        name = hashlib.sha256(row["booklet_url"].encode()).hexdigest()[:16] + ".pdf"
        if name not in local:
            continue
        if name not in cache:
            raw = pdf_pages(str(local[name]))
            norm = [normalize(p) for p in raw]
            cache[name] = (raw, norm, [words(p) for p in norm])
        raw, norm, pw = cache[name]
        key = (name, row["reference_string"])
        if key not in gold_cache:
            gold_cache[key] = gold_pages(norm, pw, row["reference_string"])
        gold = gold_cache[key]
        if not gold:
            continue
        selected, meta = ds.vote_pages(raw, row["vote"])
        provided = [i + 1 for i in selected]
        if not all(g in provided for g in gold):
            hits["gold_outside_vote_pages"] += 1
            continue
        total += 1
        pair = f"{row['reference_language']}->{row['claim_language']}"
        overview = provided[:2]
        ranked = ds.rank_pages(row["claim"], raw, provided)
        ranked_rest = ds.rank_pages(row["claim"], raw, [p for p in provided if p not in overview])
        # Span level: rank 1200-char spans of the vote pages by the same lexical score.
        masked = [raw[i] if (i + 1) in provided else "" for i in range(len(raw))]
        spans = candidates(masked)
        span_texts = [s["text"] for s in spans]
        order = sorted(range(len(spans)), key=lambda i: -span_score(row["claim"], span_texts, i))
        for k in args.ks:
            variants = {
                f"pages_top{k}": ranked[:k],
                f"overview+top{k}": overview + ranked_rest[:k],
                f"spans_top{k}_pages": sorted({spans[i]["page"] for i in order[:k]}),
                f"overview+spans_top{k}": overview + sorted({spans[i]["page"] for i in order[:k]}),
            }
            for label, pages in variants.items():
                hit = any(g in pages for g in gold)
                hits[label] += hit
                pair_hits[pair][label] += hit
                size = sum(len(raw[p - 1]) for p in set(pages)) if "spans" not in label else (
                    sum(len(raw[p - 1]) for p in overview) if label.startswith("overview") else 0) + sum(len(span_texts[i]) for i in order[:k])
                chars[label].append(size)
        chars["all_vote_pages"].append(sum(len(raw[p - 1]) for p in provided))
        hits["all_vote_pages"] += 1
        pair_hits[pair]["all_vote_pages"] += 1
    print(json.dumps({"rows_with_gold_inside_vote_pages": total, "gold_outside_vote_pages": hits["gold_outside_vote_pages"]}))
    print(f"{'variant':24s} {'coverage':>9s} {'chars mean':>11s} {'chars max':>10s}")
    for label in sorted(hits):
        if label == "gold_outside_vote_pages":
            continue
        c = chars[label]
        print(f"{label:24s} {hits[label]/total:9.3f} {sum(c)/len(c):11.0f} {max(c):10d}")
    print("\nper language pair (reference->claim): rows, overview+top3, overview+spans_top6")
    for pair in sorted(pair_hits):
        n = pair_hits[pair]["all_vote_pages"]
        print(f"  {pair}: n={n} overview+top3={pair_hits[pair]['overview+top3']/n:.2f} overview+spans_top6={pair_hits[pair]['overview+spans_top6']/n:.2f}")


def span_score(claim, texts, i):
    return rank_cache(claim, texts)[i]


_cache = {}


def rank_cache(claim, texts):
    key = (claim, len(texts), texts[0] if texts else "")
    if key not in _cache:
        import math
        docs = [ds.tokens(t) for t in texts]
        query = set(ds.tokens(claim))
        count = len(docs) or 1
        average = sum(len(d) for d in docs) / count
        frequency = collections.Counter(w for d in docs for w in set(d))
        scores = []
        for d in docs:
            counts = collections.Counter(d)
            length = len(d) / average if average else 1
            scores.append(sum(math.log(1 + (count - frequency[w] + 0.5) / (frequency[w] + 0.5)) * (counts[w] * 2.2) / (counts[w] + 1.2 * (0.25 + 0.75 * length)) for w in query if w in counts))
        _cache[key] = scores
    return _cache[key]


if __name__ == "__main__":
    main()
