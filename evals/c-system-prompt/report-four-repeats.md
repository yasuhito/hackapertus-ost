# Four-repeat C baseline and frozen internal split

Official evaluator commit `5e6957729b77a126006049305ad1ef241211a5b4`, unmodified,
executed through grader.py. Q_label_norm is the +0.02 objective; Task A Hit@5
is also a primary improvement goal. Q_task is not an adoption objective.
Only baseline repeat 4 made new model calls; all split scoring is offline.

| Repeat | F1 A | F1 B | Q_label_norm | Hit@5 A | Valid | Fallback neutral | Contradiction→entailment | Tokens |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 0.700000 | 0.885714 | 0.789655 | 7/18 | 54/54 | 0 | 8 | 1,067,678 |
| 2 | 0.657143 | 0.885714 | 0.767488 | 7/18 | 54/54 | 0 | 9 | 1,067,678 |
| 3 | 0.657143 | 0.885714 | 0.767488 | 7/18 | 54/54 | 0 | 9 | 1,067,678 |
| 4 | 0.657143 | 0.885714 | 0.767488 | 7/18 | 54/54 | 0 | 9 | 1,067,678 |

All full-dev runs pass A>=0.60/B>=0.75. Each has 164 POSTs, fixed 70B parent/8B
actual package child, and 2 child duplicate-ID schema repairs. No API failures,
timeouts, invalid/empty canonical predictions or nonzero exits. No prompt or
production runner changes. Frozen inputs identical across all repeats.

Repeat 4 actual job is `output/cscs/format-C-r4.` with a trailing dot. This
operator path typo is preserved, not renamed or rerun. The start timestamp was
not saved, so command duration is unavailable. Stored case mean/p95 is
6427.684/10240.912 ms; API wait 282.020 s. Do not manufacture missing telemetry.

## Full-dev noise

- Q mean: 0.773030; run SD: 0.011084; run spread: 0.022167.
- Mean SE: 0.005542; t95 df3: [0.755393, 0.790666].
- Temporal detectable difference `2 sqrt(2) SE_mean`: **0.015675** (<0.02).
- Case bootstrap Q95: [0.639833, 0.880036]; conservative unpaired detectable difference: 0.173234.
- Hit@5 always 7/18; case bootstrap95 [0.166667, 0.625000].

20,000 draws, seed20261016, A/B source-row paired resampling, repeat contributions
averaged per case. Pooled nonlinear Q=0.773197, distinct from mean of run Q.
Case uncertainty is not generation noise; unpaired estimates do not substitute
for paired candidate-difference intervals. Four repeats remain a small sample.

## Split, created without predictions

Seed20261016; 27 A/B source-row pairs. Merge identical B reference language/text,
including three pairs of duplicate references: **24 source groups**. Randomized
source-group ordering, first label-balanced subset reached by dynamic programming.
Train36 cases (16 groups), test18 cases (8 groups). A/B and identical reference
source overlap is zero. Three booklets appear on both sides with different
passages; broader vote/booklet dependence remains. Do not call this unseen
source generalization. All cases were exposed before partitioning.

Per task train18 cases, each label6; test9 cases, each label3.
Train dates: 2020-09-27 30 cases, 2021-03-07 6.
Test dates: 2020-09-27 6 cases, 2021-03-07 12.
No source-date stratification guarantee; this imbalance is reported, not fixed
by choosing a score-favorable seed. Protected holdout was never used.
After split creation, no individual test output or transcript was opened;
only machine-scored aggregate test results are shown below.

| Split | Repeat | F1 A | F1 B | Q | Hit@5 A | A>=.60 | B>=.75 |
|---|---:|---:|---:|---:|---:|---|---|
| train | 1 | 0.608392 | 0.885714 | 0.742272 | 0.416667 | pass | pass |
| train | 2 | 0.542857 | 0.885714 | 0.708374 | 0.416667 | FAIL | pass |
| train | 3 | 0.542857 | 0.885714 | 0.708374 | 0.416667 | FAIL | pass |
| train | 4 | 0.542857 | 0.885714 | 0.708374 | 0.416667 | FAIL | pass |
| test | 1 | 0.885714 | 0.885714 | 0.885714 | 0.333333 | pass | pass |
| test | 2 | 0.885714 | 0.885714 | 0.885714 | 0.333333 | pass | pass |
| test | 3 | 0.885714 | 0.885714 | 0.885714 | 0.333333 | pass | pass |
| test | 4 | 0.885714 | 0.885714 | 0.885714 | 0.333333 | pass | pass |

| Split | Q mean | Run SD | Temporal detectable difference | Case Q bootstrap95 | Conservative unpaired case detectable difference |
|---|---:|---:|---:|---|---:|
| train | 0.716849 | 0.016949 | 0.023969 | [0.565900, 0.819376] | 0.184755 |
| test | 0.885714 | 0.000000 | 0.000000 | [0.555556, 1.000000] | 0.388708 |

## STOP: hillclimb §1 sensitivity gate on both splits

Full-dev temporal sensitivity improved, but train detectable difference is
**0.023969 > +0.02**. Train A also fails the safety threshold in repeats2-4.
Test run SD0 means no observed variance, not guaranteed absence of noise.
Both-splits adoption rules remain unchanged. No prompt candidate or further
inference launched. No score-based repartitioning or relaxed thresholds.

Approval questions: keep this split and authorize an additional unchanged
baseline repeat to reassess train temporal sensitivity, or propose a new
case/split design at an explicit review checkpoint? Larger independent approved
case coverage may be needed for sampling uncertainty. Never use protected
holdout. If changing the split or cases, freeze the new design and rescore all
baselines before any candidate, rather than using test outcomes to pick a seed.

Committed report contains aggregate metrics only. Raw predictions/transcripts,
full local grader reports and analysis scripts remain ignored under output/.
