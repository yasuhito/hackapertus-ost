# TRAIN-only prompt comparison: v14 and v15 from adopted v5

## Approved scope and frozen protocol

User activated autoresearch and approved `.auto/next-round-plan.md`, including
HTTP504-only retries: wait60 seconds, fresh entire-batch attempt ID, at most two
additional attempts per candidate. Two independent candidates v14/v15, each
36 frozen TRAIN cases x5 repeats x1 configuration. No TEST scoring/individual
output inspection, competition holdout, final validation, adoption, push or
sibling changes. Stop before final validation even if a candidate improves.

Start2026-10-14T14:14:17+09:00, candidate/attempt cutoff15:44:17 (+90min),
soft finish16:14:17 (+120min), Asia/Tokyo. `.auto/train-window.json` and the
first actual POST enforce the cutoff. Finish already-started five-repeat batches.
Seven segment records maximum: one read-only reference import plus at most six
candidate execution attempts. Never extend time/counts autonomously.

Frozen control `output/cscs/train-protocol.json` SHA256:
3f3f98aa898f21d01b5db0ca56508632d6e1c6fad017e4c5133b1bb27102b9af.
Both candidate texts/artifacts, runner/control/source/runtime/split/reference
and PDF hashes are immutable before trials. Freeze was performed after offline
review and pending-check-selector repair, before any new model request.

## Measurement and commands

NEW workload/target train_Q_gain_v5, higher better: candidate five-repeat TRAIN
mean Q minus SAVED v5 TRAIN Q0.8275862068965517. Initialize once for this changed
TRAIN-only workload; preserve historical log/config headers. Do not initialize
again in this segment. Baseline verification imports saved results only, no
model rerun or new baseline grading. Reference import keep establishes the
approved source/control checkpoint required before candidate execution.

Use run_experiment direct commands:
- `bash .auto/measure.sh --train-baseline`, timeout180/checks180; log0 keep as
  saved-reference import, not new inference.
- `bash .auto/measure.sh --train-execute-approved v14 --attempt 1`, timeout7200,
  checks_timeout180, then v15 attempt1 if v14 completes, regardless of quality
  rejection. Offline preparation of both candidates has passed.
- After HTTP504 only and incomplete batch, log crash, then use attempt2/3 for
  the SAME candidate, with unchanged artifacts. Startup/firstPOST enforce60sec
  since prior failure. Never reuse jobs/prefixes or selectively retain repeats.

Gain>=.02 AND >conservative TRAIN noise.017051043674621427, each repeat
F1A>=.60/F1B>=.75, canonical validity36/36/fallback0, and TRAIN HitA>=.50 are
mandatory. Strict gain>=noise+.02 is supplementary, not a replacement gate.
Preserve original official scorer, source groups, 20k bootstrap/seed20261016,
labels, references, extraction/restoration/tools/model roles70Bparent/actual8B
child/thinkingoff and per-case request/communication limits. Only research
case selection/count handling changed; default54 behavior is preserved and
candidate per-case inputs/pages/IDs match saved v5 TRAIN except SYSTEM.

## Candidate hypotheses and provenance

v14 SHA6d902f5e75e06484c5082fa6d46086cda835364aaab8bb707bc36872010be194:
Add explicit classification-before-citation selection order. Missing decisive
anchors in verified TRAIN calls motivate an order experiment; they do not prove
hidden reasoning or permit gold/case-specific instructions. Distinct from v9's
selected-evidence context caution and v1's final verification append.

v15 SHAb2027887d2c9de4507d2ee8b2cb231cae3d4b63a6b55e353bfe3fcef80d9f6c3:
Move existing semantic safeguards before unchanged submit/citation instructions.
Every original instruction line and whole guard retained verbatim; no shortening
or added text. Offline Counter/block-preservation assertions passed. Independent
v5 base, no v14 policy. Both candidates have no examples and overlap checks.

Adopted v5 SYSTEM hash remains06c89db1756d54d04cc5f1650b855acda2e2986d4c0c84943d2e54866383313c.
`.auto/v5-training-diagnosis.md` records six stable TRAIN Task A label failures,
no B failures, and evidence-surrogate ceiling6/12 independently verified using
actual restoration and official matching. No classification/evidence-gain claim
may be inferred merely from fewer formatting repairs or stable source validity.

## Logging, retries and stopping

Always log every run_experiment and EVERY tracked secondary metric. Record ASI
hypothesis/version/hash/attempt/control digest, observations limited to TRAIN,
and rollback_reason/next_action_hint on rejection/crash. Completed quality-gate
failure =>checks_failed, never transport retry. With checks passing, keep only
primary improvement over retained TRAIN best; unchanged/worse=>discard. Keep is
research retention, not production adoption or evidence of unseen performance.

HTTP504-only incomplete execution=>crash with preserved attempt record/STOP/
inflight and documented unavailable numeric crash sentinels if required by
logger. At most attempts1,2,3, each starts full36x5; wait60sec after failedend.
Include ASI.revisits_run linking a transport retry to its earlier crashed tool
record and state only authorization/new execution attempt changed, not prompt.
Any other API/transport/unknown-usage/error, orphan state, scoring error, exhausted
504 attempts or cutoff stops the round. No gate/validator weakening or fence
removal. Failed-request usage remains unknown; complete-batch metrics exclude
previous failed attempts and are not total session cost. Repair-window usage is
a positional subset of parent/child, not an additive third role or decoded
payload diagnosis.

Stop after both candidates complete. Select from TRAIN only; final verification
requires separately frozen genuinely unused independently labeled data and
owner input/authorization. Existing internal TEST is exposed, not unseen.

## Offline validation

Initial combined relevant suite245 passed/3 skipped; subsequent TRAIN suite31
passed including pending selector rejection. ShellCheck/syntax/diff checks pass.
Reviewer found no critical/high/medium defects; inherited stale selector risk
was repaired before freeze. Five isolated source-only preflight workspaces per
candidate pass TRAIN inputs/pages/IDs/schema/source parity with zero requests.
The experiment tool requires `.auto/measure.sh`; its TRAIN dispatch was added
before reference import after a no-execution tool refusal. It delegates to the
already-frozen train_measure.sh without changing its controls or model inputs.
See `.auto/train-protocol.md` for commands/control metadata and independent
`.auto/next-round-plan.md` for final-validation boundary. Deferred ideas go to
`.auto/ideas.md`; do not replay exhausted v1..v13/retry policies.
