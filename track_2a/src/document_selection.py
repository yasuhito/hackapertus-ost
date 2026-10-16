"""Select the pages of one vote from a multi-vote booklet. Uses request + PDF only; never gold."""
import re
import unicodedata

STOP = {'volksinitiative', 'initiative', 'iniziativa', 'populaire', 'popolare', 'federale', 'fur', 'eine', 'ein',
        'der', 'die', 'das', 'des', 'du', 'de', 'la', 'le', 'les', 'une', 'un', 'per', 'una', 'di', 'della', 'del'}
ORDINALS = {
    'erste': 1, 'zweite': 2, 'dritte': 3, 'vierte': 4, 'funfte': 5, 'sechste': 6, 'siebte': 7, 'achte': 8,
    'premier': 1, 'premiere': 1, 'deuxieme': 2, 'troisieme': 3, 'quatrieme': 4, 'cinquieme': 5, 'sixieme': 6,
    'septieme': 7, 'huitieme': 8,
    'primo': 1, 'secondo': 2, 'terzo': 3, 'quarto': 4, 'quinto': 5, 'sesto': 6, 'settimo': 7, 'ottavo': 8,
}
ORDINAL_WORDS = '|'.join(ORDINALS)
ORDINAL_RE = re.compile(r'\b(' + ORDINAL_WORDS + r')(?:\s+(?:und|et|e)\s+(' + ORDINAL_WORDS + r'))?\s+(?:vorlagen?|objets?|oggett[oi])\b')
MIN_TITLE_MATCH = 0.45


def normalize(text):
    text = re.sub(r'(\w)\s*[-\u00ad]\s*\n\s*(?=\w)', r'\1', text)
    folded = unicodedata.normalize('NFKD', text.casefold())
    return ' '.join(''.join(c for c in folded if not unicodedata.combining(c)).split())


def tokens(text):
    return [w for w in re.findall(r'\w+', normalize(text)) if len(w) > 2 and w not in STOP]


def page_ordinals(page):
    """Vote ordinals printed in the running header at the top of a booklet page.

    Content pages name exactly one vote (or one shared pair, 'Zweite und dritte
    Vorlage'). Cover and contents pages mention every vote and yield nothing.
    """
    if len(ORDINAL_RE.findall(normalize(page))) != 1:
        return []
    m = ORDINAL_RE.search(normalize(page[:400]))
    if not m:
        return []
    found = {ORDINALS[m.group(1)]}
    if m.group(2):
        found.add(ORDINALS[m.group(2)])
    return sorted(found)


def vote_pages(pages, vote):
    """Indices of the pages that belong to the given vote, with selection metadata.

    Federal booklets print 'Erste Vorlage: ...' style running headers on the
    first page of each spread; a page without a header belongs to the preceding
    headed page. The vote is identified by matching its title against the text
    of each ordinal's own pages, which open with the full title. Booklets
    without such headers (single-vote layouts) are returned whole.
    """
    labels = [page_ordinals(p) for p in pages]
    if not any(labels):
        return list(range(len(pages))), {'fallback': 'no running headers'}
    first = min(i for i, l in enumerate(labels) if l)
    owner, current = [], []
    for i, l in enumerate(labels):
        if l:
            current = l
        owner.append(list(current) if i >= first else [])
    query = set(tokens(vote))

    def match(text):
        return len(query & set(tokens(text))) / max(1, len(query))
    # Shared pages print both titles, so they identify a vote only when it has
    # no page of its own.
    exclusive, shared = {}, {}
    for i, l in enumerate(labels):
        for o in l:
            target = exclusive if len(l) == 1 else shared
            target[o] = max(target.get(o, 0), match(pages[i][:900]))
    scores = {o: exclusive.get(o, shared.get(o, 0)) for o in set(exclusive) | set(shared)}
    ordinal, confidence = max(scores.items(), key=lambda kv: (kv[1], -kv[0]))
    if confidence < MIN_TITLE_MATCH:
        return list(range(len(pages))), {'fallback': 'weak vote match', 'confidence': confidence}
    selected = [i for i, o in enumerate(owner) if ordinal in o]
    return selected, {'ordinal': ordinal, 'confidence': confidence, 'selected_pages': [i + 1 for i in selected]}


def char_grams(text, n=4):
    """Character 4-grams of content words plus bare numbers.

    Claims and booklets are often in different languages; shared stems such as
    pestizid / pesticid / pesticide still overlap at the character level, which
    plain word matching misses.
    """
    out = []
    for w in re.findall(r'\w+', normalize(text)):
        if w.isdigit():
            out.append(w)
        elif len(w) > 3 and w not in STOP:
            padded = f' {w} '
            out.extend(padded[i:i + n] for i in range(len(padded) - n + 1))
    return out


def bm25_scores(query_tokens, docs_tokens):
    import math
    count = len(docs_tokens) or 1
    frequency = {}
    for d in docs_tokens:
        for w in set(d):
            frequency[w] = frequency.get(w, 0) + 1
    average = sum(len(d) for d in docs_tokens) / count
    query = set(query_tokens)
    scores = []
    for d in docs_tokens:
        counts = {}
        for w in d:
            counts[w] = counts.get(w, 0) + 1
        length = len(d) / average if average else 1
        scores.append(sum(math.log(1 + (count - frequency[w] + 0.5) / (frequency[w] + 0.5)) * (counts[w] * 2.2) / (counts[w] + 1.2 * (0.25 + 0.75 * length))
                          for w in query if w in counts))
    return scores


def claim_span_pages(pages, selected, claim, spans, top_k):
    """Reduce the vote's pages to its opening spread plus the spans most related to the claim.

    `selected` are 0-based indices of the vote's pages, `spans` the candidate
    spans over those pages (each with 'page' and 'text'). Returns a page tuple
    of the booklet's length: the first two selected pages intact, other pages
    reduced to their kept spans in document order (joined by blank lines),
    unselected pages empty. Verbatim text only; nothing is rewritten.
    """
    overview = {i + 1 for i in selected[:2]}
    scores = bm25_scores(char_grams(claim), [char_grams(s['text']) for s in spans])
    order = sorted(range(len(spans)), key=lambda i: (-scores[i], i))
    keep = {}
    for i in order[:top_k]:
        keep.setdefault(spans[i]['page'], []).append(i)
    result = []
    for number, text in enumerate(pages, 1):
        if number in overview:
            result.append(text)
        elif number in keep:
            result.append('\n\n'.join(spans[i]['text'] for i in sorted(keep[number])))
        else:
            result.append('')
    return tuple(result), {'kept_spans': top_k, 'kept_pages': sorted(overview | set(keep))}


def claim_pages(pages, selected, claim, spans, top_k):
    """Keep whole pages: the opening spread, the pages holding the top-k spans, and their neighbours.

    Whole pages preserve the surrounding conditions that a 1200-char span can
    cut off. On the public rows this keeps the gold page for 97% of claims at
    about two thirds of the vote's text.
    """
    provided = {i + 1 for i in selected}
    overview = {i + 1 for i in selected[:2]}
    scores = bm25_scores(char_grams(claim), [char_grams(s['text']) for s in spans])
    order = sorted(range(len(spans)), key=lambda i: (-scores[i], i))
    keep = set(overview)
    for i in order[:top_k]:
        page = spans[i]['page']
        keep.update(n for n in (page - 1, page, page + 1) if n in provided)
    return tuple(text if number in keep else '' for number, text in enumerate(pages, 1)), {'kept_pages': sorted(keep)}


def rank_pages(claim, pages, page_numbers):
    """Order the given 1-based page numbers by lexical relevance to the claim (BM25).

    Ties keep booklet order. Cross-lingual pairs still share names, numbers and
    many stems, so this is a deterministic tie-breaker, not a semantic judgment.
    """
    import math
    docs = {n: tokens(pages[n - 1]) for n in page_numbers}
    query = set(tokens(claim))
    count = len(docs) or 1
    average = sum(len(d) for d in docs.values()) / count
    frequency = {}
    for d in docs.values():
        for w in set(d):
            frequency[w] = frequency.get(w, 0) + 1

    def score(n):
        d = docs[n]
        length = len(d) / average if average else 1
        counts = {}
        for w in d:
            counts[w] = counts.get(w, 0) + 1
        return sum(math.log(1 + (count - frequency[w] + 0.5) / (frequency[w] + 0.5)) * (counts[w] * 2.2) / (counts[w] + 1.2 * (0.25 + 0.75 * length))
                   for w in query if w in counts)
    return sorted(page_numbers, key=lambda n: (-score(n), n))


def selected_context(pages, case, variant):
    if variant != 'vote_pages':
        raise ValueError('invalid context variant')
    selected, meta = vote_pages(pages, case['vote'])
    return '\n\n'.join(f'[PAGE {i + 1}]\n{pages[i]}' for i in selected), meta
