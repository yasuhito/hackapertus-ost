# C SYSTEM autoresearch

## Current STOP

Autoresearch mode and the experiment config are initialized. The user approved
the next candidate in principle and suggested inspecting agent logs. v4 has
been prepared and passed offline 54 x 5 source/input audits; no inference yet.
Its conditional parent-ownership SYSTEM SHA256 is
e14dff10a25dbab7e8ae92b6af8a4bbe7adb38d8ba0d99a5b119952783d58a9e.
The user has approved the next candidate and this experiment branch's setup
save and log_experiment automatic commit/revert behavior. Record the saved
historical baseline with keep to checkpoint preparation/v3/v4 draft records
before authorizing v4 metadata and starting inference. No manual commit/revert.
Record each tool run immediately. Do not rerun v3. After the one v4 candidate,
STOP regardless of outcome; v5, production adoption and push are not approved.

## Protocol

Read `evals/c-system-prompt/README.md`, `docs/prompt-eval-log.md`, and
`docs/autoresearch-preparation.md`. The fixed split/evaluator, two split gain
requirements, evidence objective and per-repeat F1 gates remain authoritative.
Change only SYSTEM in isolated source-only workspaces. Keep FINAL_VERIFICATION,
model roles, tools, PDFs/extraction, user inputs, transport and scoring frozen.
Examples must be entirely fictional; no dev-case copying/paraphrase, tuning
split/seeds/grader, or protected holdout access. Individual test outputs and
transcripts stay machine-only. Report Hit as a local reference surrogate.

## Tools after approval

Config already exists in `.auto/log.jsonl`: do not initialize again for this
same target. Primary `min_Q_gain`, higher better, is the minimum of train and
test five-repeat mean Q gains against the fixed v0 baseline. Baseline is zero.
This conservative logging reduction does not replace either split's individual
noise threshold, F1/evidence requirements, or secondary regression reporting.

1. Once Git/logging permission and a safe checkpoint are established, record
   the saved baseline with run_experiment using:
   `export AUTO_BASELINE=1; unset AUTO_CANDIDATE; ./.auto/measure.sh --baseline`.
   No inference occurs. Call log_experiment afterwards with metric 0, baseline
   status keep, description explicitly saved historical baseline, and ASI.
2. Prepare a genuinely new v4 policy and obtain hash/scale approval. Set its
   candidate-specific metadata approval, never borrow v3 approval. Offline
   `./.auto/measure.sh --prepare-candidate v4` must pass first. Resolve any
   mandatory metric coverage gaps before inference.
3. Use run_experiment with sufficient timeout (7200 seconds):
   `export AUTO_CANDIDATE=v4; unset AUTO_BASELINE; ./.auto/measure.sh --execute-approved v4`.
   A successful measurement writes `.auto/check-context.json` for checks.sh,
   which runs in a separate process (shell exports alone do not propagate).
   Always log the completed tool run;
   use the parsed min_Q_gain and all available secondary metrics, with ASI
   hypothesis and, on rejection, rollback_reason/next_action_hint.
4. Keep only measured primary improvements passing checks. Checks failure,
   crash or unknown usage stops the batch. log_experiment Git retention is NOT
   production adoption. Report all regressions before separate adoption approval.
   STOP after this one candidate even on success. v5 needs new approval.

`.auto/config.json` permits two tool records: historical baseline plus one new
candidate. At most five prompt candidates total, including historical v1/v2/v3.
Preserve all uncertain-request fences; no retry, auto-resume, fence clearing,
production edits or push. Raw jobs remain ignored under clone output/cscs;
original sibling/external dependencies are read-only. Keep bytecode disabled.

## History

v1 rejected (see authoritative log). v2 state unknown; proceed independently,
without duplication. v3 completed all 54 x 5, valid 54/54 each, and was rejected:
train gain -0.006028454304316422, test gain -0.1660919540229886; per-repeat test
F1 gates fail. Saved results are only a historical reference, not a new trial.
v4 is prepared from v0, not v3. It conditionally asks the parent to treat a
child recommendation as a proposal and judge it against original source within
the normal final submission; no forced disagreement, extra calls or examples.
Eight sampled train executions copy child labels/IDs unchanged; this does NOT
prove absence of internal review. v4 has zero dev54 8-gram overlap and passed
five offline isolated input/source audits. No v4/v5 inference has run.

Usage measurement now reconciles ledger digests/counters with parent/child
and train/test input/output/total tokens. Extra parent>=2 or child>=1 request
slots are repair-window subsets, not a third additive role or proof of exact
schema-repair payload contents. Missing/invalid usage fails closed.
