"""Measure a fake Apertus request locally, without credentials or remote access."""
import json
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from predict import Backend, context

@pytest.mark.parametrize('scenario', ['usage', 'missing_usage', 'http_error'])
def test_request_observer(monkeypatch, scenario):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args): pass
        def do_POST(self):
            self.rfile.read(int(self.headers['Content-Length']))
            time.sleep(0.035)
            payload = {'id':'fake-response','model':'swiss-ai/apertus-v1.5-8b',
                       'choices':[{'message':{'content':'{"label":1,"evidence":[]}'}}]}
            if scenario == 'usage':
                payload['usage'] = {'prompt_tokens':100, 'completion_tokens':20,
                    'prompt_tokens_details':{'cached_tokens':60},
                    'completion_tokens_details':{'reasoning_tokens':8}}
            self.send_response(503 if scenario == 'http_error' else 200)
            self.end_headers(); self.wfile.write(json.dumps(payload).encode())
    server = HTTPServer(('127.0.0.1',0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
    for name in ['LLM_MODEL','LLM_NAME','API_KEY','LLM_API_KEY','PUBLICAI_API_KEY']:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv('BASE_URL',f'http://127.0.0.1:{server.server_port}/v1')
    events=[]; pages,messages=context({'id':'fixture','reference':{'text':'A'},'claim':{'text':'B'}}, Path('.'))
    try:
        if scenario == 'http_error':
            with pytest.raises(Exception): Backend('openai', events.append).complete(messages,pages,'B')
        else:
            raw,usage=Backend('openai', events.append).complete(messages,pages,'B')
            assert json.loads(raw)['label'] == 1
        assert len(events)==2 and events[0]['event']=='request_started'
        terminal=events[-1]
        assert terminal['finished_monotonic']-terminal['started_monotonic'] >= .03
        if scenario=='http_error':
            assert terminal['event']=='request_failed' and terminal['raw_usage'] is None
        else:
            assert terminal['event']=='response_completed' and terminal['api_wait_ms'] >= 30
            assert terminal['raw_usage']==(usage if scenario=='usage' else None)
            assert terminal['response_id']=='fake-response'
        assert 'headers' not in json.dumps(events).lower()
    finally:
        server.shutdown(); server.server_close(); thread.join()
