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
    order = rank_spans(claim, spans)
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


def reciprocal_rank_fusion(*orders, k=60):
    scores = {}
    for order in orders:
        for rank, i in enumerate(order):
            scores[i] = scores.get(i, 0.0) + 1.0 / (k + rank + 1)
    return sorted(scores, key=lambda i: (-scores[i], i))


def rank_spans(claim, spans, translation=None):
    """Span indices by relevance to the claim.

    With a translation of the claim into the booklet language, word-level and
    character-level BM25 on the translation are fused; this keeps the gold page
    for 99% of public claims when whole pages with neighbours are kept. Without
    one, character 4-grams of the original claim are used (about 95%).
    """
    grams = [char_grams(s['text']) for s in spans]

    def order(scores):
        return sorted(range(len(spans)), key=lambda i: (-scores[i], i))
    if translation:
        words_ = [tokens(s['text']) for s in spans]
        return reciprocal_rank_fusion(order(bm25_scores(char_grams(translation), grams)),
                                      order(bm25_scores(tokens(translation), words_)))
    return order(bm25_scores(char_grams(claim), grams))


def claim_pages(pages, selected, claim, spans, top_k, translation=None):
    """Keep whole pages: the opening spread, the pages holding the top-k spans, and their neighbours.

    Whole pages preserve the surrounding conditions that a 1200-char span can
    cut off. `translation` is the claim in the booklet language, if available.
    """
    provided = {i + 1 for i in selected}
    overview = {i + 1 for i in selected[:2]}
    order = rank_spans(claim, spans, translation)
    keep = set(overview)
    for i in order[:top_k]:
        page = spans[i]['page']
        keep.update(n for n in (page - 1, page, page + 1) if n in provided)
    return tuple(text if number in keep else '' for number, text in enumerate(pages, 1)), {'kept_pages': sorted(keep), 'translated': bool(translation)}


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


def paragraphs(pages, selected):
    """Page-local, offset-anchored paragraphs, targeting 200..700 characters.

    Unsplittable sentences may exceed the target; no word-level cuts are made.
    Short headings attach forward, including across a blank line.
    """
    result = []
    for page in sorted(set(selected)):
        source = pages[page]
        blocks = []
        start = 0
        for match in re.finditer(r'\n[ \t]*\n(?:[ \t]*\n)*', source):
            blocks.append((start, match.start()))
            start = match.end()
        blocks.append((start, len(source)))
        units = []
        for start, end in blocks:
            while start < end and source[start].isspace():
                start += 1
            while end > start and source[end - 1].isspace():
                end -= 1
            if start == end:
                continue
            cuts = [start + m.end() for m in re.finditer(r'[.!?](?=\s|$)|\n', source[start:end])]
            while end - start > 700:
                options = [c for c in cuts if start < c <= start + 700]
                cut = max(options) if options else next((c for c in cuts if c > start), end)
                units.append((start, cut))
                start = cut
            if start < end:
                units.append((start, end))
        merged = []
        for start, end in units:
            if merged and (merged[-1][1] - merged[-1][0] < 60 or
                           (merged[-1][1] - merged[-1][0] < 200 and end - merged[-1][0] <= 700)):
                merged[-1] = (merged[-1][0], end)
            else:
                merged.append((start, end))
        for start, end in merged:
            result.append({'page': page + 1, 'start': start, 'end': end, 'text': source[start:end]})
    return result


CLAIM_KINDS = (
    ('summary', r'(?:le resume|il riassunto|nel riassunto|die zusammenfassung|laut der zusammenfassung|gemass der zusammenfassung|secondo il riassunto|d.apres le resume|selon le resume|the summary)'),
    ('committee', r'(?:das (?:initiativ|referendums)?komitee|le comite|il comitato|laut dem komitee|selon le comite|secondo il comitato)'),
    ('council', r'(?:der bundesrat|le conseil federal|il consiglio federale|bundesrat und parlament|laut (?:dem )?bundesrat|selon le conseil federal|secondo il consiglio federale)'),
    ('votetext', r'(?:laut dem abstimmungstext|der abstimmungstext|gemass abstimmungstext|selon le texte soumis|d.apres le texte|le texte (?:soumis au vote|de vote)|secondo il testo|stando al testo|il testo (?:di voto|in votazione))'),
    ('ifadopted', r'(?:wird die abstimmung|bei annahme|bei einer annahme|si le vote|en cas d.acceptation|si l.objet est|se il voto|se la votazione|in caso di accettazione)'),
)
# Which booklet sections the dataset's claim openings quote from (public rows,
# gold passages): summary claims cite the opening spread almost exclusively;
# committee and council claims cite their own argument pages or the detail
# section; vote-text claims cite the law text.
PREFERRED_SECTIONS = {
    'summary': {'overview'},
    'committee': {'committee', 'detail', 'overview', 'arguments'},
    'council': {'council', 'detail', 'overview', 'arguments'},
    'votetext': {'votetext'},
    'ifadopted': {'detail', 'overview', 'votetext'},
}


def claim_kind(claim):
    """Classify a claim by its attributive opening; 'other' when none applies."""
    head = normalize(claim)[:80]
    for kind, pattern in CLAIM_KINDS:
        if re.match(pattern, head):
            return kind
    return 'other'


SECTION_MARKERS = (
    ('votetext', r'(?:abstimmungstext|texte soumis au vote|testo in votazione)\b'),
    ('committee', r'\b(?:argumente|arguments|argomenti)\b[^.]{0,40}?\b(?:komitee|komitees|comite|comitato)\b'),
    ('council', r'\b(?:argumente|arguments|argomenti)\b[^.]{0,40}?\b(?:bundesrat und parlament|conseil federal et parlement|consiglio federale e parlamento)\b'),
    ('detail', r'(?:im detail|en detail|in dettaglio)\b'),
)
SPEAKER_LINES = (
    ('committee', r'(?:das |le |il )?(?:(?:initiativ|referendums)?komitee|comite(?: referendaire| d.initiative)?|comitato(?: referendario| d.iniziativa)?)'),
    ('council', r'(?:bundesrat und parlament|conseil federal et parlement|consiglio federale e parlamento)'),
)
LAW_SIGN = re.compile(r'^\s*\d*\s*§')


def page_sections(pages, selected):
    """Section label per selected page (0-based index -> label).

    The first two selected pages are the vote's opening spread ('overview').
    Later pages take the section of the last marker in their first lines (a
    page's mini table of contents precedes its own heading), a standalone
    speaker line marks argument pages, and pages without any marker inherit
    the previous page's section. Law text is recognised by its paragraph sign.
    """
    labels = {}
    current = 'detail'
    for position, page in enumerate(sorted(set(selected))):
        text = pages[page]
        if position < 2:
            labels[page] = 'overview'
            continue
        head = normalize(text[:400])
        found, best = None, -1
        for label, pattern in SECTION_MARKERS:
            for m in re.finditer(pattern, head):
                if m.start() >= best:
                    best, found = m.start(), label
        for line in text[:400].splitlines():
            normal = normalize(line)
            for label, pattern in SPEAKER_LINES:
                if re.fullmatch(pattern, normal):
                    found = label
        if found is None and LAW_SIGN.match(text):
            found = 'votetext'
        if found:
            current = found
        labels[page] = current
    return labels


def section_order(paras, sections, kind):
    """Paragraph indices whose page section fits the claim kind, in document order."""
    preferred = PREFERRED_SECTIONS.get(kind)
    if not preferred:
        return []
    return [i for i, p in enumerate(paras) if sections.get(p['page'] - 1) in preferred]


def rank_paragraphs(claim, paras, translation=None, embedder=None, sections=None, kind=None, section_mode='fuse'):
    """Fuse lexical, optional local embedding and optional section-prior rankings.

    section_mode 'fuse' adds the section prior as one more fused ranking;
    'first' moves fitting paragraphs ahead of the rest (fused order inside).
    """
    import math

    def order(scores):
        return sorted(range(len(paras)), key=lambda i: (-scores[i], i))

    if not paras:
        return []
    texts = [p['text'] for p in paras]
    grams = [char_grams(text) for text in texts]
    orders = [order(bm25_scores(char_grams(claim), grams))]
    if translation:
        orders.extend([order(bm25_scores(char_grams(translation), grams)),
                       order(bm25_scores(tokens(translation), [tokens(text) for text in texts]))])
    if embedder:
        vectors = embedder(texts)
        for query in ([translation, claim] if translation else [claim]):
            q = embedder([query])[0]
            qnorm = math.sqrt(sum(float(x) ** 2 for x in q))
            scores = []
            for vector in vectors:
                denom = qnorm * math.sqrt(sum(float(x) ** 2 for x in vector))
                scores.append(sum(float(a) * float(b) for a, b in zip(q, vector)) / denom if denom else 0.0)
            orders.append(order(scores))
    fused = reciprocal_rank_fusion(*orders)
    if sections is not None and kind:
        fitting = section_order(paras, sections, kind)
        if fitting:
            if section_mode == 'first':
                fit = set(fitting)
                return [i for i in fused if i in fit] + [i for i in fused if i not in fit]
            # Rank fitting paragraphs by their fused position so the prior is stable.
            rank = {i: r for r, i in enumerate(fused)}
            return reciprocal_rank_fusion(fused, sorted(fitting, key=lambda i: rank[i]))
    return fused


def paragraph_context(pages, selected, claim, top_k, translation=None, embedder=None, neighbours=1, section_prior=True, section_mode='fuse'):
    """Keep ranked paragraphs and page-local neighbours as original regions."""
    from source_spans import REGION_BREAK
    paras = paragraphs(pages, selected)
    sections = page_sections(pages, selected) if section_prior else None
    kind = claim_kind(claim) if section_prior else None
    keep = set()
    for i in rank_paragraphs(claim, paras, translation, embedder, sections, kind, section_mode)[:top_k]:
        keep.update(j for j in range(max(0, i - neighbours), min(len(paras), i + neighbours + 1))
                    if paras[j]['page'] == paras[i]['page'])
    groups = {}
    previous = None
    for i in sorted(keep):
        para = paras[i]
        page = para['page']
        if previous is not None and i == previous + 1 and paras[previous]['page'] == page:
            groups[page][-1][1] = para['end']
        else:
            groups.setdefault(page, []).append([para['start'], para['end']])
        previous = i
    reduced = tuple(REGION_BREAK.join(text[start:end] for start, end in groups.get(n, []))
                    for n, text in enumerate(pages, 1))
    return reduced, {'kept_paragraphs': len(keep), 'kept_pages': sorted(groups),
                     'chars': sum(map(len, reduced))}
