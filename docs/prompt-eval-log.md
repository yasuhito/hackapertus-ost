# C system-prompt evaluation log

## Fixed protocol

Official evaluator commit5e6957729b77a126006049305ad1ef241211a5b4, unmodified,
via evals/c-system-prompt/grader.py. Split95c3468 date-balanced v2,
seed20261016, train36/test18,24 source groups. No split changes from scores.
Parent swiss-ai/Apertus-v1.5-70B, actual package child swiss-ai/Apertus-v1.5-8B,
nonthinking, Pi1.1.0, pi-subagents0.19.0, Node26.10.0.
Only SYSTEM may change. No tool/runner/model/assembler edits.

Primary: Q_label_norm and Task A Hit@5. Q_task is logging only.
Adoption requires both train/test improvements beyond noise plus at least+0.02,
and A>=0.60/B>=0.75. Secondary regressions must be reported before adoption.
Maximum5 candidates. Examples must be wholly fictional; no dev54 copying or
paraphrase. Test individual outputs/transcripts are never opened after splitting.
This remains an already-exposed internal development eval, not unseen holdout.

## v0 baseline: five repeats

| Split | Repeat | Q | F1 A | F1 B | Hit@5 A | A/B gates |
|---|---:|---:|---:|---:|---:|---|
| train | 1 | 0.772414 | 0.666667 | 0.885714 | 5/12 | pass/pass |
| train | 2 | 0.742272 | 0.608392 | 0.885714 | 5/12 | pass/pass |
| train | 3 | 0.742272 | 0.608392 | 0.885714 | 5/12 | pass/pass |
| train | 4 | 0.742272 | 0.608392 | 0.885714 | 5/12 | pass/pass |
| train | 5 | 0.742272 | 0.608392 | 0.885714 | 5/12 | pass/pass |
| test | 1 | 0.815517 | 0.750000 | 0.885714 | 2/6 | pass/pass |
| test | 2 | 0.815517 | 0.750000 | 0.885714 | 2/6 | pass/pass |
| test | 3 | 0.815517 | 0.750000 | 0.885714 | 2/6 | pass/pass |
| test | 4 | 0.815517 | 0.750000 | 0.885714 | 2/6 | pass/pass |
| test | 5 | 0.815517 | 0.750000 | 0.885714 | 2/6 | pass/pass |

| Split | Mean Q | Run SD | Temporal detectable difference | Case bootstrap95 |
|---|---:|---:|---:|---|
| train | 0.748300 | 0.013480 | 0.017051 | [0.583760, 0.869446] |
| test | 0.815517 | 0.000000 | 0.000000 | [0.520778, 1.000000] |

Detectable difference =2sqrt(2)SD/sqrt(5). Temporal sensitivity gate now clears
0.02. Sampling uncertainty remains much wider; it is distinct from repeat noise.
Use paired candidate-difference intervals after a candidate, not the conservative
unpaired baseline case interval as a fabricated measured candidate delta.

### Repeat5 operational/secondary metrics

Exact job output/cscs/format-C-r5 (no trailing dot), start/end saved,
exit0,164 POST,1,067,678 tokens,315.481 command seconds. Baseline inputs and
source hashes identical to repeat1. Full valid54/54, fallback neutral0,
contradiction→entailment9. All source/tool limits unchanged.

| Split | Valid | Fallback neutral | Contradiction→entailment | Tokens | Mean/p95 ms |
|---|---:|---:|---:|---:|---|
| train | 36/36 | 0 | 6 | 641,810 | 5392.772/6994.300 |
| test | 18/18 | 0 | 3 | 425,868 | 6195.116/8388.268 |

## v1 candidate: draft, not applied or evaluated

Hypothesis from train-only analysis: accepted citations still coexist with
wrong semantic polarity, ignored exceptions, and misaligned speaker/conditions.
A general final label/evidence check may reduce these failures.

Proposed one-line SYSTEM change: append the existing, currently unused
FINAL_VERIFICATION constant after the neutral/paraphrase guards. This checks
source negation/exclusions against the selected label, and distinguishes a
negative claim supported by negative source text from a contradiction.
No fabricated examples are needed for this first caution-only candidate (0 examples).
No source facts, numbers, names or case excerpts are inserted.

Artifacts: evals/c-system-prompt/prompts/v1.patch, v1-system.txt, v1-added.txt,
v1.json. v0-system.txt freezes the baseline system text. File SHA matches the
recorded prompt content SHA. Production predict.py is still unchanged.

Automatic approved-dev54 overlap check: NFKC/casefold word8-grams,54 cases,
0 overlapping cases. Candidate context-size estimate65252 bytes <66000 cap.
Lexical overlap is not a proof against semantic paraphrase; this candidate is
only a general policy and contains no worked example. Checks consume public
fixture text mechanically and expose only counts, not test case content.

| Version | Change | Train/test Q,F1_A,F1_B,Hit@5 | Valid/fallback/C→E | Tokens/time | Decision |
|---|---|---|---|---|---|
| v1 | Activate final-verification policy | not run | not run | not run | draft; run-size approval STOP |

Proposed scale:54 cases×5 repeats×1 configuration =270 case trials,
about25-30 minutes and5.3m expected tokens, at most270 POST/6m tokens PER job.
No candidate inference yet. Need explicit scale approval per skill before run.
Then compute paired differences on each split and retain only an eligible gain.
Using current baseline temporal margins conservatively, required point gains
are at least0.037051(train) and0.020000(test), subject also to measured candidate
noise and paired confidence intervals. No adoption if secondary regressions
require an unresolved decision. Stop at every skill checkpoint.

Raw outputs/logs/local reports stay ignored under output/. No raw output committed.
