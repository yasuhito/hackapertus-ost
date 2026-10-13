# Overnight C SYSTEM autoresearch

## Owner-approved window

The user approved autonomous additional candidates v5 through v10, at most six,
with no per-candidate confirmation during this window. Total prompt cap is now
10, overriding the earlier cap5 only for this session. Each candidate still
requires fixed54 cases x5 repeats x1 configuration. Timezone Asia/Tokyo:
The owner rescheduled on the morning of October14 after sleeping; all other
scope/limits remain unchanged. Start new candidates strictly before
2026-10-14T11:00:00+09:00; finish target2026-10-14T12:00:00+09:00. An already-started five-repeat batch may finish;
never forcibly interrupt an in-flight API request merely for the time target.
`.auto/window.json` is enforced before preflight and immediately before the
first request. No new starts after cutoff or v10, even if tool slots remain.

Git setup saving and log_experiment's automatic experiment-branch commits and
rollbacks are authorized. Production adoption and push are not. Keep original
sibling and external dependencies read-only. On actual execution/API/transport/
usage errors or STOP fences, STOP the entire overnight loop; no retry/resume,
next candidate, fence deletion or secret logging. A successfully completed
candidate failing quality/adoption gates is rejection, not an execution error:
record it and move to a genuinely different policy while time/candidate slots
remain. Do not loosen gates to make a rejected candidate pass.

## Existing session

`.auto/log.jsonl` contains config and two records: historical v0 baseline0 and
v4 checks_failed at min_Q_gain -0.11379310344827587. Do not initialize again,
rerun baseline, or rerun archived v1/v2/v3/v4. maxIterations8 includes these two
records and at most six new candidates. Runtime caches limits: after changing
config use Pi /reload before activating mode; retain the existing config/log.
Checkpoint409d39f preserves setup and draft v4 records. Rejected metadata may
revert to draft; existing completed jobs still categorically forbid replay.

## Frozen protocol and anti-overfitting

Read evals/c-system-prompt/README.md, docs/prompt-eval-log.md and
.auto/window.json. The owner override changes only count and autonomous
permission, not scoring, split, noise/safety requirements or model workflow.
SYSTEM-only changes in isolated source-only copies; FINAL_VERIFICATION, parent
70B/actual child8B, thinkingoff, tools, source extraction, quotes, communication,
user inputs, graders/data/split stay frozen. Do not modify measure/check/report
scripts during the loop except a demonstrable integration defect; report it.

Only verified TRAIN individual records/transcripts may inform hypotheses.
Use a small representative sample to identify general behavior, not exhaustive
case-specific rule mining. Never open individual test outputs/transcripts or
protected holdout. Test aggregate scores are acceptance checks only: do not
use them to invent the next policy, probe test failure topics, select seeds,
change references or move split cases. This exposed internal dev split is not
an unseen holdout; repeated selection cannot prove generalization.
Examples, if used, must be wholly fictional and neither copied nor paraphrased
from dev54. Prefer no examples. No external facts, case IDs, gold labels,
booklet details or exceptions targeted at benchmark cases in SYSTEM. Run the
existing overlap check on added text; lexical pass is not semantic proof.

## Tool loop

1. Check actual local time and slots before designing each candidate. Choose
   the next unexecuted ID in v5..v10. Use one general hypothesis distinguishable
   from prior policies; keep discarded policies available for hash checks.
   No automatic v4 retry. If an idea needs changed assumptions, explain them
   rather than cosmetic edits or duplicate prompt replay.
2. Create evals/c-system-prompt/prompts/vN-system.txt, vN-added.txt, vN.patch,
   vN-overlap.json and vN.json. Freeze candidate SYSTEM/hash before evaluation.
   Use initial metadata proposed_trials and approved_trials54/5/1,
   inference_approved:true, approval_scope:{candidate:vN,cases:54,repeats:5,
   configs:1}; cite this approved overnight window, not old v4 permission.
   Do not alter metadata after preparation: archive is byte-exact immutable.
3. Offline prepare with bash .auto/measure.sh --prepare-candidate vN. It audits
   five fresh isolated workspaces against baseline user inputs/pages/IDs and
   source hashes (only predict.py changes). Required role/split usage coverage
   already exists; repair-window slots are a subset, not a third additive role.
   Candidates are archived under ignored output/cscs/candidate-archive/vN before
   execution so tool rollback does not destroy prior hash/history evidence.
4. Use run_experiment with direct command
   `bash .auto/measure.sh --execute-approved vN`, timeout7200, checks_timeout180.
   No shell exports/prefixes: the tool enforces the measure entrypoint.
   Successful measurements write check-context.json for separate-process checks.
5. ALWAYS log a real completed tool run immediately. Primary is parsed
   min_Q_gain, higher better: minimum of train and test five-repeat mean Q gains
   over fixed v0. Zero is existing baseline. Use all parsed secondary metrics
   PLUS previously tracked baseline constants from run1; tool logging requires
   all earlier metric names. Secondary schemas do not change across candidates.
   ASI includes hypothesis, candidate/hash, general learning, diagnostic scope,
   and on rejection rollback_reason and next_action_hint.
6. Completed quality gate failure -> log status checks_failed, preserve ignored
   raw outputs, then next genuinely different candidate if allowed. Actual
   execution failure -> log crash (measured failure, not invented scores), STOP.
   Primary improvement with passing checks -> keep, but not production adoption.
   Unchanged/worse without checks failures -> discard. Never manually commit or
   revert. Never rerun to game noise or conceal failures.
7. Stop at start cutoff, last v10, six additional candidates, any execution STOP,
   or maxIterations8. Report aggregates/limitations; do not autoextend bounds.

Both split gain>=.02 AND gain>side measured noise, strict supplementary
interpretation, A>=.60/B>=.75 EACH repeat, evidence objective and secondary
regression reporting remain required. Scalar min_Q_gain does not replace them.
Local Hit@5 is an estimated-reference surrogate, not official overall score.
Retain all diagnostic/token/time/validity/fallback counts even on rejection.

## History and hypotheses

v1 appended FINAL_VERIFICATION and failed. v2 is independent/unknown; do not
wait for it or duplicate its fictional GOOD/BAD-pair policy. v3 evidence
sufficiency/minimal citations failed train/test gains. v4 conditional parent
ownership failed: train gain-.004683439166197734, test gain-.11379310344827587;
test B F1.65. All v4 runs valid54/54/fallback0;815 requests/5,433,529 tokens.
Eight sampled train executions copied child labels/IDs, but this does not prove
skipped internal review caused errors. Neither longer cautionary instructions
nor forcing disagreement is established as a solution.

Reasonable distinct avenues, not validated prescriptions: simplify redundant
judgment instructions while preserving guards; concise relation alignment
before delegation; resolve ambiguous entailment-vs-contradiction wording without
new benchmark facts. Choose from train evidence and independent logic, never
from individual test failures or test-aggregate-driven targeting.
