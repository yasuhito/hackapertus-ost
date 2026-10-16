# C system-prompt eval

## Approved scope

54 already-exposed development cases only, from 2020-09-27 and 2021-03-07.
This is not an unseen holdout. Never read the protected competition holdout.
C uses the authoritative nonthinking Apertus v1.5 70B parent and an actual
pi-subagents 8B child. Only the system prompt may change during hillclimb.
The existing runner, tool contracts, model roles and transport caps stay fixed.

## Official scoring

`grader.py` executes an unmodified external checkout of:

- https://gitlab.com/ifsoftware/hackapertus-starter.git
- commit `5e6957729b77a126006049305ad1ef241211a5b4`
- file `evaluate.py`

Acquire that public checkout outside this repository. Install its dev dependencies
in a separate environment. Pass the checkout and interpreter explicitly:

```sh
python3 evals/c-system-prompt/grader.py \
  --official-repo /tmp/official-starter \
  --python /tmp/official-env/bin/python \
  --predictions /path/to/canonical.jsonl \
  --expected /path/to/expected.jsonl \
  --cases /path/to/cases.jsonl \
  --output /path/to/ignored-results.json
```

`cases.jsonl` contains reviewed public inputs, expected labels and paired reference
passages for scoring only. Never expose these expectations, this directory, or
any grader to the model. Official CLI `--cases` rows are each case's `input`;
`--expected` rows are `{"id": id, **expect}`. The reviewed paired reference is
used as `expected.reference`, exactly as official `prepare_cases.py` uses the
underlying row's `reference_string`. Neutral expectations omit reference.

## Objectives and adoption rules

- Classification: `Q_label_norm = (0.30 F1_A + 0.28 F1_B) / 0.58`.
  The minimum worthwhile gain is +0.02 on this metric, beyond measured noise
  on **both train and test**. `Q_task` is logging only, not a goal.
- Evidence: Task A Hit@5 is a second primary improvement objective. Baseline
  reference is 7/18; its contribution is 20% of SA. Do not claim that improved
  labels alone establish improved overall official performance.
- Always log F1_A, F1_B, Hit@5, canonical/source validity, fallback-neutral count,
  all parent/child/repair tokens, case wall time and API wait separately.
- Require F1_A >= 0.60 and F1_B >= 0.75 on every scored evaluation.
  Upstream's B threshold remains 0.70; the safety policy is separate.
- Report any secondary metric regression before adoption.
- Canonical fallback neutral is scored by official `label_of`, not changed to
  INVALID by internal error metadata. Count fallbacks separately.
- Maximum five prompt candidates, entirely fictional prompt examples only.
- Preserve uncertain-request fences. No unknown-usage retry or auto-resume.
- Honor every eval-hillclimb STOP. A baseline noise check precedes any split or
  candidate. New runs require approved scale; baseline repeats 3 and 4 were approved.

The application runner creates fresh isolated parent and child workspaces and
in-memory credentials; scoring-only fixtures are not mounted there. Baseline
repeat 3 uses `--repeat 1 --job output/cscs/format-C-r3` because the unchanged
runner's repeat option accepts only 1/2 and controls the default path only.
Repeat 4 was saved at `output/cscs/format-C-r4.` (trailing dot from the operator's
command); preserve that actual completed job, do not rename or rerun it.
Its command start timestamp was not saved; command duration is unavailable.
Neither difference changes model configuration or scoring inputs.

## Frozen internal train/test split

`make_split.py` creates `split.json` without reading predictions. Seed 20261016;
36 train cases and 18 test cases, balanced over 3 labels within each task.
Keep each source-row A/B pair together AND merge pairs whose B reference
language/text is identical: 27 source rows become 24 source groups. The seeded
ordering and label-balanced subset algorithm are recorded in split.json.
Public source_date metadata guards the two approved dates; no dataset-wide read.
The owner-approved v2 redesign additionally enforces the same 2:1 date ratio
on each side: train dates24/12 cases, test dates12/6 cases. The seed is unchanged.
Five-dimensional dynamic programming targets test source-row label counts3/3/3
and date counts6/3 simultaneously. Predictions and scores are not inputs.
`split-source-only-v1.json` preserves the original split; active `split.json`
is version `label-date-balanced-v2`. No score-based search or seed selection.
Different passages from a shared booklet/vote can still cross splits. This is
an exposed internal split, not genuine held-out generalization. Do not re-seed
or repartition to improve scores or move failures. After creation, inspect
train outputs only; test outputs are machine-scored and aggregate-only.
`report-date-balanced-v2.md` records the current noise STOP;
`report-four-repeats.md` is historical (source-only v1).

## Five-repeat baseline and first prompt draft

`docs/prompt-eval-log.md` records five-repeat aggregate scores and all required
secondary metrics for repeat5. Train temporal detectable difference is0.017051,
below0.02; test observed run SD is0 (not proof of zero true noise).
`prompts/v0-system.txt` freezes baseline SYSTEM; `prompts/v1.patch` proposes
activating existing FINAL_VERIFICATION in SYSTEM. v1 was evaluated in5 isolated source-only copies and rejected under both adoption
interpretations. Production was not changed. Its general policy has0 examples
and0 approved-dev54 word8-gram overlaps. `check_prompt_overlap.py` performs that mechanical check; its unit
tests use fictional data only. Test fixture text is never displayed by the check.
Candidate1 completed54×5×1 trials in1680.203 summed command seconds,
815 POSTs/5,463,187 tokens, all valid54/54 per run. Train Q gain-0.002756,
test gain-0.210920; test fails both safety thresholds. Hit@5 improved but does
not override label/gate regressions. No candidate2 inference is approved.
Literal adoption: gain>=0.02 AND gain>side's noise width on both splits.
Strict reference: gain>=noise width+0.02. Both rejectv1.
Await STOP approval for any next round and for any production change.

Raw outputs, transcripts and local metrics remain under ignored `output/`.
No raw outputs are committed. `grader-review.md` records the official scoring
semantics approved by the owner, superseding the older local-grader review.

## Portable saved-run CLI

Current owner procedure/results: `docs/dev54-eval-runbook.md`. Candidate v2 was
rejected; production remains v0. These helpers do not discover jobs or retry.
Set `REPO` to the repository root, `RUN_PYTHON` to the runner interpreter,
`EVAL_PYTHON` to the interpreter with official scoring dependencies (including
NumPy), and `OFFICIAL_REPO` to the pinned external evaluator checkout. Export
`PI_PACKAGE_ROOT` and `PI_SUBAGENTS_ROOT` as described in the format README.
No machine-specific defaults are embedded in these helpers.

```sh
# Baseline; fresh explicit prefix, one batch, real ordinals 1 through 5.
"$RUN_PYTHON" -B evals/c-system-prompt/run_batch.py \
  --repo "$REPO" --python "$RUN_PYTHON" --count 5 --start-index 1 \
  --prefix "$REPO/output/cscs/new-baseline" --prepare-only
# Candidate SYSTEM append (never executes prompt Python); same default offline mode.
"$RUN_PYTHON" -B evals/c-system-prompt/run_batch.py \
  --repo "$REPO" --python "$RUN_PYTHON" --count 5 --start-index 1 \
  --prefix "$REPO/output/cscs/new-candidate" \
  --prompt-file evals/c-system-prompt/prompts/v2-added.txt \
  --metadata evals/c-system-prompt/prompts/v2.json --prepare-only
```

Alternatively pass `--jobs PATH1 PATH2 ...` instead of `--prefix`; exactly
`--count` fresh paths are required. Preparation creates private source-only
workspaces, but no designated jobs/logs and no credential reads/remote requests.
Only six approved PDF links are added. Live operation requires separately
recorded user approval: replace `--prepare-only` with `--user-run --approval
'runbook approval reference'`. Do not use live mode without that approval.
The entire batch's designated jobs/logs/provenance is checked for preexistence
before requests. A failure stops the batch; all workspaces/jobs/fences remain.

```sh
# Official full rescore plus arbitrary-N run noise; exact read-only job inputs.
"$EVAL_PYTHON" -B evals/c-system-prompt/analyze_runs.py score \
  --repo "$REPO" --official-repo "$OFFICIAL_REPO" --python "$EVAL_PYTHON" \
  --jobs output/cscs/format-C-r1 output/cscs/format-C-r2 \
  --part full --destination output/cscs/new-full-score
# Fixed label-date-balanced-v2 split; r4. remains exact, never renamed.
"$EVAL_PYTHON" -B evals/c-system-prompt/analyze_runs.py score \
  --repo "$REPO" --official-repo "$OFFICIAL_REPO" --python "$EVAL_PYTHON" \
  --jobs output/cscs/format-C-r1 output/cscs/format-C-r2 output/cscs/format-C-r3 \
         output/cscs/format-C-r4. output/cscs/format-C-r5 \
  --part split --destination output/cscs/new-split-score
# Paired source-group bootstrap; each arm retains its own actual repeat count.
"$EVAL_PYTHON" -B evals/c-system-prompt/analyze_runs.py compare \
  --repo "$REPO" --official-repo "$OFFICIAL_REPO" --python "$EVAL_PYTHON" \
  --jobs output/cscs/format-C-r1 output/cscs/format-C-r2 output/cscs/format-C-r3 \
         output/cscs/format-C-r4. output/cscs/format-C-r5 \
  --candidate-jobs output/cscs/prompt-C-v2-r1 output/cscs/prompt-C-v2-r2 \
         output/cscs/prompt-C-v2-r3 output/cscs/prompt-C-v2-r4 output/cscs/prompt-C-v2-r5 \
  --part split --destination output/cscs/new-comparison
```

`score` includes noise; no separate wrapper is needed. Only completed,
known-usage C jobs with all 54 cases are normal inputs. All generated data lives
under a fresh ignored `output/` destination; stdout is aggregate-only, never
individual TEST predictions/transcripts. Expected labels/references come from
the tracked approved fixture, not ignored historical gold. Missing start times
are null (no r4 prefix repair or inference). SD/noise is null for one repeat.

Comparisons audit source inputs, pages, user messages, IDs/schema and all
model/cap/policy fields. Historical `predict.py` differences require provenance
review: a hash alone cannot establish SYSTEM-only changes. If comparing current
CLI-only code changes with historical runs, explicitly add
`--allow-cli-only-hash-changes`; only `run_comparison.py` and its new CLI test
hash/presence differences are allowed and displayed, not concealed. This never
permits changed tools/models/caps. Bootstrap reports both pooled-confusion F1
and mean-repeat nonlinear F1 estimands. Adoption gates use mean Q, baseline run
noise, .02 minimum gain, and every repeat's task safety thresholds; evidence,
validity, timing and token regressions still require review.

Focused offline tests (pytest in the selected interpreter, NumPy for analysis):

```sh
"$RUN_PYTHON" -m pytest -q -p no:cacheprovider track_2a/dev/format/test_cli_paths.py
"$EVAL_PYTHON" -m pytest -q -p no:cacheprovider evals/c-system-prompt/test_runbook_cli.py
```

## Owner-approved single-tool experiment: id-existence-check

Production and default paths remain **v0 C**. Only an explicit
`--variant id-existence-check` applies its separately tracked `.patch` and
`.json` specification in a source-only temporary archive. The rejected
`evidence-only-child` overlay is never composed with this experiment.
Only archived `submit-extension.ts`, `sdk.ts`, and `run_comparison.py` change;
`package-child.mjs`, v0 SYSTEM, parent submit validator/schema and the child's
label-plus-IDs recommendation protocol are unchanged.

Parent order is forced native function choice:
`subagent -> check_candidate_ids -> submit`. The one new parent-only tool
accepts exactly `candidate_ids: string[]`, max5, empty/duplicates/unknown queries
allowed, no extra properties. Its ordered results contain only
`{candidate_id, exists}`; exact membership is **not semantic support**.
No filtering, deduplication, search, rule checking or automatic correction.
Final submitted IDs may differ; that mismatch is recorded, not prohibited.

**Tradeoff:** the check consumes the existing third parent completion slot.
A failed final submit cannot obtain a fourth request for repair. All caps stay
unchanged: 270 POSTs/run, 6m tokens, parent3/child2, at most one schema repair,
256 output tokens, existing deadlines/reservation/fences/private child isolation.
The child still uses the real pinned `runAgent` with its sole submit tool.

With the pre-existing interpreters/dependencies and six approved local PDFs
set up as above (no install or credential operation needed for preparation):

```sh
"$RUN_PYTHON" -B evals/c-system-prompt/run_batch.py \
  --repo "$REPO" --python "$RUN_PYTHON" --count 5 \
  --prefix "$REPO/output/cscs/id-check-C" \
  --variant id-existence-check --prepare-only
```

Preparation automatically checks the new patch's added instruction lines for
approved54 word8-gram overlap, verifies exact source maps, immutable policy and
frozen input/base-vs-new declaration hashes, and performs no key reads/API calls.
The lexical check is not a semantic nonparaphrase proof. Live operation is the
parent's separately approved54x5 run only, after commit verification; retain all
jobs/fences and never retry an uncertain send. Use the same explicit variant on
`analyze_runs.py score/compare`. Comparison with the five historical v0 jobs also
requires `--allow-cli-only-hash-changes`; exact historical source maps are pinned.
No old role experiment or prompt mixture is accepted.

Case SDK records include deterministic inputs/results, check call count,
unknown IDs, checked IDs, accepted submitted IDs and their ordered mismatch.
Run summaries and split analysis aggregate counts. Structural qualification
checks success, exact source membership, label-free local result shape, ordering
and model/tool identity independently of classification quality. Existing
classification, evidence, cost, literal/strict adoption and safety metrics remain.
Child-label-free qualification applies **only** to evidence-only-child, not
this v0-label child. Default analysis rejects both variants.

After the new live54x5, review **all TRAIN** exchanges/tool calls/source evidence/
labels before any next proposal or STOP decision; TEST stays aggregate-only.
Do not commit raw model logs. No live results are available from implementation
or synthetic SDK tests.

```sh
"$EVAL_PYTHON" -B -m pytest -q -p no:cacheprovider evals/c-system-prompt
"$RUN_PYTHON" -B -m pytest -q -p no:cacheprovider \
  track_2a/dev/format track_2a/dev/cscs track_2a/tests -k 'not test_no_split_leakage'
```
