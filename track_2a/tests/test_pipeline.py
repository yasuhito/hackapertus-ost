import json
from pathlib import Path
import sys
import subprocess
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from predict import Backend, context, decode, predict
from source_spans import candidates
from score import score


def case(text='Der Bundesrat lehnt die Initiative ab.'):
    return {'id': 'a', 'reference': {'text': text}, 'claim': {'text': text}}


def test_mock_verbatim():
    p = predict(case(), Backend('mock'))
    assert p['label'] == 0 and p['label_name'] == 'entailment'
    assert p['evidence'] == [{'page': None, 'text': case()['reference']['text']}]
    assert p['metrics']['input_tokens'] > 0


@pytest.mark.parametrize('bad', [None, [], {}, {'id': 'x', 'claim': {'text': ''}}])
def test_malformed_valid_output(bad):
    p = predict(bad, Backend('mock'), fallback_id='bad')
    assert p['label'] == 1 and 'error' in p
    json.dumps(p, allow_nan=False)


@pytest.mark.parametrize('raw', ['{"label":true}', '{"label":3}', '{"label":2,"evidence":[]}',
    '{"label":0,"evidence":[{"page":2,"text":"A"}]}',
    '{"label":0,"evidence":[{"page":1,"text":"translated"}]}'])
def test_reject_bad_evidence(raw):
    with pytest.raises((ValueError, KeyError)):
        decode(raw, ['A'])


def test_contradiction_and_reject_fence():
    raw=json.dumps({'label':2,'evidence':[{'span_id':candidates(['NON'])[0]['span_id']}]})
    assert decode(raw,['NON'])[0]==2
    with pytest.raises(ValueError):decode('```json\n'+raw+'\n```',['NON'])


def test_pdf_full_document(tmp_path):
    # Tiny valid two-page PDF with real extracted text; no external fixture.
    objects = [b'<< /Type /Catalog /Pages 2 0 R >>', b'<< /Type /Pages /Kids [3 0 R 4 0 R] /Count 2 >>',
        b'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 300 300] /Resources << /Font << /F1 5 0 R >> >> /Contents 6 0 R >>',
        b'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 300 300] /Resources << /Font << /F1 5 0 R >> >> /Contents 7 0 R >>',
        b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>']
    for text in ('FIRST', 'SECOND'):
        stream = f'BT /F1 12 Tf 20 200 Td ({text}) Tj ET'.encode()
        objects.append(b'<< /Length ' + str(len(stream)).encode() + b' >>\nstream\n' + stream + b'\nendstream')
    data = b'%PDF-1.4\n'; offsets = [0]
    for n, obj in enumerate(objects, 1):
        offsets.append(len(data)); data += f'{n} 0 obj\n'.encode() + obj + b'\nendobj\n'
    start = len(data)
    data += f'xref\n0 {len(objects)+1}\n0000000000 65535 f \n'.encode()
    data += b''.join(f'{v:010} 00000 n \n'.encode() for v in offsets[1:])
    data += f'trailer\n<< /Size 8 /Root 1 0 R >>\nstartxref\n{start}\n%%EOF'.encode()
    (tmp_path / 'a.pdf').write_bytes(data)
    c = {'id': 'pdf', 'booklet': {'path': 'a.pdf'}, 'vote': 'test', 'claim': {'text': 'SECOND'}}
    pages, messages = context(c, tmp_path)
    assert len(pages) == 2 and {x['page'] for x in json.loads(messages[1]['content'])['source_spans']} == {1,2}
    result = predict(c, Backend('mock'), tmp_path)
    assert result['evidence'][0]['page'] == 2
    # Actual mixed A/B CLI run; inputs stay read-only and unchanged.
    source = tmp_path / 'mixed.jsonl'
    source.write_text(json.dumps(c) + '\n' + json.dumps(case('Ja')) + '\n')
    before = source.read_bytes()
    source.chmod(0o444)
    (tmp_path / 'a.pdf').chmod(0o444)
    target = tmp_path / 'out' / 'predictions.jsonl'
    subprocess.run([sys.executable, str(Path(__file__).resolve().parents[1] / 'src/predict.py'),
                    '--backend', 'mock', '--input', str(source), '--output', str(target)], check=True)
    rows = [json.loads(line) for line in target.read_text().splitlines()]
    assert source.read_bytes() == before
    assert [r['id'] for r in rows] == ['pdf', 'a']
    assert [r['evidence'][0]['page'] for r in rows] == [2, None]
    assert all('error' not in r for r in rows)


def test_scorer_order_errors_pages():
    gold = []
    preds = []
    for i in range(3):
        gold.append({'id': str(i), 'label': i, 'task': 'advanced', 'claim_language': 'de',
                     'reference_language': 'fr', 'evidence': [{'page': 2, 'text': 'ABC'}] if i != 1 else []})
        preds.append({'id': str(i), 'label': i, 'label_name': ['entailment', 'neutral', 'contradiction'][i],
                      'evidence': [{'page': 2, 'text': 'ABC'}] if i != 1 else [],
                      'metrics': {'input_tokens': 3, 'output_tokens': 2, 'inference_time_ms': i+1}})
    report = score(gold, list(reversed(preds)))
    assert report['macro_f1']['overall']['value'] == 1
    assert report['evidence']['exact_match_rate'] == 1
    assert report['tokens']['input_tokens'] == 9
    preds[0]['evidence'][0]['page'] = 1
    assert score(gold, preds)['evidence']['exact_match_rate'] == .5
    preds[1]['error'] = 'broken'
    assert score(gold, preds)['macro_f1']['overall']['value'] == pytest.approx(2/3)
    assert score(gold, preds + [preds[0]])['invalid_or_missing'] == 2
    assert score(gold, [])['macro_f1']['overall']['value'] == 0
    assert score(gold, [None, {'id': {}}, {'id': '0'}])['invalid_or_missing'] == 3
    assert score(gold, [None, {'id': {}}])['unidentifiable_prediction_rows'] == 2


def test_cli_bad_line_keeps_rows(tmp_path):
    source = tmp_path / 'cases.jsonl'; target = tmp_path / 'predictions.jsonl'
    source.write_text(json.dumps(case()) + '\n{bad\n' + json.dumps(case('Non.')) + '\n')
    subprocess.run([sys.executable, str(Path(__file__).resolve().parents[1] / 'src/predict.py'),
                    '--backend', 'mock', '--input', str(source), '--output', str(target)], check=True)
    rows = [json.loads(line) for line in target.read_text().splitlines()]
    assert len(rows) == 3 and rows[1]['id'] == 'invalid-line-2' and 'error' in rows[1]


@pytest.mark.parametrize("official", [False, True])
@pytest.mark.parametrize("b_page", [None, 1])
def test_openai_wire_local_only(monkeypatch, official, b_page):
    monkeypatch.delenv('BASE_URL', raising=False)
    monkeypatch.delenv('API_KEY', raising=False)
    captured = {}
    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            captured.update(path=self.path, header=self.headers['User-Agent'], auth=self.headers.get('Authorization'),
                            body=json.loads(self.rfile.read(int(self.headers['Content-Length']))))
            self.send_response(200); self.end_headers()
            self.wfile.write(json.dumps({'choices': [{'message': {'content': json.dumps({'label': 0, 'evidence': [{'span_id':json.loads(captured['body']['messages'][1]['content'])['source_spans'][0]['span_id']}]})}}],
                                        'usage': {'prompt_tokens': 11, 'completion_tokens': 7}}).encode())
        def log_message(self, *args): pass
    server = HTTPServer(('127.0.0.1', 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
    monkeypatch.setenv('LLM_BASE_URL', f'http://127.0.0.1:{server.server_port}/v1')
    if official:
        monkeypatch.setenv('BASE_URL', f'http://127.0.0.1:{server.server_port}/v1')
        monkeypatch.setenv('LLM_BASE_URL', 'http://127.0.0.1:1/forbidden')
        monkeypatch.setenv('API_KEY', 'official-test-key')
        monkeypatch.setenv('LLM_API_KEY', 'legacy-test-key')
    monkeypatch.setenv('LLM_MODEL', 'swiss-ai/apertus-v1.5-70b')
    monkeypatch.setenv('LLM_USER_AGENT', 'test-agent')
    try:
        p = predict(case('Ja'), Backend('openai'))
        assert p['label'] == 0 and p['metrics']['input_tokens'] == 11
        assert p['evidence'] == [{'page': None, 'text': 'Ja'}]
        assert captured['path'] == '/v1/chat/completions' and captured['header'] == 'test-agent'
        assert captured['body']['model'].endswith('70b')
        if official:
            assert captured['auth'] == 'Bearer official-test-key'
    finally:
        server.shutdown(); server.server_close(); thread.join()


def test_no_split_leakage():
    data = Path(__file__).resolve().parents[1] / 'data'
    train = [json.loads(l) for l in (data / 'train_cases.jsonl').read_text().splitlines()]
    dev = [json.loads(l) for l in (data / 'dev_cases.jsonl').read_text().splitlines()]
    assert not {r['date'] for r in train} & {r['date'] for r in dev}
    assert len(train) + len(dev) == 1488


@pytest.mark.parametrize('label', [0, 2])
def test_reference_evidence_required_by_id_pipeline(label):
    with pytest.raises(ValueError):decode(json.dumps({'label':label,'evidence':[]}),['Ja'],reference=True)
    raw=json.dumps({'label':label,'evidence':[{'span_id':candidates(['Ja'],True)[0]['span_id']}]})
    assert decode(raw,['Ja'],reference=True)[1][0]['page'] is None


@pytest.mark.parametrize('length', [5000, 5001])
def test_document_quote_boundary(length):
    text = 'A' * length
    raw = json.dumps({'label': 0, 'evidence': [{'span_id': candidates([text])[0]['span_id']}]})
    if length == 5000:
        assert decode(raw, [text])[1][0]['text'] == text
    else:
        with pytest.raises(ValueError, match='5000'):
            decode(raw, [text])


def test_evidence_above_five_rejected():
    pages=list(map(str,range(1,7)));evidence=[{'span_id':x['span_id']} for x in candidates(pages)]
    with pytest.raises(ValueError):decode(json.dumps({'label':0,'evidence':evidence}),pages)


def test_reject_ambiguous_source():
    c = case()
    c['booklet'] = {'path': 'not-opened.pdf'}
    assert 'exactly one' in predict(c, Backend('mock'))['error']


def test_official_empty_url_does_not_fall_back(monkeypatch):
    monkeypatch.setenv('BASE_URL', '')
    monkeypatch.setenv('LLM_BASE_URL', 'https://api.publicai.co/v1')
    assert 'BASE_URL must not be empty' in predict(case(), Backend('openai'))['error']


@pytest.mark.parametrize('evidence', [[], [{'page': None, 'text': 'Ja'}]])
def test_scorer_reference_optional(evidence):
    gold = [{'id': str(i), 'label': i, 'task': 'beginner'} for i in range(3)]
    preds = [{'id': str(i), 'label': i, 'label_name': ['entailment', 'neutral', 'contradiction'][i],
              'evidence': evidence, 'metrics': {'input_tokens': 0, 'output_tokens': 0, 'inference_time_ms': 0}} for i in range(3)]
    report = score(gold, preds)
    assert report['macro_f1']['overall']['value'] == 1
    assert report['invalid_or_missing'] == 0
    assert report['evidence']['evaluated'] == 0


@pytest.mark.parametrize('page', [None, 1, 7])
def test_reference_page_canonicalization(page):
    raw={'label':0,'evidence':[{'span_id':candidates(['Ja'],True)[0]['span_id'],'page':page}]}
    with pytest.raises(ValueError):decode(json.dumps(raw),['Ja'],reference=True)


def test_reference_page_normalization_preserves_quote_check():
    with pytest.raises(ValueError):
        decode('{"label":0,"evidence":[{"page":1,"text":"invented"}]}', ['Ja'], reference=True)


@pytest.mark.parametrize('model', ['swiss-ai/apertus-v1.5-8b', 'swiss-ai/apertus-v1.5-70b'])
def test_publicai_request_shape_without_network(monkeypatch, model):
    import io
    import predict as engine
    monkeypatch.setenv('BASE_URL', 'https://api.publicai.co/v1')
    monkeypatch.setenv('API_KEY', 'dummy-test-key')
    monkeypatch.setenv('LLM_MODEL', model)
    monkeypatch.delenv('LLM_USER_AGENT', raising=False)
    captured = {}
    def fake_open(request, timeout):
        captured.update(url=request.full_url, headers=dict(request.header_items()), body=json.loads(request.data))
        return io.StringIO(json.dumps({'choices': [{'message': {'content': json.dumps({'label':0,'evidence':[{'span_id':json.loads(captured['body']['messages'][1]['content'])['source_spans'][0]['span_id']}]})}}],
                                      'usage': {'prompt_tokens': 11, 'completion_tokens': 7}}))
    monkeypatch.setattr(engine.urllib.request, 'urlopen', fake_open)
    p = predict(case('Ja'), Backend('openai'))
    assert p['label'] == 0 and 'error' not in p
    assert captured['url'] == 'https://api.publicai.co/v1/chat/completions'
    assert captured['body']['model'] == model
    assert captured['headers']['User-agent'] == 'HackApertus-OST/1.0 (Track-2A)'
    assert captured['headers']['Authorization'] == 'Bearer dummy-test-key'
    assert p['metrics']['input_tokens'] == 11 and p['metrics']['output_tokens'] == 7


@pytest.mark.parametrize('model', ['gpt-6.1-sol', 'swiss-ai/apertus-v1-8b', 'unapproved/model'])
def test_submission_backend_rejects_other_models_before_network(monkeypatch, model):
    import predict as engine
    monkeypatch.setenv('BASE_URL', 'https://api.publicai.co/v1')
    monkeypatch.setenv('API_KEY', 'dummy-test-key')
    monkeypatch.setenv('LLM_MODEL', model)
    called = []
    monkeypatch.setattr(engine.urllib.request, 'urlopen', lambda *args, **kwargs: called.append(True))
    assert 'only Apertus v1.5' in predict(case(), Backend('openai'))['error']
    assert not called
