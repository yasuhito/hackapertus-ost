# Approved one-candidate Task A/B SYSTEM-order round: v16

User explicitly approved Task A/B-specific instruction order, one candidate,
TRAIN36 cases x5 repeats x1 config, fixed scoring, stop before final validation.

## Frozen hypothesis and implementation

Task A uses unchanged v15 SYSTEM SHA b2027887d2c9de4507d2ee8b2cb231cae3d4b63a6b55e353bfe3fcef80d9f6c3.
Task B uses unchanged v5 SYSTEM SHA 06c89db1756d54d04cc5f1650b855acda2e2986d4c0c84943d2e54866383313c.
Only existing structured input type booklet/reference and its derived taskA/B
select the order. No case IDs, claims, source dates, labels, gold, examples or
TEST feedback select prompts. This TRAIN-adaptive hypothesis uses observed v15
A improvement/B regression and independently meaningful document/reference
input differences; it is not unseen-performance evidence or an independent
post-selection confirmation.

v16-system.txt is a canonical JSON artifact containing the two SYSTEM strings,
SHA d61868e705aacb3fc69e09485ce9b0f215d3f90a672605638380fecf8aa25ec0.
Models never receive that JSON bundle. A small wrapper in isolated copied
predict.py replaces messages[0].content with the exact selected string; all
messages[1:], pages, IDs, schema/reminder/rolemodel/caps/temp stay unchanged.
Adopted application predict.py remains v5. No parent/child/tool restructuring.

Freeze control output/cscs/train-route-protocol.json SHA
e9c38425ff68adeb45e124da921306cc95f3e5fe8ea1546593acf37897396bbb
pins bundle/source artifacts, wrapper and generated source, controls, runtime,
evaluator, split, reference records and PDFs before all trials. Historical
v14/v15 controls are preserved unchanged; replay those from their own code
checkpoint, not this revised control code. Never overwrite/de-fence old jobs.

## Target and setup

Same train_Q_gain_v5 target/workload as preceding TRAIN round, higher better;
do NOT initialize again. Saved reference trainQ.8275862068965517, F1A.666667,
B1, HitA.50. Read-only reference checkpoint may use historical known TRAIN
usage metrics, but TRAIN-only command duration was never measured for saved54
jobs: mark it unavailable, not a measured zero. No baseline inference/grading.

Canonical run_experiment commands:
- bash .auto/measure.sh --route-baseline, timeout180/checks180; log0 keep as
  read-only source/control checkpoint, not a new prompt inference.
- bash .auto/measure.sh --route-execute-approved v16 --attempt 1,
  timeout7200/checks_timeout180; always log the completed experiment cycle.

New approved window start2026-10-14T16:04:15+09:00, candidate/attempt cutoff
17:34:15 (+90min), softfinish18:04:15 (+120min), Asia/Tokyo. No autonomous
extension. Finish already-started five-repeat batches. Startup and first POST
gate the actual clock. Current maxIterations7 covers prior3 records plus this
reference checkpoint and at most3 v16 attempts; unused slots do not authorize
other candidates.

## Same acceptance and transport rules

Primary gain>=.02 AND >conservative TRAIN noise.017051043674621427; eachrepeat
F1A>=.60/B>=.75; canonical36/36/fallback0; meanHitA>=.50. Strict gain>=noise+.02
is supplementary. Same original official evaluator, references, sourcegroups,
20k bootstrap/seed20261016. No TEST grading/individual outputs/protectedholdout.
Evidence surrogate is at frozen attainable TRAIN ceiling6/12, so preservation
is not an evidence improvement. Report all secondary regressions/usage/latency.

Previously approved operational504 policy remains: only incomplete HTTP504,
wait60sec then fresh entire36x5batch attempt2/3 (maximum2 additional), exactsame
artifacts/conditions, no prefix reuse or fence deletion. Log each crash and
unknown failed-request usage, link retries using ASI.revisits_run. Other errors,
orphanstates, exhausted retries or cutoff stop. No completed quality retry or
favorable repeat selection. Failed attempts are excluded from successful-batch
usage; those metrics are not total session cost. Repair-window usage is subset,
not additive role or proof of decoded schema-repair reason.

## Logging and completion

Record parsed primary and all tracked secondaries. Historical reference import
must label historical candidate-named values as reference observations, not new
candidate measurements; unknown command duration uses an explicit unavailable
sentinel if the numeric logger requires it. On incomplete crashes, numeric
sentinels are unavailable values, never zero measured usage/quality.

Completed gain/validity/F1/evidence gate failure =>checks_failed. Checks passing
and primary improves retained TRAIN best =>keep for research only; otherwise
discard. Keep NEVER edits adopted app or means final validation/adoption.

Stop after the one candidate completes, even if it improves. No final validation,
new hypothesis, sibling modification, push or deployment. A genuinely unused,
independently labeled validation set needs owner-provided provenance/separate
preparation approval before any later confirmation. `.auto/ideas.md` stores
only deferred directions, not permissions.

Offline route/controls suite64 passed under pinned runtime; relevant combined
suite168passed/2skipped, syntax/ShellCheck/diffcheck pass. Reviewer found no
routing defects. Its unpinned SDK tests failed; rerunning with required Pi1.1.0
and child0.19.0 roots passed both realSDK mocks. Offline five-workspace36case
preparation passed exact per-task SYSTEM/input/pages/IDs/schema/source audits
with zero model calls, credentials or jobs. No new inference yet.
