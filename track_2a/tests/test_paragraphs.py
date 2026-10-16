import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parents[1] / 'src'))
import embedding
import predict
from document_selection import paragraphs, paragraph_context, rank_paragraphs
from source_spans import REGION_BREAK, candidates


def sample():
    return ('\n\n'.join(f'Heading {i}\n' + (f'Topic {i} sentence. ' * 20) for i in range(12)),)


def test_paragraph_offsets_and_sizes():
    pages = sample()
    paras = paragraphs(pages, [0])
    assert len(paras) == 12
    for para in paras:
        assert pages[para['page'] - 1][para['start']:para['end']] == para['text']
        assert 200 <= len(para['text']) <= 700


def test_contiguous_groups_preserve_original_separators(monkeypatch):
    import document_selection
    pages = sample()
    monkeypatch.setattr(document_selection, 'rank_paragraphs', lambda *args: [1, 2, 7])
    reduced, meta = paragraph_context(pages, [0], 'Topic', 3, neighbours=0)
    paras = paragraphs(pages, [0])
    assert reduced[0] == pages[0][paras[1]['start']:paras[2]['end']] + REGION_BREAK + paras[7]['text']
    assert meta['kept_paragraphs'] == 3
    for span in candidates(reduced):
        assert span['text'] in pages[0]
        assert reduced[0][span['start']:span['end']] == span['text']
        assert REGION_BREAK not in span['text']


def test_rank_with_and_without_embeddings():
    paras = [{'text': 'aaaa'}, {'text': 'zzzz'}]
    calls = []
    def embed(texts):
        calls.append(texts)
        return [[text.count('a'), text.count('z')] for text in texts]
    assert rank_paragraphs('aaaa', paras, embedder=None) == [0, 1]
    assert rank_paragraphs('aaaa', paras, translation='aaaa', embedder=embed) == [0, 1]
    assert calls == [['aaaa', 'zzzz'], ['aaaa'], ['aaaa']]


def test_context_original_substrings(monkeypatch):
    pages = sample()
    monkeypatch.setattr(predict, 'pdf_pages', lambda _: pages)
    monkeypatch.setattr(predict, 'CLAIM_SPANS', 2)
    monkeypatch.setattr(embedding, 'load_embedder', lambda: None)
    case = {'id': 'p', 'vote': 'Topic', 'booklet': {'path': 'fake.pdf', 'language': 'de'},
            'claim': {'text': 'Topic 7', 'language': 'fr'}}
    calls = []
    reduced, messages = predict.context(case, Path('.'), 'claim_paragraphs',
                                       lambda text, lang: calls.append((text, lang)) or 'Topic 7')
    assert calls == [('Topic 7', 'de')]
    spans = json.loads(messages[1]['content'])['source_spans']
    assert spans
    assert all(span['text'] in pages[span['page'] - 1] for span in spans)


def test_embedder_disabled_and_missing(monkeypatch):
    embedding.load_embedder.cache_clear()
    monkeypatch.setenv('OST_EMBEDDER', 'none')
    assert embedding.load_embedder() is None
    embedding.load_embedder.cache_clear()
    monkeypatch.delenv('OST_EMBEDDER')
    monkeypatch.setenv('OST_EMBED_MODEL_DIR', '/nonexistent/ost-test-model')
    assert embedding.load_embedder() is None
    embedding.load_embedder.cache_clear()
