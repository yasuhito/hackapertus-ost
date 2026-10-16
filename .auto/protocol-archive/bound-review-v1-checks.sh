#!/usr/bin/env bash
# run_experiment starts checks in another process: use the successful measurement context.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.."
export PYTHONDONTWRITEBYTECODE=1
python3 -B - <<'PY'
import json
import os
from pathlib import Path
import subprocess
import sys
context = json.loads(Path('.auto/check-context.json').read_text())
mode, candidate = context['mode'], context['candidate']
# BEGIN bound-review-v1 additive
if mode == 'bound_review':
    subprocess.run(['/tmp/hackapertus-ost-contract/.venv/bin/python', '-B', '-Werror::ResourceWarning', '.auto/bound_review_research.py', '--check-context'], check=True)
    sys.exit(0)
# END bound-review-v1 additive
# BEGIN fragment-review-v1 additive
if mode == 'fragment_review':
    subprocess.run(['/tmp/hackapertus-ost-contract/.venv/bin/python', '-B', '-Werror::ResourceWarning', '.auto/fragment_review_research.py', '--check-context'], check=True)
    sys.exit(0)
# END fragment-review-v1 additive
if mode == 'role_review':
    subprocess.run(['/tmp/hackapertus-ost-contract/.venv/bin/python', '-B', '-Werror::ResourceWarning', '.auto/role_review_research.py', '--check-context'], check=True)
elif mode in ('fullbranch_reference', 'fullbranch_candidate'):
    subprocess.run(['/tmp/hackapertus-ost-contract/.venv/bin/python', '-B', '-Werror::ResourceWarning', '.auto/fullbranch_public60.py', '--check'], check=True)
elif mode == 'provider_schema_edge':
    subprocess.run(['/tmp/hackapertus-ost-contract/.venv/bin/python', '-B', '.auto/provider_schema_edge_probe.py', '--check'], check=True)
elif mode == 'provider_schema_empty':
    subprocess.run(['/tmp/hackapertus-ost-contract/.venv/bin/python', '-B', '.auto/provider_schema_empty_source.py', '--check'], check=True)
elif mode == 'provider_schema_empty_retry':
    subprocess.run(['/tmp/hackapertus-ost-contract/.venv/bin/python', '-B', '.auto/provider_schema_empty_retry.py', '--check'], check=True)
elif mode == 'provider_schema_unique_ids':
    assert context['report_phase'] in ('baseline', 'candidate'), 'REPORT_PHASE_INVALID'
    subprocess.run(['/tmp/hackapertus-ost-contract/.venv/bin/python', '-B', '.auto/provider_schema_unique_ids.py', '--check', '--report-phase', context['report_phase']], check=True)
elif mode == 'provider_schema_branch_closure':
    subprocess.run(['/tmp/hackapertus-ost-contract/.venv/bin/python', '-B', '.auto/provider_schema_branch_closure.py', '--check'], check=True)
elif mode == 'provider_schema_probe':
    subprocess.run(['/tmp/hackapertus-ost-contract/.venv/bin/python', '-B', '.auto/provider_schema_probe.py', '--check'], check=True)
elif mode == 'provider_schema_probe_recovered':
    subprocess.run(['/tmp/hackapertus-ost-contract/.venv/bin/python', '-B', '.auto/provider_schema_probe_recovery.py', '--check'], check=True)
elif mode in ('train_baseline', 'train_candidate'):
    import sys
    sys.path.insert(0, '.auto')
    selected_round = context.get('round', '')
    assert selected_round in ('', 'v16'), 'TRAIN_ROUND_CONTEXT_INVALID'
    assert os.environ.get('TRAIN_ROUND', selected_round) == selected_round, 'TRAIN_ROUND_SELECTOR_CONFLICT'
    os.environ['TRAIN_ROUND'] = selected_round
    import train_run as train
    assert context.get('protocol_sha256') == train.old.digest(train.CONTROL.read_bytes()), 'TRAIN_CONTEXT_CHANGED'
    train.verify_protocol()
    if mode == 'train_baseline':
        assert candidate == '' and context.get('attempt') is None, 'TRAIN_SELECTOR_CONFLICT'
        command = [sys.executable, '-B', '.auto/train_results.py', '--baseline', '--check']
    else:
        assert candidate in train.VERSIONS and type(context.get('attempt')) is int and context['attempt'] in (1, 2, 3), 'TRAIN_SELECTOR_MISSING'
        command = ['/tmp/ost-official-evaluator-3U4yO9/env/bin/python', '-B', '.auto/train_results.py', '--candidate', candidate, '--attempt', str(context['attempt']), '--check']
    subprocess.run(command, check=True)
elif mode == 'feedback_h2_g2_candidate':
    subprocess.run(['/tmp/hackapertus-ost-contract/.venv/bin/python', '-B', '.auto/feedback_research_h2_g2.py', '--check'], check=True)
elif mode == 'feedback_h2_candidate':
    subprocess.run(['/tmp/hackapertus-ost-contract/.venv/bin/python', '-B', '.auto/feedback_research_h2.py', '--check'], check=True)
elif mode in ('feedback_reference', 'feedback_candidate'):
    subprocess.run(['/tmp/hackapertus-ost-contract/.venv/bin/python', '-B', '.auto/feedback_research.py', '--check'], check=True)
elif mode in ('public_continue_baseline', 'public_continue_candidate'):
    subprocess.run(['/tmp/hackapertus-ost-contract/.venv/bin/python', '-B', '.auto/public_validation_continue.py', '--check'], check=True)
elif mode in ('public_baseline', 'public_candidate'):
    subprocess.run(['/tmp/hackapertus-ost-contract/.venv/bin/python', '-B', '.auto/public_validation.py', '--check'], check=True)
elif mode == 'baseline':
    assert candidate == '' and not os.environ.get('AUTO_CANDIDATE'), 'CHECK_SELECTOR_CONFLICT'
    subprocess.run(['bash', '.auto/measure.sh', '--baseline'], check=True)
else:
    assert mode == 'candidate' and candidate in ('v3', 'v4', 'v5', 'v6', 'v7', 'v8', 'v9', 'v10', 'v11', 'v12', 'v13', 'v12-retry1', 'v13-retry1'), 'CHECK_SELECTOR_MISSING'
    assert not os.environ.get('AUTO_BASELINE'), 'CHECK_SELECTOR_CONFLICT'
    assert os.environ.get('AUTO_CANDIDATE', candidate) == candidate, 'CHECK_SELECTOR_CONFLICT'
    subprocess.run([sys.executable, '-B', '.auto/results.py', '--candidate', candidate, '--check'], check=True)
PY
