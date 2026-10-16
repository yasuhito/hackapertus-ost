#!/usr/bin/env bash
# No candidate selection or approval is inferred from historical results.
set -euo pipefail
# The experiment tool requires this canonical entry point; TRAIN controls stay separate.
case "${1:-}" in
# BEGIN span-retrieval-v1 additive
  --span-retrieval-prepare|--span-retrieval-candidate)
    [[ $# == 1 ]] || exit 2
    case "$1" in
      --span-retrieval-prepare) phase=--prepare-only ;;
      --span-retrieval-candidate) phase=--candidate ;;
    esac
    exec /tmp/hackapertus-ost-contract/.venv/bin/python -B -Werror::ResourceWarning "$(dirname -- "${BASH_SOURCE[0]}")/span_retrieval_research.py" "$phase" ;;
# END span-retrieval-v1 additive
# BEGIN evidence-only-v1 additive
  --evidence-only-prepare|--evidence-only-candidate)
    [[ $# == 1 ]] || exit 2
    case "$1" in
      --evidence-only-prepare) phase=--prepare-only ;;
      --evidence-only-candidate) phase=--candidate ;;
    esac
    exec /tmp/hackapertus-ost-contract/.venv/bin/python -B -Werror::ResourceWarning "$(dirname -- "${BASH_SOURCE[0]}")/evidence_only_research.py" "$phase" ;;
# END evidence-only-v1 additive
# BEGIN bound-review-v1 additive
  --bound-review-prepare|--bound-review-candidate)
    [[ $# == 1 ]] || exit 2
    case "$1" in
      --bound-review-prepare) phase=--prepare-only ;;
      --bound-review-candidate) phase=--candidate ;;
    esac
    exec /tmp/hackapertus-ost-contract/.venv/bin/python -B -Werror::ResourceWarning "$(dirname -- "${BASH_SOURCE[0]}")/bound_review_research.py" "$phase" ;;
# END bound-review-v1 additive
# BEGIN fragment-review-v1 additive
  --fragment-review-prepare|--fragment-review-candidate)
    [[ $# == 1 ]] || exit 2
    case "$1" in
      --fragment-review-prepare) phase=--prepare-only ;;
      --fragment-review-candidate) phase=--candidate ;;
    esac
    exec /tmp/hackapertus-ost-contract/.venv/bin/python -B -Werror::ResourceWarning "$(dirname -- "${BASH_SOURCE[0]}")/fragment_review_research.py" "$phase" ;;
# END fragment-review-v1 additive
  --role-review-prepare|--role-review-baseline|--role-review-candidate)
    [[ $# == 1 ]] || exit 2
    case "$1" in
      --role-review-prepare) phase=--prepare-only ;;
      --role-review-baseline) phase=--baseline ;;
      --role-review-candidate) phase=--candidate ;;
    esac
    exec /tmp/hackapertus-ost-contract/.venv/bin/python -B -Werror::ResourceWarning "$(dirname -- "${BASH_SOURCE[0]}")/role_review_research.py" "$phase" ;;
  --fullbranch-prepare|--fullbranch-reference|--fullbranch-execute)
    [[ $# == 1 ]] || exit 2
    case "$1" in
      --fullbranch-prepare) phase=--prepare-only ;;
      --fullbranch-reference) phase=--reference ;;
      --fullbranch-execute) phase=--candidate ;;
    esac
    exec /tmp/hackapertus-ost-contract/.venv/bin/python -B -Werror::ResourceWarning "$(dirname -- "${BASH_SOURCE[0]}")/fullbranch_public60.py" "$phase" --approved-at "$(date +%s)" ;;
  --provider-schema-edge-prepare)
    [[ $# == 1 ]] || exit 2
    exec /tmp/hackapertus-ost-contract/.venv/bin/python -B "$(dirname -- "${BASH_SOURCE[0]}")/provider_schema_edge_probe.py" --prepare ;;
  --provider-schema-edge)
    [[ $# == 1 ]] || exit 2
    exec /tmp/hackapertus-ost-contract/.venv/bin/python -B "$(dirname -- "${BASH_SOURCE[0]}")/provider_schema_edge_probe.py" --execute ;;
  --provider-schema-empty-prepare)
    [[ $# == 1 ]] || exit 2
    exec /tmp/hackapertus-ost-contract/.venv/bin/python -B "$(dirname -- "${BASH_SOURCE[0]}")/provider_schema_empty_source.py" --prepare ;;
  --provider-schema-empty)
    [[ $# == 1 ]] || exit 2
    exec /tmp/hackapertus-ost-contract/.venv/bin/python -B "$(dirname -- "${BASH_SOURCE[0]}")/provider_schema_empty_source.py" --execute ;;
  --provider-schema-empty-retry-prepare)
    [[ $# == 1 ]] || exit 2
    exec /tmp/hackapertus-ost-contract/.venv/bin/python -B "$(dirname -- "${BASH_SOURCE[0]}")/provider_schema_empty_retry.py" --prepare ;;
  --provider-schema-empty-retry)
    [[ $# == 1 ]] || exit 2
    exec /tmp/hackapertus-ost-contract/.venv/bin/python -B "$(dirname -- "${BASH_SOURCE[0]}")/provider_schema_empty_retry.py" --execute ;;
  --provider-schema-unique-prepare)
    [[ $# == 1 ]] || exit 2
    exec /tmp/hackapertus-ost-contract/.venv/bin/python -B "$(dirname -- "${BASH_SOURCE[0]}")/provider_schema_unique_ids.py" --prepare ;;
  --provider-schema-unique-baseline)
    [[ $# == 1 ]] || exit 2
    exec /tmp/hackapertus-ost-contract/.venv/bin/python -B "$(dirname -- "${BASH_SOURCE[0]}")/provider_schema_unique_ids.py" --baseline ;;
  --provider-schema-unique-candidate)
    [[ $# == 1 ]] || exit 2
    exec /tmp/hackapertus-ost-contract/.venv/bin/python -B "$(dirname -- "${BASH_SOURCE[0]}")/provider_schema_unique_ids.py" --candidate ;;
  --provider-schema-branch-closure-prepare)
    [[ $# == 1 ]] || exit 2
    exec /tmp/hackapertus-ost-contract/.venv/bin/python -B "$(dirname -- "${BASH_SOURCE[0]}")/provider_schema_branch_closure.py" --prepare ;;
  --provider-schema-branch-closure)
    [[ $# == 1 ]] || exit 2
    exec /tmp/hackapertus-ost-contract/.venv/bin/python -B "$(dirname -- "${BASH_SOURCE[0]}")/provider_schema_branch_closure.py" --execute ;;
  --provider-schema-probe-report)
    [[ $# == 1 ]] || exit 2
    exec /tmp/hackapertus-ost-contract/.venv/bin/python -B "$(dirname -- "${BASH_SOURCE[0]}")/provider_schema_probe_recovery.py" --execute-report ;;
  --provider-schema-probe-prepare)
    [[ $# == 1 ]] || exit 2
    exec /tmp/hackapertus-ost-contract/.venv/bin/python -B "$(dirname -- "${BASH_SOURCE[0]}")/provider_schema_probe.py" --prepare ;;
  --provider-schema-probe)
    [[ $# == 1 ]] || exit 2
    exec /tmp/hackapertus-ost-contract/.venv/bin/python -B "$(dirname -- "${BASH_SOURCE[0]}")/provider_schema_probe.py" --execute ;;
  --feedback-h2-g2-prepare)
    [[ $# == 1 ]] || exit 2
    exec /tmp/hackapertus-ost-contract/.venv/bin/python -B "$(dirname -- "${BASH_SOURCE[0]}")/feedback_research_h2_g2.py" --prepare-only ;;
  --feedback-execute)
    if [[ $# == 2 && $2 == h2-g2 ]]; then
      exec /tmp/hackapertus-ost-contract/.venv/bin/python -B "$(dirname -- "${BASH_SOURCE[0]}")/feedback_research_h2_g2.py" --candidate --approved-at "$(date +%s)"
    fi
    ;;&
  --feedback-h2-prepare)
    [[ $# == 1 ]] || exit 2
    exec /tmp/hackapertus-ost-contract/.venv/bin/python -B "$(dirname -- "${BASH_SOURCE[0]}")/feedback_research_h2.py" --prepare-only ;;
  --feedback-execute)
    if [[ $# == 2 && $2 == h2 ]]; then
      exec /tmp/hackapertus-ost-contract/.venv/bin/python -B "$(dirname -- "${BASH_SOURCE[0]}")/feedback_research_h2.py" --candidate --approved-at "$(date +%s)"
    fi
    ;;&
  --feedback-prepare|--feedback-reference|--feedback-execute)
    mode=$1
    if [[ $mode == --feedback-execute ]]; then
      [[ $# == 2 && $2 == h1 ]] || exit 2
      phase=--candidate
    else
      [[ $# == 1 ]] || exit 2
      if [[ $mode == --feedback-prepare ]]; then phase=--prepare-only; else phase=--reference; fi
    fi
    exec /tmp/hackapertus-ost-contract/.venv/bin/python -B "$(dirname -- "${BASH_SOURCE[0]}")/feedback_research.py" "$phase" --approved-at "$(date +%s)" ;;
  --public-continue-baseline|--public-continue-candidate)
    mode=$1
    if [[ $mode == --public-continue-baseline ]]; then
      [[ $# == 1 ]] || exit 2
      phase=--baseline-continue
    else
      [[ $# == 2 && $2 == v16 ]] || exit 2
      phase=--candidate
    fi
    exec /tmp/hackapertus-ost-contract/.venv/bin/python -B "$(dirname -- "${BASH_SOURCE[0]}")/public_validation_continue.py" "$phase" --approved-at "$(date +%s)" ;;
  --public-continue-prepare)
    [[ $# == 1 ]] || exit 2
    exec /tmp/hackapertus-ost-contract/.venv/bin/python -B "$(dirname -- "${BASH_SOURCE[0]}")/public_validation_continue.py" --prepare-only ;;
  --public-baseline|--public-candidate)
    mode=$1
    if [[ $mode == --public-baseline ]]; then
      [[ $# == 1 ]] || exit 2
      phase=--baseline
    else
      [[ $# == 2 && $2 == v16 ]] || exit 2
      phase=--candidate
    fi
    exec /tmp/hackapertus-ost-contract/.venv/bin/python -B "$(dirname -- "${BASH_SOURCE[0]}")/public_validation.py" "$phase" --approved-at "$(date +%s)" ;;
  --public-preflight)
    [[ $# == 1 ]] || exit 2
    /tmp/hackapertus-ost-contract/.venv/bin/python -B "$(dirname -- "${BASH_SOURCE[0]}")/public_validation.py" --prepare-only
    # Readiness alone is never a measured PUBLIC60 baseline or gain.
    printf '%s\n' 'PUBLIC_PREFLIGHT_ONLY: no quality measurement; live adapter required.' >&2
    exit 1 ;;
  --route-baseline)
    [[ $# == 1 ]] || exit 2
    export TRAIN_ROUND=v16
    exec bash "$(dirname -- "${BASH_SOURCE[0]}")/train_measure.sh" --baseline ;;
  --route-prepare-candidate)
    [[ $# == 2 && $2 == v16 ]] || exit 2
    export TRAIN_ROUND=v16
    exec bash "$(dirname -- "${BASH_SOURCE[0]}")/train_measure.sh" --prepare-candidate "$2" ;;
  --route-execute-approved)
    [[ $# == 4 && $2 == v16 ]] || exit 2
    export TRAIN_ROUND=v16
    exec bash "$(dirname -- "${BASH_SOURCE[0]}")/train_measure.sh" --execute-approved "$2" "$3" "$4" ;;
  --train-baseline)
    export TRAIN_ROUND=
    [[ $# == 1 ]] || exit 2
    exec bash "$(dirname -- "${BASH_SOURCE[0]}")/train_measure.sh" --baseline ;;
  --train-prepare-candidate)
    export TRAIN_ROUND=
    [[ $# == 2 ]] || exit 2
    exec bash "$(dirname -- "${BASH_SOURCE[0]}")/train_measure.sh" --prepare-candidate "$2" ;;
  --train-execute-approved)
    export TRAIN_ROUND=
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
