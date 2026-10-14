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
if mode == 'baseline':
    assert candidate == '' and not os.environ.get('AUTO_CANDIDATE'), 'CHECK_SELECTOR_CONFLICT'
    subprocess.run(['bash', '.auto/measure.sh', '--baseline'], check=True)
else:
    assert mode == 'candidate' and candidate in ('v3', 'v4', 'v5', 'v6', 'v7', 'v8', 'v9', 'v10', 'v11', 'v12', 'v13'), 'CHECK_SELECTOR_MISSING'
    assert not os.environ.get('AUTO_BASELINE'), 'CHECK_SELECTOR_CONFLICT'
    assert os.environ.get('AUTO_CANDIDATE', candidate) == candidate, 'CHECK_SELECTOR_CONFLICT'
    subprocess.run([sys.executable, '-B', '.auto/results.py', '--candidate', candidate, '--check'], check=True)
PY
