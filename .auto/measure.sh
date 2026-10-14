#!/usr/bin/env bash
# No candidate selection or approval is inferred from historical results.
set -euo pipefail
# The experiment tool requires this canonical entry point; TRAIN controls stay separate.
case "${1:-}" in
  --train-baseline)
    [[ $# == 1 ]] || exit 2
    exec bash "$(dirname -- "${BASH_SOURCE[0]}")/train_measure.sh" --baseline ;;
  --train-prepare-candidate)
    [[ $# == 2 ]] || exit 2
    exec bash "$(dirname -- "${BASH_SOURCE[0]}")/train_measure.sh" --prepare-candidate "$2" ;;
  --train-execute-approved)
    [[ $# == 4 ]] || exit 2
    exec bash "$(dirname -- "${BASH_SOURCE[0]}")/train_measure.sh" --execute-approved "$2" "$3" "$4" ;;
esac
usage() {
  printf '%s\n' \
    'Usage: .auto/measure.sh --baseline | --saved VERSION | --prepare-candidate VERSION | --execute-approved VERSION' \
    'Default refuses. --baseline is offline, min_Q_gain_v5=0. --saved only reads completed reports.' \
    'Preparation is offline and creates no jobs or prompts. Execution requires explicit selected-candidate metadata approval.' \
    'Selectors: v11..v13 or v12-retry1/v13-retry1; saved also accepts v3..v10. Only exact approved fresh v12-retry1/v13-retry1 jobs; no same-job restart, resume or adoption.' \
    'Tool callers export AUTO_CANDIDATE to the selected future version. Baseline checks use AUTO_BASELINE=1.'
}
if [[ $# == 1 && $1 == --help ]]; then usage; exit 0; fi
mode=${1:-}
version=${2:-}
case "$mode" in
  --baseline) [[ $# == 1 ]] || { usage >&2; exit 2; } ;;
  --saved) [[ $# == 2 && $version =~ ^(v3|v4|v5|v6|v7|v8|v9|v10|v11|v12|v13|v12-retry1|v13-retry1)$ ]] || { usage >&2; exit 2; } ;;
  --prepare-candidate|--execute-approved)
    [[ $# == 2 && $version =~ ^(v11|v12|v13|v12-retry1|v13-retry1)$ ]] || { printf '%s\n' 'REFUSED: select v11..v13 or exact v12-retry1/v13-retry1; archived v1..v10 cannot prepare or execute.' >&2; exit 2; } ;;
  *) printf '%s\n' 'REFUSED: explicit mode and candidate required. No inference performed.' >&2; usage >&2; exit 2 ;;
esac
cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.."
export PYTHONDONTWRITEBYTECODE=1 GIT_OPTIONAL_LOCKS=0
# checks.sh runs in a separate process, so shell exports alone cannot select it.
write_check_context() {
  python3 -B - "$1" "$2" <<'PYCONTEXT'
import json, sys
from pathlib import Path
Path('.auto/check-context.json').write_text(json.dumps({'mode':sys.argv[1], 'candidate':sys.argv[2]}) + '\n')
PYCONTEXT
}
if [[ $mode == --saved ]]; then
  python3 -B .auto/results.py --candidate "$version"
  write_check_context candidate "$version"
  exit 0
fi
if [[ $mode == --baseline ]]; then
bash -n .auto/measure.sh
python3 -B - <<'PY'
import ast
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import statistics
import sys
sys.path.insert(0, str(Path.cwd() / ".auto"))
import results, run_candidate

root = Path.cwd()
out = root / 'output/cscs'
scripts = ('run_prompt_v1.py', 'score_split5_date_balanced.py', 'baseline_noise.py',
           'baseline_noise4.py', 'official_rescore.py', 'score_prompt_v1.py',
           'analyze_v1_comparison.py')
for name in scripts:
    text = (out / name).read_text()
    ast.parse(text, filename=name)  # Parse only: do not import/execute.
    assert 'ROOT=Path(__file__).resolve().parents[2]' in text, 'NONLOCAL_ROOT'
ast.parse((root / 'evals/c-system-prompt/grader.py').read_text())
jobs = ('format-C-r1', 'format-C-r2', 'format-C-r3', 'format-C-r4.', 'format-C-r5')
for name in jobs:
    job = out / name
    assert json.loads((job / 'summary.json').read_text())['status'] == 'completed', name
    assert not any(p.name in {'STOP.json', 'inflight.json', 'state.pending'}
                   for p in job.rglob('*')), 'BASELINE_FENCE: ' + name
for name in ('official-rescore-evidence', 'hillclimb-split5-date-balanced-analysis'):
    assert not any(p.name in {'STOP.json', 'inflight.json', 'state.pending'}
                   for p in (out / name).rglob('*')), 'EVIDENCE_FENCE: ' + name
provenance = json.loads((out / 'preparation-provenance.json').read_text())
assert provenance['baseline_jobs'] == list(jobs)
assert len(provenance['pdf_mapping']) == 6
assert not (out / 'format-C-r4-start.txt').exists(), 'UNEXPECTED_R4_START'
for record in provenance['files']:
    path = root / record['local']
    assert path.resolve().is_relative_to(root) and not path.is_symlink(), 'NONLOCAL_COPY'
    assert hashlib.sha256(path.read_bytes()).hexdigest() == record['local_sha256'], 'COPY_CHANGED: ' + record['local']
    if path.name not in scripts:
        assert record['source_sha256'] == record['local_sha256'], 'SNAPSHOT_REWRITTEN'
for local in provenance['pdf_mapping'].values():
    assert (root / local).is_file() and (root / local).read_bytes()[:5] == b'%PDF-', 'MISSING_LOCAL_PDF'

repo = Path('/tmp/ost-official-evaluator-3U4yO9/repo')
python = Path('/tmp/ost-official-evaluator-3U4yO9/env/bin/python')
commit = '5e6957729b77a126006049305ad1ef241211a5b4'
assert repo.is_dir() and (repo / 'evaluate.py').is_file(), 'OFFICIAL_REPO_MISSING'
assert python.is_file() and os.access(python, os.X_OK), 'OFFICIAL_PYTHON_MISSING'
def git(*args):
    return subprocess.check_output(['git', '-C', str(repo), *args], text=True).strip()
assert git('rev-parse', 'HEAD') == commit, 'OFFICIAL_COMMIT_CHANGED'
assert not git('status', '--porcelain'), 'OFFICIAL_REPO_MODIFIED'
official = json.loads((out / 'official-rescore-evidence/provenance.json').read_text())
assert official['commit'] == commit
assert hashlib.sha256((repo / 'evaluate.py').read_bytes()).hexdigest() == official['evaluate_sha256'], 'OFFICIAL_EVALUATOR_CHANGED'
# Dependency presence only; do not import evaluate.py or invoke the grader.
subprocess.run([str(python), '-B', '-c',
                'import sklearn, rapidfuzz, numpy'], check=True,
               cwd=out, capture_output=True, text=True)
# Saved v5 only: verify the complete ledger/digests without grading or inference.
summaries = results.completed_jobs(out, 'v5')
results.usage.candidate_usage(out, 'v5', summaries,
                            results.load(root / 'evals/c-system-prompt/split.json'))
meta = results.load(root / 'evals/c-system-prompt/prompts/v5.json')
prompt = (root / 'evals/c-system-prompt/prompts/v5-system.txt').read_bytes()
assert run_candidate.digest(prompt) == meta['candidate_prompt_sha256'], 'BASELINE_PROMPT_CHANGED'
assert run_candidate.digest(run_candidate.system((root / 'track_2a/src/predict.py').read_text()).encode()) == meta['candidate_prompt_sha256'], 'ADOPTED_SYSTEM_CHANGED'
for repeat in range(1, 6):
    manifest = results.load(out / f'prompt-C-v5-r{repeat}/manifest.json')
    provenance_v5 = results.load(out / f'prompt-C-v5-r{repeat}-provenance.json')
    assert provenance_v5['prompt_sha256'] == meta['candidate_prompt_sha256'], 'BASELINE_PROVENANCE_CHANGED'
    for frozen in manifest['frozen']:
        assert frozen['messages'][0]['content'] == prompt.decode() + '\n\n' + manifest['protocol_reminder'], 'BASELINE_SYSTEM_CHANGED'
        assert results.usage.digest(frozen['messages']) == frozen['messages_sha256'], 'BASELINE_MESSAGES_CHANGED'
    for source, sha in manifest['sources'].items():
        path = Path(source) if Path(source).is_absolute() else Path(provenance_v5['workspace']) / source
        assert run_candidate.digest(path.read_bytes()) == sha, 'BASELINE_SOURCE_CHANGED'
        if source.endswith('track_2a/src/predict.py'):
            assert run_candidate.digest(run_candidate.system(path.read_text()).encode()) == meta['candidate_prompt_sha256'], 'BASELINE_SOURCE_SYSTEM_CHANGED'
aggregate = results.load(out / 'hillclimb-v5-analysis/aggregate.json')
for part, count in (('train', 36), ('test', 18)):
    side = aggregate[part]
    assert side['cases'] == count and [r['repeat'] for r in side['repeats']] == list(range(1, 6)), 'INCOMPLETE_AGGREGATE'
    assert math.isfinite(side['Q_mean']) and side['Q_mean'] == statistics.mean(r['Q'] for r in side['repeats']), 'INVALID_BASELINE_METRIC'
print('Offline saved v5 baseline verified. No runner, grader, model or API execution.')
results.baseline_metrics(aggregate)
print('METRIC min_Q_gain_v5=0')
PY
write_check_context baseline ''
fi
case "$mode" in
  --prepare-candidate)
    /tmp/hackapertus-ost-contract/.venv/bin/python -B .auto/run_candidate.py --candidate "$version" --prepare-only
    ;;
  --execute-approved)
    /tmp/hackapertus-ost-contract/.venv/bin/python -B .auto/run_candidate.py --candidate "$version" --execute-approved
    /tmp/ost-official-evaluator-3U4yO9/env/bin/python -B .auto/score_candidate.py --candidate "$version"
    /tmp/ost-official-evaluator-3U4yO9/env/bin/python -B .auto/compare_candidate.py --candidate "$version"
    # Completed quality rejections belong to checks.sh (checks_failed), not execution errors.
    python3 -B .auto/results.py --candidate "$version"
    write_check_context candidate "$version"
    printf '%s\n' 'STOP: candidate finished. No automatic adoption or production change.'
    ;;
esac
