"""HTTP500-only retries around UNCHANGED Transport; physical accounting only."""
import collections
import math
import signal
import time

CAP = 300
RESERVE = 262400
BUDGET = 78720000
BYTE_CAP = 240000
WAITS = (2, 4, 8, 16)


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
        self.r, self.job, self.deadline = runner, job, deadline
        self.path = job / 'physical'
        self.path.mkdir(mode=0o700)  # never resume/replay
        self.records = []
        self.charged = 0
        self.clients = {}

    def guard(self, cutoff, payload=None, wait=0):
        if time.monotonic() + wait >= min(cutoff, self.deadline):
            raise self.r.Stop('PHYSICAL_DEADLINE_STOP')
        if len(self.records) >= CAP or self.charged + RESERVE > BUDGET:
            raise self.r.Stop('PHYSICAL_BUDGET_STOP')
        if payload is not None and len(self.r.legacy.encode(payload)) > BYTE_CAP:
            raise self.r.Stop('PAYLOAD_BYTE_LIMIT')

    def client(self, model, base=None):
        ledger = self
        base = base or self.r.Transport
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
                value = self.clients[model].request(method, path, payload)
                status = 200
            except BaseException as exc:
                failure = exc
                status = getattr(exc, 'http_status', None)
                if type(status) is not int:
                    status = None
            safe = failure is None and response_safe(r, value, model)
            result = {**before, 'http_status': status, 'safe_success': safe,
                      'usage_known': safe, 'usage': value['usage'] if safe else None,
                      'response_sha256': r.legacy.digest(r.legacy.encode(value)) if safe else None,
                      'response': value if safe else None,
                      'raw_body_unavailable': failure is not None,
                      'network_seconds': time.monotonic() - started,
                      'unknown_charge': 0 if safe else RESERVE,
                      'wait_seconds': WAITS[attempt - 1] if status == 500 and attempt < 5 else 0}
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
            # Only original Stop carrying known 500 is retryable.
            if not isinstance(failure, r.Stop) or status != 500 or attempt == 5:
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
                    or result['unknown_charge'] != 0 or result['wait_seconds'] != 0):
                raise ValueError('PHYSICAL_SUCCESS_CHANGED')
            charged += result['usage']['total_tokens']
        else:
            wait = WAITS[len(group) - 1] if len(group) < 5 else None
            if (result['http_status'] != 500 or result['usage_known'] or result['usage'] is not None
                    or not result['raw_body_unavailable'] or result['response'] is not None
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
            'physical_network_seconds': sum(x['network_seconds'] for x in records),
            'physical_backoff_seconds': sum(x['wait_seconds'] for x in records)}
