# C SYSTEM autoresearch: v5 reference, v11..v13

## Current authorization and clock

The user approved this NEW target segment: improve the locally adopted v5,
not the historical v0. Existing records stay in .auto/log.jsonl. Old v0 window
and v5..v10 segment are exhausted; never replay them. New candidates ONLY
v11,v12,v13, at most3, each fixed54 cases x5 repeats x1 configuration.
Started2026-10-14T09:47:02+09:00 Asia/Tokyo. No new candidates at/after
2026-10-14T11:17:02+09:00 (+90min). Soft finish2026-10-14T11:47:02+09:00 (+120min).
Finish already-started five-repeat batches; do not kill in-flight API requests.
Enforced early and before first API request by .auto/window.json.

Experiment-branch automatic setup commits/rollback are approved. Preserve
owner-adopted track_2a/src/predict.py v5 and its regression test/documentation
by recording the saved-reference baseline with keep before candidate inference.
Candidate SYSTEM changes execute ONLY in isolated source copies; never edit
adopted application SYSTEM during this segment. Original sibling, push,
deployment and adoption of a new candidate are outside approval.

## New segment / measurement

Target min_Q_gain_v5, higher better: minimum of train/test five-repeat mean Q
improvement over SAVED v5 scores. v5 trainQ0.8275862068965517, testQ
0.8857142857142859. Baseline0. No model rerun, new split or new reference grading.
Config maxIterations4 is one saved-baseline tool record plus at most3 trials
in this new segment. Initialize once for this changed v5-reference target;
retain old log/config headers. Do not initialize again within the new segment.

Use run_experiment direct `bash .auto/measure.sh --baseline` for a read-only
saved-v5 verification, then log metric0 keep as historical-reference import,
not new inference. This establishes the safe adopted-v5 checkpoint. All real
runs use `bash .auto/measure.sh --execute-approved vN`, timeout7200,
checks_timeout180. No shell prefix/exports. Always log the completed run.

Both split gains>=.02 AND >side measured noise are mandatory. Conservative
noise uses max(v5 observed temporal noise, existing v0 measured noise): train
.017051043674621427,test0; observed zero does not prove zero true noise.
Strict supplementary reference gain>=noise+.02 remains reported. Per-repeat
F1A>=.60/B>=.75, canonical/source validity, evidence objective and secondary
regression reporting remain. Scalar primary does not replace individual gates.
Hit@5 is estimated-reference local surrogate, not official overall score.

## Frozen scope / anti-overfitting

Read evals/c-system-prompt/README.md and docs/prompt-eval-log.md for frozen
models, parent70B/actual child8B/thinkingoff, tools, FINAL_VERIFICATION, source
extraction, citation restoration, communication caps, grader/data/split.
Owner override changes candidate count/clock/reference and autonomous approval,
not scorer formulas or fixtures. Update measurement wiring only for this approved
reference switch; freeze it before trials. Do not loosen gates or validators.

Only verified TRAIN individual records/transcripts may inform hypotheses.
No individual test outputs, protected holdout, test-topic failure mining,
seed/split/reference manipulation, case IDs or benchmark-specific exceptions
in prompts. Test aggregates are acceptance checks, not candidate-design input.
Prefer no examples; any examples entirely fictional, never dev54 copies or
paraphrases. Run existing added-text overlap check, not proof of semantics.
This exposed internal split and adaptive selection do not establish unseen
performance. Cost/repair improvements are not classification/evidence gains.

## Candidate sequence / loop

v11: Normalize output-only empty-evidence terminology to candidate_ids. Preserve
meaning, all semantic judgment rules and full introduction. Do not repeat v6's
broad shortening or v7..v10's failed general rule appendings.

v12: Next distinct narrow hypothesis from TRAIN logs: remove duplicate IDs
before submit, even if one span supports several points. Verified train cases
in v5 child0 emitted duplicate existing IDs and child1 repaired to singleton;
diagnostic DUPLICATE_ID. No claim about unseen cases or hidden reasoning.

v13: Only if clock remains and distinct assumptions are clear: explicitly
constrain empty candidate_ids to neutral while preserving existing non-neutral
support requirement. One verified TRAIN child emitted label2/empty list twice,
reported INVALID_TOOL_JSON due to missing supporting span, not malformed syntax.
Do not change the label solely to satisfy formatting; retain source judgment.
If this duplicates v11's actual change, choose no cosmetic retry or stop early.

Each candidate has one hypothesis, based on v5 (or a retained genuine improvement
without test-targeted tweaks), never cumulative discarded policies. Create
vN-system.txt/added.txt/json/patch/overlap under evals/c-system-prompt/prompts;
metadata baseline_prompt_sha256 MUST be v5 hash06c89db1756d54d04cc5f1650b855acda2e2986d4c0c84943d2e54866383313c,
proposed/approved_trials54/5/1, inference_approved:true, exact approval_scope
candidate/version54/5/1 citing this user window. Freeze metadata/artifacts before
prepare; immutable ignored archive preserves hashes on rollback.

Offline `bash .auto/measure.sh --prepare-candidate vN` must audit five isolated
source-only workspaces against v5 frozen user inputs/pages/IDs/role models and
code hashes (only predict.py differs). Existing job paths/STOP/fences prohibit
replay. Required parent/child/split usage is ledger/digest verified; repair-window
usage is a subset, not additive third role or proof of decoded repair payloads.

After each actual run, log parsed primary and EVERY previously tracked secondary
metric, including new-segment saved baseline_v5 constants. ASI records hypothesis,
version/hash, observed general learning, diagnostic scope, and rollback_reason/
next_action_hint on rejection. Completed quality gate failure => checks_failed,
then next distinct candidate while window open. Primary improvement with all
checks passing => keep for research only; unchanged/worse => discard. Actual
API/transport/execution/unknown usage/STOP => log crash and STOP entire loop,
without retries, resume, fence deletion or next candidate. No manual commits/
reverts. Stop at cutoff,3 candidates or4 segment records; never autoextend.

## Previous outcomes

v5 aligned raw output sentence with existing submit contract; improved v0 train
+.079286/test+.070197, per-repeat safety/validity pass. Owner adopted it locally.
Tokens+3.1521%, requests820->835, repair-window10->25 were disclosed. v6 broad
shortening produced8 fallback cases perrepeat and was rejected; v7/v8/v9 failed
quality gates, v10 passed baseline gates but was inferior to v5. Those are NOT
new authorizations or grounds for reruns. Baseline v5 repeated label scores had
observed temporal noise0, distinct from wider sampling uncertainty.
