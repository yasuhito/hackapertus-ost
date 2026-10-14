#!/usr/bin/env bash
# Direct bounded TRAIN-only entry point. No experiment initialization/logging.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.."
export PYTHONDONTWRITEBYTECODE=1 GIT_OPTIONAL_LOCKS=0
mode=${1:-}
candidate=${2:-}
if [[ ${TRAIN_ROUND:-} == v16 ]]; then
  candidate_pattern='^v16$'
elif [[ -z ${TRAIN_ROUND:-} ]]; then
  candidate_pattern='^v1[45]$'
else
  exit 2
fi
case "$mode" in
  --baseline) [[ $# == 1 ]] || exit 2 ;;
  --prepare-candidate) [[ $# == 2 && $candidate =~ $candidate_pattern ]] || exit 2 ;;
  --execute-approved) [[ $# == 4 && $candidate =~ $candidate_pattern && $3 == --attempt && $4 =~ ^[123]$ ]] || exit 2 ;;
  *) echo 'Usage: bash .auto/train_measure.sh --baseline | --prepare-candidate v14/v15 | --execute-approved v14/v15 --attempt 1/2/3' >&2; exit 2 ;;
esac
if [[ $mode == --prepare-candidate ]]; then
  exec python3 -B .auto/train_run.py --prepare-candidate "$candidate"
fi
# A failed measurement must never leave a successful selector from a prior run.
python3 -B - "$candidate" <<'PY'
import json, os, sys
from pathlib import Path
Path('.auto/check-context.json').write_text(json.dumps({'mode': 'train_pending', 'round': os.environ.get('TRAIN_ROUND', ''), 'candidate': sys.argv[1]}) + '\n')
PY
if [[ $mode == --baseline ]]; then
  python3 -B .auto/train_results.py --baseline
  python3 -B - <<'PY'
import json, os, sys
from pathlib import Path
sys.path.insert(0, '.auto')
import train_run as run
Path('.auto/check-context.json').write_text(json.dumps({'mode': 'train_baseline', 'round': run.ROUND, 'candidate': '', 'attempt': None, 'protocol_sha256': run.old.digest(run.CONTROL.read_bytes())}) + '\n')
PY
else
  python3 -B .auto/train_run.py --execute-approved "$candidate" --attempt "$4"
  python3 -B - "$candidate" "$4" <<'PY'
import json, os, sys
from pathlib import Path
sys.path.insert(0, '.auto')
import train_run as run
Path('.auto/check-context.json').write_text(json.dumps({'mode': 'train_candidate', 'round': run.ROUND, 'candidate': sys.argv[1], 'attempt': int(sys.argv[2]), 'protocol_sha256': run.old.digest(run.CONTROL.read_bytes())}) + '\n')
PY
fi
