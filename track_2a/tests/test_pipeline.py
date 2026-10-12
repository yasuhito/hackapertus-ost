import json
from pathlib import Path
import sys
import subprocess
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from predict import Backend, context, decode, predict
from score import score


def case(text='Der Bundesrat lehnt die Initiative ab.'):
    return {'id': 'a', 'reference': {'text': text}, 'claim': {'text': text}}


def test_mock_verbatim():
    p = predict(case(), Backend('mock'))
    assert p['label'] == 0 and p['label_name'] == 'entailment'
    assert p['evidence'] == [{'page': 1, 'text': case()['reference']['text']}]
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


def test_contradiction_and_fence():
    assert decode('```json\n{"label":2,"evidence":[{"page":1,"text":"NON"}]}\n```', ['NON'])[0] == 2


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
    assert len(pages) == 2 and '[PAGE 2]' in messages[1]['content']
    result = predict(c, Backend('mock'), tmp_path)
    assert result['evidence'][0]['page'] == 2


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


def test_openai_wire_local_only(monkeypatch):
    captured = {}
    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            captured.update(path=self.path, header=self.headers['User-Agent'],
                            body=json.loads(self.rfile.read(int(self.headers['Content-Length']))))
            self.send_response(200); self.end_headers()
            self.wfile.write(json.dumps({'choices': [{'message': {'content': json.dumps({'label': 0, 'evidence': [{'page': 1, 'text': 'Ja'}]})}}],
                                        'usage': {'prompt_tokens': 11, 'completion_tokens': 7}}).encode())
        def log_message(self, *args): pass
    server = HTTPServer(('127.0.0.1', 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
    monkeypatch.setenv('LLM_BASE_URL', f'http://127.0.0.1:{server.server_port}/v1')
    monkeypatch.setenv('LLM_MODEL', 'swiss-ai/apertus-v1.5-70b')
    monkeypatch.setenv('LLM_USER_AGENT', 'test-agent')
    try:
        p = predict(case('Ja'), Backend('openai'))
        assert p['label'] == 0 and p['metrics']['input_tokens'] == 11
        assert captured['path'] == '/v1/chat/completions' and captured['header'] == 'test-agent'
        assert captured['body']['model'].endswith('70b')
    finally:
        server.shutdown(); server.server_close(); thread.join()


def test_no_split_leakage():
    data = Path(__file__).resolve().parents[1] / 'data'
    train = [json.loads(l) for l in (data / 'train_cases.jsonl').read_text().splitlines()]
    dev = [json.loads(l) for l in (data / 'dev_cases.jsonl').read_text().splitlines()]
    assert not {r['date'] for r in train} & {r['date'] for r in dev}
    assert len(train) + len(dev) == 1488
