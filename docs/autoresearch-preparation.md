# C SYSTEM experiment-tool integration

The config in `.auto/log.jsonl` initializes primary `min_Q_gain`, higher better.
The user has now approved next-candidate evaluation and experiment-branch
setup saving/automatic Git logging. The first tool cycle will record the saved
historical baseline to establish the safe checkpoint, not rerun inference. `.auto/prompt.md` records the
current STOP and exact post-approval workflow; read it before continuing.

## Fixed protocol and permissions

`evals/c-system-prompt/README.md` and `docs/prompt-eval-log.md` govern evaluation:
fixed exposed dev54 split and five repeats, unchanged official evaluator,
SYSTEM-only changes, two independent split/noise requirements, per-repeat F1
gates and evidence objective. The conservative minimum split gain is only a
scalar for tool logging, not a replacement for these conditions. Local Hit@5
uses estimated reference passages and is not the official overall score.

Next inference needs candidate-specific hash and 54 x 5 x 1 approval. Production
adoption and push are separate. log_experiment automatically stages/commits on
keep and reverts on rejection; existing untracked preparation/v3 records could
be affected. Git-operation permission has now been granted. Record the historical baseline
with keep to checkpoint setup and archived candidate records before v4 inference. Never use tool keep as automatic
production adoption. The two tool records allowed by config are saved baseline
plus one new candidate, not two candidates.

## Commands

```sh
# Historical baseline only; no model calls or new grading.
./.auto/measure.sh --baseline
# Existing v3 reports only; no rerun, model calls or new grading.
./.auto/measure.sh --saved v3
# Next candidate preparation only; artifacts must first exist.
./.auto/measure.sh --prepare-candidate v4
# ONLY after separate explicit v4 approval. Not yet approved.
# ./.auto/measure.sh --execute-approved v4
```

Default/unknown modes refuse execution. v3 runner execution is permanently
refused. Future runner IDs are v4/v5 only, five total including historical
v1/v2/v3. Metadata must match the selected candidate and exact scale; CLI flags
alone do not grant approval. Existing jobs/sidecars/fences refuse the entire
batch before any request. Fresh source-only workspaces, six independent local
PDF copies and unchanged prepared user inputs/pages/IDs/source audits precede
execution. Only predict.py SYSTEM differs. No retries/resume or fence clearing.

Scoring/comparison scripts use the existing official grader and bootstrap
semantics. results.py reads aggregates, verifies five completed jobs/IDs/fences,
and emits primary/secondary METRIC lines. checks.sh enforces both split gains,
per-repeat F1 and validity. A successful measurement explicitly records its
baseline/candidate selector in .auto/check-context.json, so separate-process
checks do not depend on shell exports. Conflicting environment selectors refuse. Secondary evidence
and resource changes still need reporting before adoption. usage.py now verifies saved record/manifest digests, known/valid usage and
ledger totals before reporting parent/child and train/test input/output tokens.
Repair-window token usage (parent request number >=2 or child >=1) is a subset
of those role totals, not additional usage or proof of decoded schema-repair
payloads. Missing usage fails closed. v3 reconciles to 3,611,843 parent tokens,
1,857,015 child tokens, 56,865 repair-window subset tokens and 820 requests.

## Local data and historical result

Ignored output/cscs contains byte-preserved completed format-C-r1/r2/r3/r4./r5,
seven ROOT-adapted historical scripts, official-rescore-evidence and
hillclimb-split5-date-balanced-analysis. preparation-provenance.json records
checksums and six PDF mappings. Original manifests remain unchanged; r4 start
is missing and is never reconstructed. PDFs are independent booklets/ copies.
Original sibling/external dependencies are read-only; protected holdout and
individual test outputs/transcripts remain unopened. Older noise scripts that
inspect individual failures must not be executed under this policy.

v3 completed five repeats with 820 requests and 5,468,858 total tokens. Train Q
mean 0.7422715215818665, gain -0.006028454304316422; test Q mean
0.6494252873563219, gain -0.1660919540229886. Literal and strict label adoption
both fail; per-repeat test F1 gates fail. It is rejected, not rolled back from
production because production was never changed. Raw evidence remains ignored.
v2 state is unknown and imposes no waiting requirement or duplication permission.

## Offline validation

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -B .auto/test_controls.py
PYTHONDONTWRITEBYTECODE=1 /tmp/ost-official-evaluator-3U4yO9/env/bin/python -B .auto/test_scoring.py
```

The replay passes saved v0 predictions through official scoring/comparison in a
disposable local directory and expects zero gain/no adoption. It is not a v3
result. Shell/Python syntax, baseline/saved modes and archived-candidate/approval/
fence refusal checks pass. v4 has now passed five isolated offline workspaces (54 cases each); no v4/v5
inference has run. Its policy is conditional parent source-based ownership of
the child recommendation, with no forced disagreement, extra calls or examples.
Design evidence came from four verified train failures in baseline r1/v3 r1:
all eight parent submissions matched their child's label/IDs. This observation
does not establish that internal source review was absent. No individual test
outputs were used to design v4. Next-candidate approval was given in principle;
Git-logging permission is now granted. v4 will run only after the saved-baseline
checkpoint and explicit candidate metadata authorization.

The external evaluator is read-only at /tmp/ost-official-evaluator-3U4yO9/repo,
commit 5e6957729b77a126006049305ad1ef241211a5b4, with interpreter
/tmp/ost-official-evaluator-3U4yO9/env/bin/python. Verify pin/integrity and leave
dependencies unchanged. All subprocess bytecode writing stays disabled.
