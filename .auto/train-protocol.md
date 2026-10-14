# Bounded TRAIN36x5 wiring

This is research only. No TEST scoring, final validation or adoption is wired here.
Historical `measure.sh`, `results.py` and candidate scopes remain separate.

## Owner freeze, before any preparation

1. Finish both independent v5-based v14/v15 artifacts in `evals/c-system-prompt/prompts/`: `.json`, `-system.txt`, `-added.txt`, `.patch`, `-overlap.json`. Metadata must have exact `version`, `proposed_trials` and `approved_trials` `{cases:36,repeats:5,configs:1}`, `inference_approved:true`, `approval_scope:{candidate:"v14",cases:36,repeats:5,configs:1}` (v15 respectively), baseline SYSTEM SHA256 `06c89db1756d54d04cc5f1650b855acda2e2986d4c0c84943d2e54866383313c`, and exact candidate SYSTEM hash. No approval is inherited.
2. Create the approved `.auto/train-window.json` with the exact owner-specified 2026-10-14 Tokyo timestamps, 90/120 minute intervals, candidates v14/v15, TRAIN trials36/5/1, three attempts, HTTP504-only retry and 60-second wait.
3. Run `python3 -B .auto/train_run.py --freeze-protocol` once. This archives both candidates and exclusively creates ignored `output/cscs/train-protocol.json`. It pins selection runner, controls, split, PDFs, TRAIN references/individual ledger records, source files and installed runtime fingerprints. Record its SHA256 in the experiment configuration before reference import. Do not modify it or candidate artifacts after freezing.
4. Offline preparation may use the approved working-tree runner before a HEAD checkpoint. Execution additionally requires every frozen `track_2a/` and `.auto/` code file to byte-match HEAD. The owner must create that checkpoint; this implementation never commits. A changed control/source/runtime after reference import is refused by check context or attempt provenance.

## Direct commands

```sh
bash .auto/train_measure.sh --baseline
bash .auto/train_measure.sh --prepare-candidate v14
bash .auto/train_measure.sh --prepare-candidate v15
# Only after the owner checkpoint and inside the approved start window:
bash .auto/train_measure.sh --execute-approved v14 --attempt 1
bash .auto/checks.sh
# Then v15, even if completed v14 failed quality, but never after execution STOP:
bash .auto/train_measure.sh --execute-approved v15 --attempt 1
bash .auto/checks.sh
```

No inference was authorized or performed by implementing these commands. Baseline is read-only and does not invoke a scorer. Preparation creates five disposable isolated source/PDF/input-ID workspaces, no designated jobs, credentials or scoring fixtures. Only SYSTEM differs from saved v5 TRAIN inputs. Generic research runner `--case-ids-file` accepts a gold-free JSON list; approved TRAIN orchestration does not expose arbitrary selection and requires the frozen split.

An explicit attempt2/3 is allowed only after the immediately preceding incomplete entire-batch HTTP504 STOP. All five repeats restart at new deterministic `prompt-C-v14-a2-r1` through `r5` paths, never at old prefixes. Prior artifacts remain intact. The startup gate waits until failure end plus60 seconds. A gold-free shim gates the first actual POST against actual UTC and the same wait; later repeats of an already-started batch are not halted at cutoff. Any existing current/future job or attempt sidecar refuses execution. Unknown errors, orphan inflight attempts, exhausted retries and grading errors stop the round. A completed quality failure is not an execution error, returns measurement exit0, then fails checks; it cannot retry. v15 waits for completed v14 grading/reporting, not merely five summaries.

## Metrics and checks

Primary: `train_Q_gain_v5`, baseline0, candidate TRAIN Q minus saved v5 TRAIN Q0.8275862068965517. Other scalar metrics:

- `baseline_train_Q`, `baseline_train_F1_A`, `baseline_train_F1_B`, `baseline_train_Hit_A`, `train_noise`
- `candidate_train_Q`, `candidate_train_F1_A`, `candidate_train_F1_B`, `candidate_train_Hit_A`
- `train_F1_A_delta`, `train_F1_B_delta`, `train_Hit_A_delta`
- `candidate_train_{parent,child,repair_window}_{input_tokens,output_tokens,total_tokens,calls,API_wait_seconds}`
- `candidate_train_command_seconds`, `candidate_train_API_wait_seconds`

Baseline emits only its applicable saved-reference metrics, not invented candidate costs. Crashes emit no measured quality or primary metric. If the outer logger requires every tracked metric on crashes, its owner must configure documented crash sentinels outside measured quality. Failed attempts remain separate with unknown failed-request usage. Completed-batch tokens are not total session cost. Repair-window totals are a positional subset of parent/child calls, not a third role or proof of a schema repair.

The local gates are gain>=.02 and gain>max(saved v5 TRAIN temporal noise,0.017051043674621427), per-repeat F1A>=.60/F1B>=.75, 36 valid canonical outputs and zero fallbacks each repeat, mean TRAIN evidence Hit>=.50. Strict gain>=noise+.02 is supplemental only. Grouped paired nonlinear F1 bootstrap uses all five repeats, original TRAIN source groups, 20,000 draws and seed20261016. Original official scorer, split, expectations and references are unmodified. Hit is a reference surrogate already at frozen ceiling6/12; there is no evidence-improvement claim.

`train_results.py --candidate v14 --attempt 1 --check` is read-only, recomputes aggregate comparisons from saved TRAIN scores and validates selected individual request/response ledger digests, source/message/schema bindings, model/role identities, SDK counts, successful usage and end states. Original request payload bytes are not retained by the historical ledger; their recorded digests are validated within hashed records, not falsely reconstructed. Check context pins mode `train_baseline` or `train_candidate`, candidate/attempt and control digest. Old check selectors are unchanged.

## Offline tests

```sh
PI_PACKAGE_ROOT=/home/yasuhito/.pi/agent/install/releases/1.1.0/node_modules/@earendil-works/pi-coding-agent \
PI_SUBAGENTS_ROOT=/home/yasuhito/.pi/agent/npm/node_modules/@tintinweb/pi-subagents \
PYTHONPATH=/usr/lib/python3.14/site-packages \
/tmp/hackapertus-ost-contract/.venv/bin/python -B -m pytest -q \
  track_2a/dev/format .auto/test_controls.py .auto/test_retries.py .auto/test_usage.py .auto/test_train.py
```

The explicit runtime roots are required by existing synthetic SDK tests. NumPy is available in system/official-evaluator Python, not the contract venv. No dependencies are installed. The new tests include real offline CLI prepare36 and saved-v5 frozen input/page/ID parity, but do not grade the saved baseline. The old standalone `.auto/test_scoring.py` replay is intentionally not run because it opens combined54/TEST outputs.
