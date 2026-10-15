"""Prospective transient retries; Root transport remains unchanged."""
import collections
import errno
import http.client
import re
import math
import signal
import time

CAP = 300
RESERVE = 262400
BUDGET = 78720000
BYTE_CAP = 240000
WAITS = (2, 4, 8, 16)


ABSOLUTE_STOP = 1792098000
BODY_CAP = 65536


def classify(status, excerpt='', kind=None, error_errno=None):
    text = excerpt.lower()
    permanent = re.search(r'unsupported|grammar|schema|\bauth|credential|api[ _-]?key|permission|invalid[ _-]?(input|request|parameter)|unauthorized|forbidden', text)
    if permanent or status in (200, 401, 403):
        return 'permanent'
    if status in (408, 425, 429) or type(status) is int and 500 <= status <= 599:
        return 'transient_http'
    if status is not None:
        return 'explicit_capacity' if re.search(r'overload|capacity|rate[ _-]?limit|temporar(?:y|ily)[ _-]unavailable', text) else 'permanent'
    if kind in ('TimeoutError', 'ConnectionResetError', 'ConnectionAbortedError') or error_errno in (errno.ETIMEDOUT, errno.ECONNRESET, errno.ECONNABORTED, errno.EPIPE, errno.EAGAIN):
        return 'transient_network'
    return 'uncertain_transport'


def redacted_excerpt(raw, authorization):
    """Redact before clipping, including a secret prefix cut by the bounded read."""
    secrets = [value.encode('utf-8') for value in (authorization, authorization.removeprefix('Bearer ')) if value]
    for secret in secrets:
        raw = raw.replace(secret, b'[REDACTED]')
    for secret in secrets:
        for size in range(min(len(secret)-1, len(raw)), 0, -1):
            if raw.endswith(secret[:size]):
                raw = raw[:-size] + b'[REDACTED]'
                break
    return raw.decode('utf-8', errors='replace').encode('utf-8')[:BODY_CAP].decode('utf-8', errors='ignore')


def experimental_transport(core, cutoff, factory=None):
    """Capture only bounded redacted non-200 bodies and exception *types*.

    A per-instance factory proxy lets unchanged Root perform every request guard.
    It never logs headers, key paths, credentials or exception messages.
    """
    class ExperimentalTransport(core.Transport):
        def request(self, method, path, payload):
            captured = {}
            remaining = min(min(cutoff, getattr(self, 'request_cutoff', cutoff)) - time.monotonic(), ABSOLUTE_STOP - time.time())
            if remaining <= 0:
                raise core.Stop('PHYSICAL_DEADLINE_STOP')
            real = factory or (http.client.HTTPSConnection if self.parsed.scheme == 'https' else http.client.HTTPConnection)
            def make(*args, **kwargs):
                kwargs['timeout'] = min(kwargs.get('timeout', 45), remaining)
                inner = real(*args, **kwargs)
                class Proxy:
                    def set_debuglevel(self, value):
                        inner.set_debuglevel(0)
                    def request(self, *a, **kw):
                        # Authorization exists only in this local closure.
                        self.secret = kw.get('headers', {}).get('Authorization', '')
                        try:
                            return inner.request(*a, **kw)
                        except Exception as exc:
                            captured.update(exception_kind=type(exc).__name__, error_errno=getattr(exc, 'errno', None))
                            raise
                    def getresponse(self):
                        try:
                            response = inner.getresponse()
                            captured['http_status'] = response.status
                            if response.status != 200:
                                secret = getattr(self, 'secret', '')
                                raw = response.read(BODY_CAP + len(secret.encode('utf-8')))
                                captured['error_excerpt'] = redacted_excerpt(raw, secret)
                            class ResponseProxy:
                                status = response.status
                                def read(self, *a, **kw):
                                    try:
                                        return response.read(*a, **kw)
                                    except Exception as exc:
                                        captured.update(exception_kind=type(exc).__name__, error_errno=getattr(exc, 'errno', None))
                                        raise
                            return ResponseProxy()
                        except Exception as exc:
                            captured.update(exception_kind=type(exc).__name__, error_errno=getattr(exc, 'errno', None))
                            raise
                    def close(self):
                        inner.close()
                return Proxy()
            previous = self.factory
            self.factory = make
            try:
                return super().request(method, path, payload)
            except core.Stop as exc:
                for key, value in captured.items():
                    setattr(exc, key, value)
                exc.error_classification = classify(captured.get('http_status'), captured.get('error_excerpt', ''), captured.get('exception_kind'), captured.get('error_errno'))
                raise
            except Exception as exc:
                error = core.Stop('TRANSPORT_UNCERTAIN_NO_RETRY')
                captured.update(exception_kind=type(exc).__name__, error_errno=getattr(exc, 'errno', None))
                for key, value in captured.items():
                    setattr(error, key, value)
                error.error_classification = classify(captured.get('http_status'), captured.get('error_excerpt', ''), captured.get('exception_kind'), captured.get('error_errno'))
                raise error from None
            finally:
                self.factory = previous
    return ExperimentalTransport


def response_safe(r, value, model):
    if not isinstance(value, dict):
        return False
    u = value.get('usage')
    choices = value.get('choices')
    return (r.legacy.usage_valid(u) and r.valid_usage_details(u)
            and value.get('model') == model and 'error' not in value
            and isinstance(choices, list) and len(choices) == 1
            and isinstance(choices[0], dict)
            and choices[0].get('finish_reason') in ('stop', 'tool_calls', 'length')
            and isinstance(choices[0].get('message'), dict)
            and r.wire_shape_safe(choices[0]['message']))


class PhysicalLedger:
    def __init__(self, runner, job, deadline):
        self.r, self.job, self.deadline = runner, job, min(deadline, time.monotonic() + ABSOLUTE_STOP - time.time())
        self.path = job / 'physical'
        self.path.mkdir(mode=0o700)  # never resume/replay
        self.records = []
        self.charged = 0
        self.clients = {}

    def guard(self, cutoff, payload=None, wait=0):
        if time.time() + wait >= ABSOLUTE_STOP or time.monotonic() + wait >= min(cutoff, self.deadline):
            raise self.r.Stop('PHYSICAL_DEADLINE_STOP')
        if len(self.records) >= CAP or self.charged + RESERVE > BUDGET:
            raise self.r.Stop('PHYSICAL_BUDGET_STOP')
        if payload is not None and len(self.r.legacy.encode(payload)) > BYTE_CAP:
            raise self.r.Stop('PAYLOAD_BYTE_LIMIT')

    def client(self, model, base=None):
        ledger = self
        base = base or experimental_transport(self.r, self.deadline)
        class RetryingGuarded:
            def request(self, method, path, payload):
                return ledger.request(model, base, method, path, payload)
        return RetryingGuarded()

    def request(self, model, base, method, path, payload):
        r = self.r
        remaining = signal.getitimer(signal.ITIMER_REAL)[0]
        cutoff = time.monotonic() + min(60, remaining if remaining > 0 else 60)
        logical = r.legacy.load(self.job / 'inflight.json')
        digest = r.legacy.digest(r.legacy.encode(payload))
        if logical['payload_sha256'] != digest or logical['request_model'] != model:
            raise r.Stop('PHYSICAL_LOGICAL_BINDING_FAILED')
        for attempt in range(1, 6):
            self.guard(cutoff, payload)
            n = len(self.records) + 1
            stem = f'{n:04d}'
            before = {'physical_index': n, 'logical_record': logical['record'],
                      'logical_payload_sha256': digest, 'request_model': model,
                      'role': logical['role'], 'attempt': attempt,
                      'reserved_charge': RESERVE, 'charged_before': self.charged}
            r.legacy.exclusive(self.path / (stem + '-before.json'), before)
            r.legacy.exclusive(self.path / 'inflight.json', before)
            self.charged += RESERVE
            started = time.monotonic()
            value = None
            status = None
            failure = None
            try:
                # Construction too is inside the immutable attempt reservation.
                if time.monotonic() >= min(cutoff, self.deadline):
                    raise r.Stop('PHYSICAL_DEADLINE_STOP')
                if model not in self.clients:
                    self.clients[model] = base(model)
                if time.monotonic() >= min(cutoff, self.deadline):
                    raise r.Stop('PHYSICAL_DEADLINE_STOP')
                self.clients[model].request_cutoff = min(cutoff, self.deadline)
                timer = signal.getitimer(signal.ITIMER_REAL)[0]
                request_seconds = min(cutoff - time.monotonic(), self.deadline - time.monotonic(), ABSOLUTE_STOP - time.time())
                signal.setitimer(signal.ITIMER_REAL, min(timer, request_seconds) if timer > 0 else request_seconds)
                try:
                    value = self.clients[model].request(method, path, payload)
                finally:
                    signal.setitimer(signal.ITIMER_REAL, max(.000001, timer - (time.monotonic() - started)) if timer > 0 else 0)
                status = 200
            except BaseException as exc:
                failure = exc
                status = getattr(exc, 'http_status', None)
                if type(status) is not int:
                    status = None
            classification = classify(status, getattr(failure, 'error_excerpt', ''), getattr(failure, 'exception_kind', None), getattr(failure, 'error_errno', None)) if failure else 'invalid_success'
            retryable = failure is not None and classification in ('transient_http', 'explicit_capacity', 'transient_network')
            safe = failure is None and response_safe(r, value, model)
            result = {**before, 'http_status': status, 'safe_success': safe,
                      'usage_known': safe, 'usage': value['usage'] if safe else None,
                      'response_sha256': r.legacy.digest(r.legacy.encode(value)) if safe else None,
                      'response': value if safe else None,
                      'raw_body_unavailable': not hasattr(failure, 'error_excerpt'),
                      'error_excerpt': getattr(failure, 'error_excerpt', ''),
                      'exception_kind': getattr(failure, 'exception_kind', type(failure).__name__ if failure else None),
                      'error_errno': getattr(failure, 'error_errno', None),
                      'error_classification': 'success' if safe else classification,
                      'network_seconds': time.monotonic() - started,
                      'unknown_charge': 0 if safe else RESERVE,
                      'wait_seconds': WAITS[attempt - 1] if retryable and attempt < 5 else 0}
            if safe:
                self.charged += value['usage']['total_tokens'] - RESERVE
            result['charged_after'] = self.charged
            r.legacy.exclusive(self.path / (stem + '-result.json'), result)
            self.records.append(result)
            if safe:
                if self.charged > BUDGET:
                    raise r.Stop('PHYSICAL_BUDGET_STOP')
                (self.path / 'inflight.json').unlink()
                return value
            # Only classified transient failures retry; known HTTP200 stays fenced.
            if not isinstance(failure, r.Stop) or not retryable or attempt == 5:
                if failure is not None:
                    raise failure
                raise r.Stop('UNKNOWN_MODEL_USAGE_OR_RESPONSE_ALL_STOP')
            wait = WAITS[attempt - 1]
            self.guard(cutoff, payload, wait)
            r.legacy.exclusive(self.path / (stem + '-wait.json'), {'seconds': wait})
            time.sleep(wait)
            self.guard(cutoff, payload)
            (self.path / 'inflight.json').unlink()
        raise r.Stop('RETRY_EXHAUSTED')


def verify(r, job):
    """Reconstruct physical budget and bijection to original logical ledger."""
    path = job / 'physical'
    if not path.is_dir() or (path / 'inflight.json').exists():
        raise ValueError('PHYSICAL_INCOMPLETE')
    state = r.legacy.load(job / 'state.json')
    logical = {n: r.legacy.load(job / n) for n in state['attempts']}
    files = set()
    charged = 0
    records = []
    groups = collections.OrderedDict()
    for index, result_path in enumerate(sorted(path.glob('*-result.json')), 1):
        stem = f'{index:04d}'
        before_path = path / (stem + '-before.json')
        if result_path.name != stem + '-result.json':
            raise ValueError('PHYSICAL_SEQUENCE_CHANGED')
        before, result = r.legacy.load(before_path), r.legacy.load(result_path)
        if (any(result.get(k) != v for k, v in before.items())
                or before['physical_index'] != index or before['charged_before'] != charged
                or before['reserved_charge'] != RESERVE or index > CAP
                or charged + RESERVE > BUDGET):
            raise ValueError('PHYSICAL_BUDGET_CHANGED')
        files.update((before_path.name, result_path.name))
        group = groups.setdefault(before['logical_record'], [])
        group.append(result)
        if before['attempt'] != len(group) or len(group) > 5:
            raise ValueError('PHYSICAL_RETRY_CHANGED')
        target = logical.get(before['logical_record'])
        if (target is None or before['logical_payload_sha256'] != target['payload_sha256']
                or before['request_model'] != target['request_model'] or before['role'] != target['role']):
            raise ValueError('PHYSICAL_LOGICAL_CHANGED')
        if (type(result['network_seconds']) not in (int, float)
                or not math.isfinite(result['network_seconds']) or result['network_seconds'] < 0):
            raise ValueError('PHYSICAL_LATENCY_CHANGED')
        safe = result['safe_success']
        if safe:
            if (not response_safe(r, result['response'], before['request_model'])
                    or result['http_status'] != 200 or not result['usage_known']
                    or result['usage'] != result['response']['usage']
                    or result['response'] != target['response']
                    or result['response_sha256'] != r.legacy.digest(r.legacy.encode(target['response']))
                    or result['unknown_charge'] != 0 or result['wait_seconds'] != 0
                    or result['error_classification'] != 'success' or result['error_excerpt'] != ''
                    or result['exception_kind'] is not None or result['error_errno'] is not None):
                raise ValueError('PHYSICAL_SUCCESS_CHANGED')
            charged += result['usage']['total_tokens']
        else:
            wait = WAITS[len(group) - 1] if len(group) < 5 else None
            if (classify(result['http_status'], result['error_excerpt'], result['exception_kind'], result['error_errno']) not in ('transient_http', 'explicit_capacity', 'transient_network')
                    or result['error_classification'] != classify(result['http_status'], result['error_excerpt'], result['exception_kind'], result['error_errno'])
                    or result['usage_known'] or result['usage'] is not None
                    or result['response'] is not None
                    or result['response_sha256'] is not None or result['unknown_charge'] != RESERVE
                    or result['wait_seconds'] != wait):
                raise ValueError('PHYSICAL_UNKNOWN_CHANGED')
            wp = path / (stem + '-wait.json')
            if r.legacy.load(wp) != {'seconds': wait}:
                raise ValueError('PHYSICAL_WAIT_CHANGED')
            files.add(wp.name)
            charged += RESERVE
        if charged != result['charged_after'] or charged > BUDGET:
            raise ValueError('PHYSICAL_CHARGE_CHANGED')
        records.append(result)
    if (set(groups) != set(logical) or not records
            or any(not g[-1]['safe_success'] or any(x['safe_success'] for x in g[:-1]) for g in groups.values())
            or set(p.name for p in path.iterdir()) != files):
        raise ValueError('PHYSICAL_BIJECTION_CHANGED')
    unknown = sum(not x['safe_success'] for x in records)
    known = sum(x['usage']['total_tokens'] for x in records if x['safe_success'])
    if known != state['tokens']:
        raise ValueError('PHYSICAL_KNOWN_USAGE_CHANGED')
    return {'physical_requests': len(records), 'unknown_failed_count': unknown,
            'reserved_unknown_charge': unknown * RESERVE, 'charged_tokens': charged,
            'full_usage_known': not unknown, 'full_total_tokens': None if unknown else known,
            'known_successful_tokens': known, 'financial_cost': 'unavailable',
            'physical_parent_calls': sum(x['role'] == 'parent' for x in records),
            'physical_child_calls': sum(x['role'] == 'child' for x in records),
            'physical_reviewer_calls': sum(x['role'] == 'reviewer' for x in records),
            'physical_network_seconds': sum(x['network_seconds'] for x in records),
            'physical_backoff_seconds': sum(x['wait_seconds'] for x in records)}
