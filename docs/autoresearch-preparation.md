# C SYSTEM experiment-tool integration

Read `.auto/prompt.md` for the current owner-approved execution scope and
`.auto/window.json` for its machine-readable time limit. `.auto/log.jsonl`
retains the initialized target and actual tool results. Do not reset or delete
that history. Primary min_Q_gain is the minimum train/test five-repeat mean Q
gain over fixed v0, higher better; historical baseline0 is already recorded.

## Overnight owner override

The owner approved up to six additional candidates v5..v10, ten total, with
fixed54 x5 x1 trials each and autonomous per-candidate execution in this window.
The owner rescheduled on October14 morning: no new candidates start at/after
2026-10-14T11:00:00+09:00, Asia/Tokyo; completion target2026-10-14T12:00:00+09:00
is soft for an already-started batch. No forced
in-flight request termination. Config maxIterations8 includes the two existing
tool records and six possible new ones. Reload Pi after changing that limit
because the extension caches it; activate autoresearch before tool execution.

This overrides only the earlier five-candidate cap and candidate-by-candidate
approval, not the frozen protocol in evals/c-system-prompt/README.md and
docs/prompt-eval-log.md. All other scoring/split/noise/F1/evidence requirements
remain. Individual logs inspected for design must be verified train cases;
test is machine-scored aggregate acceptance only, never a design target. The
exposed internal dev split is not an unseen holdout. Local estimated-reference
Hit@5 is not the official overall score.

Experiment-branch automatic commits/rollback are approved. Production adoption
and push are not. Completed quality rejection is logged and another distinct
candidate may proceed while time/slots remain. Actual API/execution/usage/STOP
errors terminate the entire loop, without retry, next candidate or fence clearing.

## Commands and isolation

Use run_experiment with direct `bash .auto/measure.sh --execute-approved v5`
(or the next approved version), timeout7200/checks_timeout180, then always
log_experiment the actual outcome and all previously tracked metrics/ASI.
No shell-export prefix is accepted by the tool. Baseline/v3/v4 are never rerun.
Saved reports can be read with `bash .auto/measure.sh --saved v4`.
Offline preparation uses `bash .auto/measure.sh --prepare-candidate v5`.

Future execution/preparation is limited to v5..v10; archived versions refuse.
Metadata must match candidate/54x5x1 scope and authorized window. The runner
checks time before preflight and immediately before the first API request, not
between the five repeats. Existing paths/fences refuse replay. Source-only
isolated copies and six local independent PDFs preserve user inputs/pages/IDs;
only predict.py SYSTEM differs, never FINAL_VERIFICATION/models/tools/transport.
Candidate artifacts are copied byte-exact to ignored candidate-archive before
execution; later hash checks can use these after tool rollback removes drafts.
Archive changes are refused, not overwritten. No new grader is introduced.

results.py emits both split metrics plus usage. checks.sh enforces independent
split gains/noise, per-repeat F1/validity using successful check-context.json.
usage.py verifies saved record/manifest digests, known/valid HTTP usage and
ledger counters. Parent/child and train/test input/output/total usage reconcile
with aggregate totals. Repair-window (parent request>=2 or child>=1) is a subset,
not a third additive role or decoded-payload schema-repair proof.

## Existing evidence and outcomes

Checkpoint409d39f saves preparation, v3 and draft v4. Tool run1 is saved baseline
only, not new inference. Run2 is v4 checks_failed and automatic rollback, with
raw completed jobs preserved. v4 completed54x5, validity54/54/fallback0 each,
815 requests,5,433,529 tokens. Train Q0.7436165367199852 (gain-.004683439166197734);
test Q0.7017241379310346 (gain-.11379310344827587), test B F1.65 fails every repeat.
Local Hit train+.05/test unchanged cannot override regression. v4 is rejected.
Its parent-ownership policy was based on eight verified train executions with
identical child/parent submissions; that does not prove absent internal review.
v3 was also rejected; see its saved aggregate. v2 remains independent/unknown.

Ignored output/cscs contains completed byte-preserved v0 format-C-r1/r2/r3/r4./r5,
seven ROOT-adapted historical scripts, official scoring/baseline aggregates,
per-candidate raw jobs and provenance. Six PDFs are independent booklets/ copies.
Original manifests remain unchanged; missing r4 start is never reconstructed.
Original sibling/external dependencies are read-only. Never open protected
holdout or individual test outputs/transcripts. Older failure-inspection noise
scripts must not run under this policy.

## Validation

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest discover -s .auto -p 'test_*.py'
PYTHONDONTWRITEBYTECODE=1 /tmp/ost-official-evaluator-3U4yO9/env/bin/python -B .auto/test_scoring.py
bash -n .auto/measure.sh .auto/checks.sh
```

Synthetic tests cover time cutoff/timezone/rollover/cap, archive fallback/digest
integrity, scoped approvals, fences, quality gates and token reconciliation.
Official replay expects zero gain/no adoption using historical v0 predictions
in a disposable directory; it is not a new candidate evaluation. Overnight
v5..v10 inference has not run yet.

The official evaluator remains read-only at /tmp/ost-official-evaluator-3U4yO9/repo,
commit5e6957729b77a126006049305ad1ef241211a5b4, interpreter
/tmp/ost-official-evaluator-3U4yO9/env/bin/python. Leave dependencies unchanged,
verify pin/integrity, and keep subprocess bytecode writing disabled.
