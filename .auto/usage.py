"""Read-only usage accounting. Never inspect or emit saved response content."""
import hashlib
import json

MODELS = {'parent': 'swiss-ai/Apertus-v1.5-70B', 'child': 'swiss-ai/Apertus-v1.5-8B'}
GROUPS = ('parent', 'child', 'repair_window')
FIELDS = ('input_tokens', 'output_tokens', 'total_tokens', 'calls')


def digest(value):
    # Exact cscs_dev54.encode serialization, including default whitespace.
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                     allow_nan=False).encode()).hexdigest()


def load(path):
    return json.loads(path.read_text())


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def integer(value):
    return type(value) is int and value >= 0


def empty():
    return {group: dict.fromkeys(FIELDS, 0) for group in GROUPS}


def job_usage(job, split, summary):
    manifest, state = load(job / 'manifest.json'), load(job / 'state.json')
    require(state['manifest_sha256'] == digest(manifest), 'USAGE_MANIFEST_CHANGED')
    require(state['version'] == 'format-1' and state['blocked'] is False
            and state['reserved_tokens'] == 0, 'USAGE_STATE_BLOCKED')
    require(manifest['strategy'] == 'C' and manifest['role_models'] == MODELS
            and manifest['parent_completion_limit'] == 3
            and manifest['child_completion_limit'] == 2, 'USAGE_ROLE_MODELS_OR_CAPS')
    ids = [row['case']['id'] for row in manifest['frozen']]
    membership = {id: part for part in ('train', 'test') for id in split[part]}
    require(len(membership) == len(split['train']) + len(split['test'])
            and len(ids) == len(set(ids)) and set(ids) == set(membership), 'USAGE_SPLIT_IDS')
    totals, splits, slots = empty(), {part: empty() for part in ('train', 'test')}, set()
    # Validate both state record maps, as the frozen Ledger does. No content parsing.
    for group in ('attempts', 'cases'):
        for name, sha in state[group].items():
            require(isinstance(name, str) and name.endswith('.json')
                    and '/' not in name and '\\' not in name, 'USAGE_RECORD_PATH')
            path = job / name
            require(not path.is_symlink(), 'USAGE_RECORD_PATH')
            record = load(path)
            require(digest(record) == sha, 'USAGE_RECORD_CHANGED')
            if group == 'cases':
                continue
            role, index, number = record['role'], record['case_index'], record['number']
            require(role in MODELS, 'USAGE_UNKNOWN_ROLE')
            require(integer(index) and index < len(ids), 'USAGE_CASE_INDEX')
            require(integer(number) and number < (3 if role == 'parent' else 2), 'USAGE_REQUEST_NUMBER')
            slot = (index, role, number)
            require(slot not in slots, 'USAGE_DUPLICATE_SLOT')
            slots.add(slot)
            require(record['request_model'] == MODELS[role], 'USAGE_REQUEST_MODEL')
            require(all(record.get(key) is True for key in ('usage_known', 'usage_valid', 'safe')),
                    'USAGE_UNKNOWN_INVALID_OR_UNSAFE')
            usage = record.get('usage')
            require(isinstance(usage, dict) and all(integer(usage.get(key)) for key in
                    ('prompt_tokens', 'completion_tokens', 'total_tokens')), 'USAGE_INVALID_TOKENS')
            require(usage['total_tokens'] == usage['prompt_tokens'] + usage['completion_tokens'],
                    'USAGE_TOKEN_SUM')
            require(type(record.get('generation_requests')) is int
                    and record['generation_requests'] == 1, 'USAGE_RECORD_REQUESTS')
            values = dict(zip(FIELDS, (usage['prompt_tokens'], usage['completion_tokens'], usage['total_tokens'], 1)))
            groups = [role]
            if number >= (2 if role == 'parent' else 1):
                groups.append('repair_window')
            for target in (totals, splits[membership[ids[index]]]):
                for bucket in groups:
                    for key in FIELDS:
                        target[bucket][key] += values[key]
    tokens = totals['parent']['total_tokens'] + totals['child']['total_tokens']
    calls = totals['parent']['calls'] + totals['child']['calls']
    for source, token_key, call_key in ((state, 'tokens', 'requests'),
                                       (summary, 'actual_total_tokens', 'generation_requests')):
        require(integer(source.get(token_key)) and source[token_key] == tokens
                and integer(source.get(call_key)) and source[call_key] == calls, 'USAGE_LEDGER_MISMATCH')
    for key in FIELDS:
        require(totals['repair_window'][key] <= totals['parent'][key] + totals['child'][key], 'USAGE_REPAIR_NOT_SUBSET')
        for group in GROUPS:
            require(totals[group][key] == sum(splits[part][group][key] for part in splits), 'USAGE_SPLIT_SUM')
    return {'totals': totals, 'splits': splits}


def candidate_usage(out, version, summaries, split):
    return [job_usage(out / f'prompt-C-{version}-r{repeat}', split, summary)
            for repeat, summary in enumerate(summaries, 1)]
