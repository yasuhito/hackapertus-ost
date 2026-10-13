# Date-balanced internal split v2: four saved C baselines

Owner-authorized redesign. No new model calls, prompt candidates, model changes,
case edits or scoring edits. Official evaluator
`5e6957729b77a126006049305ad1ef241211a5b4` is unchanged and run by grader.py.
Q_label_norm remains the +0.02 objective; Hit@5 is also primary (20% of SA).

## Partition locked before scoring

Same seed20261016. Group rules unchanged: same source-row A/B together; merge
source rows sharing exact B reference language/text. 27 source rows form24 groups.
The old source-only partition is archived as split-source-only-v1.json.
The new active split.json has version label-date-balanced-v2.

Sorted source-group keys are shuffled once using the fixed seed. Five-dimensional
subset dynamic programming chooses the first feasible state for test source-row
counts(label0,label1,label2,date2020,date2021)=(3,3,3,6,3). Existing group boundaries
are never broken. If no solution exists the script fails instead of weakening
constraints. No predictions, scores, outputs or test failures enter this search;
no seed was changed after seeing results. Synthetic tests verify determinism,
label/date balance, indivisible groups and infeasibility handling (3 pass).

| Side | Cases | Groups | A/B cases | Label0/1/2 per task | Date2020/Date2021 cases |
|---|---:|---:|---|---|---|
| Train |36|16|18/18|6/6/6|24/12|
| Test |18|8|9/9|3/3/3|12/6|

Both dates have the same2:1 ratio on each side. Pair/reference overlap0.
Five booklets have different passages represented on both sides:
- `booklets/2015c2525d232f34.pdf`
- `booklets/75dc1a878a0daf50.pdf`
- `booklets/9c7c82126209674f.pdf`
- `booklets/c5e0fe54167212d7.pdf`
- `booklets/c7e9a49cad953da0.pdf`

Booklet/vote independence is not guaranteed. These54 cases had all been exposed
before splitting. This is not genuinely unseen source generalization. All data
is from2020-09-27/2021-03-07; no protected holdout. After locking v2, test outputs
are machine-scored; only aggregate test metrics are viewed. Individual test
cases, outputs and transcripts are not opened for prompt analysis.

## Official offline rescore

| Split | Repeat | F1 A | F1 B | Q_label_norm | Hit@5 A | A>=.60 | B>=.75 |
|---|---:|---:|---:|---:|---:|---|---|
| train | 1 | 0.666667 | 0.885714 | 0.772414 | 5/12 | pass | pass |
| train | 2 | 0.608392 | 0.885714 | 0.742272 | 5/12 | pass | pass |
| train | 3 | 0.608392 | 0.885714 | 0.742272 | 5/12 | pass | pass |
| train | 4 | 0.608392 | 0.885714 | 0.742272 | 5/12 | pass | pass |
| test | 1 | 0.750000 | 0.885714 | 0.815517 | 2/6 | pass | pass |
| test | 2 | 0.750000 | 0.885714 | 0.815517 | 2/6 | pass | pass |
| test | 3 | 0.750000 | 0.885714 | 0.815517 | 2/6 | pass | pass |
| test | 4 | 0.750000 | 0.885714 | 0.815517 | 2/6 | pass | pass |

All four baselines pass both safety thresholds on both sides. Fallback neutral0 and valid54/54 on each original full run; partitioning does not alter these records.

| Split | Mean Q | Run SD | Run spread | Temporal detectable difference | Case bootstrap95 | Conservative unpaired case detectable difference |
|---|---:|---:|---:|---:|---|---:|
| train | 0.749807 | 0.015071 | 0.030142 | 0.021314 | [0.584408, 0.870920] | 0.204985 |
| test | 0.815517 | 0.000000 | 0.000000 | 0.000000 | [0.520778, 1.000000] | 0.374721 |

Temporal detectable difference is `2 sqrt(2) SD/sqrt(4)`. Four repeats remain
few; zero observed test SD is not a proof of zero generation noise. Bootstrap
uses20,000 resamples, seed20261016, keeps source groups and all repeat confusion
contributions together. Sampling uncertainty is not API randomness. Conservative
unpaired differences are not estimates of an unexecuted paired candidate delta.

**STOP: hillclimb §1 noise gate.** Train detectable difference0.021314 still
exceeds+0.02. The better threshold status under the new split does not represent
a model improvement; this is a different partition of unchanged predictions.
No prompt candidate, further baseline or model API call is authorized by this
report. Keep adoption rules intact: both splits improve beyond noise, +0.02 on
Q_label_norm, A>=0.60/B>=0.75, report metric regressions before adoption.

Approval question: retain this frozen date-balanced split and authorize a fifth
unchanged54-case C repeat, then reassess sensitivity? Expected5-6 minutes and
about1.07m tokens, existing270 POST/6m-token ceiling. It may or may not reduce
noise enough. Alternatively propose independently sourced approved dev cases at
the case-list review checkpoint; do not pick a new seed from test performance
or weaken thresholds. Protected holdout remains prohibited.

Detailed local reports and predictions are ignored under output/. This tracked
report contains aggregate metrics only. No raw output is committed.
