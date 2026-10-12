import json
from pathlib import Path
import sys
import time

import pytest

sys.path.insert(0, str(Path(__file__).parent))
import run_comparison as r
from test_comparison import offline, setup, Fake, response, tool


def test_late_state_fsync_failure_keeps_independent_fence(tmp_path, monkeypatch):
    job, manifest = setup(tmp_path)
    fake = Fake()
    original = r.legacy.state_write
    writes = []
    def late(path, state):
        original(path, state)
        writes.append(1)
        if len(writes) == 2:
            raise OSError('late fsync')
    monkeypatch.setattr(r.legacy, 'state_write', late)
    with pytest.raises(OSError):
        r.run(job, manifest, fake)
    assert len(fake.calls) == 1 and (job / 'inflight.json').exists()
    assert r.legacy.load(job / 'state.json')['tokens'] == 100
    with pytest.raises(r.Stop):
        r.run(job, manifest, fake)
    assert len(fake.calls) == 1


def test_per_request_case_deadline_preserves_uncertain_fence(tmp_path):
    job, manifest = setup(tmp_path)
    calls = []
    class Slow:
        def request(self, *a):
            calls.append(1)
            time.sleep(.1)
    ledger = r.Ledger(job, manifest, lambda _: Slow())
    with pytest.raises(r.Stop):
        ledger.post(r.MODELS[0], 0, 'parent', 0, {'model': r.MODELS[0]}, deadline=time.monotonic() + .01)
    assert len(calls) == 1 and (job / 'inflight.json').exists()
    with pytest.raises(r.Stop):
        r.Ledger(job, manifest, lambda _: Slow())
    assert len(calls) == 1


def test_malformed_tool_envelope_usage_saved_but_fenced(tmp_path):
    job, manifest = setup(tmp_path)
    class Malformed:
        def request(self, *a):
            return response(r.MODELS[0], calls=[{'type': 'function', 'function': {'name': 'submit', 'arguments': '{}'}}])
    with pytest.raises(r.Stop):
        r.run(job, manifest, lambda _: Malformed())
    assert (job / 'inflight.json').exists()
    assert r.legacy.load(job / 'state.json')['tokens'] == 100


def test_confirmed_child_prefix_replays_without_extra_post(tmp_path):
    job, manifest = setup(tmp_path, 'B')
    calls = []
    class Native:
        def request(self, method, path, payload):
            calls.append(payload)
            name = payload['tool_choice']['function']['name']
            return response(r.MODELS[0], calls=[tool(name, {} if name == 'subagent' else {'label': 1, 'candidate_ids': []})])
    ledger = r.Ledger(job, manifest, lambda _: Native())
    def interrupted(role, number, payload):
        if role == 'parent' and number == 1:
            raise RuntimeError('simulated process loss after confirmed child')
        return ledger.post(r.MODELS[0], 0, role, number, payload)
    with pytest.raises(RuntimeError):
        r.run_b(manifest['frozen'][0], r.MODELS[0], interrupted, seconds=30)
    assert len(calls) == 2 and not (job / 'inflight.json').exists()
    resumed = r.Ledger(job, manifest, lambda _: Native())
    args, _, sdk = r.run_b(manifest['frozen'][0], r.MODELS[0], lambda role, number, payload: resumed.post(r.MODELS[0], 0, role, number, payload), seconds=30)
    assert args == {'label': 1, 'candidate_ids': []}
    assert len(calls) == 3 and sdk['counts'] == {'parent': 2, 'child': 1}
    assert resumed.state['tokens'] == 300


def test_http_status_diagnostic_without_reading_error_body(tmp_path, monkeypatch):
    job, manifest = setup(tmp_path)
    monkeypatch.setenv('BASE_URL', 'http://injected.invalid/v1')
    monkeypatch.setenv('API_KEY', 'offline-synthetic')
    class Connection:
        def __init__(self, *a, **k):
            pass
        def set_debuglevel(self, n):
            pass
        def request(self, *a, **k):
            pass
        def getresponse(self):
            class Response:
                status = 400
                def read(self, *a):
                    pytest.fail('HTTP error body must never be read/logged/forwarded')
            return Response()
        def close(self):
            pass
    with pytest.raises(r.Stop):
        r.run(job, manifest, lambda model: r.Transport(model, submitted=True, factory=Connection))
    assert r.legacy.load(job / 'STOP.json')['http_status'] == 400
    assert (job / 'inflight.json').exists()
    assert r.legacy.load(job / 'state.json')['reserved_tokens'] == r.RESERVE
