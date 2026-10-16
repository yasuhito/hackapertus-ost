"""Source-only citation candidates and exact restoration, without model text."""
import hashlib
import json
import re
import unicodedata

MAX_SPAN = 1200


def speaker_heading(source):
    """Recognize standalone attribution headings, never arbitrary body mentions."""
    for line in source.splitlines():
        line = ' '.join(unicodedata.normalize('NFKC', line).casefold().split())
        if re.fullmatch(r'(?:gli |die |les )?(?:comitato(?: referendario| d[’\']iniziativa)?|(?:referendums|initiativ)?komitee|comité(?: référendaire| d[’\']initiative)?)', line):
            return 'committee'
        if re.fullmatch(r'(?:bundesrat und parlament|conseil fédéral et parlement|consiglio federale e parlamento)', line):
            return 'government'
    return None


def citation_pages(page_number, pages):
    """Include a full page and its explicit two-page speaker block if provided."""
    root = page_number
    for n in range(page_number, max(0, page_number - 2), -1):
        if not pages[n - 1].strip():
            break
        if speaker_heading(pages[n - 1]):
            root = n
            break
    selected = {page_number}
    role = speaker_heading(pages[root - 1])
    if role:
        selected.add(root)
        nxt = root + 1
        if nxt <= len(pages) and pages[nxt - 1].strip() and not speaker_heading(pages[nxt - 1]):
            selected.add(nxt)
    return sorted(selected)


def candidates(pages, reference=False):
    """Cover every non-whitespace character, retaining physical page offsets."""
    result = []
    for page_number, source in enumerate(pages, 1):
        if not isinstance(source, str):
            raise ValueError("invalid source page")
        start = 0
        digest = hashlib.sha256(source.encode()).hexdigest()[:12]
        while start < len(source):
            end = min(start + MAX_SPAN, len(source))
            if end < len(source):
                # Prefer paragraph/sentence boundaries, then a complete line/word.
                window = source[start:end]
                boundaries = [m.end() for m in re.finditer(r"\n\s*\n|[.!?][\s]+", window)]
                if not boundaries:
                    boundaries = [m.end() for m in re.finditer(r"\s+", window)]
                late = [b for b in boundaries if b >= MAX_SPAN // 2]
                if late:
                    end = start + late[-1]
            text = source[start:end]
            if text.strip():
                result.append({"span_id": f"p{page_number:04d}-o{start:07d}-e{end:07d}-{digest}",
                               "page": None if reference else page_number,
                               "start": start, "end": end, "text": text})
            start = end
    return result


def restore(raw, pages, reference=False):
    """Reject invalid IDs or missing support; never synthesize citation text."""
    obj = json.loads(raw)
    if not isinstance(obj, dict) or set(obj) != {"label", "evidence"}:
        raise ValueError("invalid ID response object")
    label = obj["label"]
    if type(label) is not int or label not in (0, 1, 2):
        raise ValueError("invalid label")
    evidence = obj["evidence"]
    if not isinstance(evidence, list) or len(evidence) > 5:
        raise ValueError("invalid evidence list")
    # The official rules do not score Task B evidence, but a non-neutral answer
    # that cannot point at any span is not grounded; keep the repair for both tasks.
    if label != 1 and not evidence:
        raise ValueError("supporting span required")
    index = {c["span_id"]: c for c in candidates(pages, reference)}
    restored = []
    selected_pages = set()
    seen = set()
    for item in evidence:
        if not isinstance(item, dict) or set(item) != {"span_id"} or not isinstance(item["span_id"], str):
            raise ValueError("invalid evidence ID object")
        span_id = item["span_id"]
        if span_id not in index or span_id in seen:
            raise ValueError("unknown, wrong-page, stale or duplicate span ID")
        seen.add(span_id)
        c = index[span_id]
        page_number = int(span_id[1:5])
        source = pages[page_number - 1]
        if source[c["start"]:c["end"]] != c["text"] or not c["text"].strip():
            raise ValueError("source span mismatch")
        if not reference and len(c["text"]) > 5000:
            raise ValueError("document evidence exceeds 5000 characters")
        selected_pages.update(citation_pages(page_number, pages) if not reference else [1])
    # IDs remain source-offset anchors. Context closure supplies original source
    # attribution/conditions, without changing words or consulting claim/gold.
    for page_number in sorted(selected_pages):
        text = pages[page_number - 1]
        if not text.strip() or (not reference and len(text) > 5000):
            raise ValueError("citation context unavailable or exceeds 5000 characters")
        restored.append({"page": None if reference else page_number, "text": text})
    if len(restored) > 5:
        raise ValueError("citation context exceeds five evidence items")
    return label, restored
