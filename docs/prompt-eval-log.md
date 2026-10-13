# C system-prompt evaluation log

## Fixed protocol

Official evaluator commit5e6957729b77a126006049305ad1ef241211a5b4, unmodified,
via evals/c-system-prompt/grader.py. Split95c3468 date-balanced v2,
seed20261016, train36/test18,24 source groups. No split changes from scores.
Parent swiss-ai/Apertus-v1.5-70B, actual package child swiss-ai/Apertus-v1.5-8B,
nonthinking, Pi1.1.0, pi-subagents0.19.0, Node26.10.0.
Only SYSTEM may change. No tool/runner/model/assembler edits.

Primary: Q_label_norm and Task A Hit@5. Q_task is logging only.
Literal adoption rule: on BOTH train/test, gain>=0.02 AND gain exceeds that
side's noise width (minimum detectable difference); require A>=0.60/B>=0.75.
Also report the strict reference rule gain>=noise width+0.02.
Secondary regressions must be reported before adoption. Production is unchanged
until approval at STOP; candidate patches execute in isolated source-only copies.
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

## v1 candidate: evaluated, rejected; production unchanged

Change: append existing FINAL_VERIFICATION to SYSTEM (one line), reinforcing
source/label polarity, negation/exclusions, attribution and final evidence checks.
0 examples; approved-dev54 normalized word8-gram overlap0. The patch is archived
in evals/c-system-prompt/prompts/v1.patch; exact text/hash in v1-system.txt/v1.json.

```diff
-SYSTEM += "\n\n" + NEUTRAL_GUARD + "\n\n" + PARAPHRASE_GUARD
+SYSTEM += "\n\n" + NEUTRAL_GUARD + "\n\n" + PARAPHRASE_GUARD + "\n\n" + FINAL_VERIFICATION
```

Applied only in5 fresh source-only /tmp workspaces, no .git or eval/gold fixtures.
Each workspace links only the6 approved booklet PDFs. Parent/child workspaces
remain fresh and isolated. Machine audit verified all user messages, pages and
candidate IDs equal baseline; code hashes differ only for predict.py SYSTEM.
Production predict.py was never edited. Official evaluator and adapter unchanged.

Exact jobs output/cscs/prompt-C-v1-r1 through prompt-C-v1-r5, no trailing dots;
each has exclusive start/end/exit records. All5 completed exit0, valid54/54,
fallback neutral0, known usage only. No retries or fence clearing.

### Per-repeat primary metrics

| Split | Repeat | Q | F1 A | F1 B | Hit@5 A | A/B gates |
|---|---:|---:|---:|---:|---:|---|
| train | 1 | 0.745544 | 0.614719 | 0.885714 | 0.500000 | pass/pass |
| train | 2 | 0.745544 | 0.614719 | 0.885714 | 0.500000 | pass/pass |
| train | 3 | 0.745544 | 0.614719 | 0.885714 | 0.500000 | pass/pass |
| train | 4 | 0.745544 | 0.614719 | 0.885714 | 0.500000 | pass/pass |
| train | 5 | 0.745544 | 0.614719 | 0.885714 | 0.500000 | pass/pass |
| test | 1 | 0.604598 | 0.555556 | 0.657143 | 0.333333 | FAIL/FAIL |
| test | 2 | 0.604598 | 0.555556 | 0.657143 | 0.500000 | FAIL/FAIL |
| test | 3 | 0.604598 | 0.555556 | 0.657143 | 0.500000 | FAIL/FAIL |
| test | 4 | 0.604598 | 0.555556 | 0.657143 | 0.500000 | FAIL/FAIL |
| test | 5 | 0.604598 | 0.555556 | 0.657143 | 0.500000 | FAIL/FAIL |

### Means, deltas and both adoption interpretations

| Split | Baseline Q | v1 Q | Gain | Noise width | Literal | Strict | Paired group delta95 |
|---|---:|---:|---:|---:|---|---|---|
| train | 0.748300 | 0.745544 | -0.002756 | 0.017051 | FAIL | FAIL | [-0.065808, 0.068035] |
| test | 0.815517 | 0.604598 | -0.210920 | 0.000000 | FAIL | FAIL | [-0.396552, -0.017555] |

Literal rule thresholds: gain>=0.02 and above noise0.017051(train)/0(test).
Strict reference thresholds: train>=0.037051, test>=0.020000. v1 fails both
because train mean slightly decreases and test regresses substantially.
Candidate Q run SD0 on both sides. Paired case-group bootstrap uses20,000 draws,
seed20261016, same source groups in both arms, all5 repeat contributions retained.
The delta interval pools repeat contributions before nonlinear F1; it is distinct
from a confidence interval directly around mean-of-run Q. No unseen-generalization
claim is made. No individual test outputs were opened to explain the regression.

| Split | Metric | Baseline mean | v1 mean | Delta |
|---|---|---:|---:|---:|
| train | F1 A | 0.620047 | 0.614719 | -0.005328 |
| train | F1 B | 0.885714 | 0.885714 | +0.000000 |
| train | Hit@5 A | 0.416667 | 0.500000 | +0.083333 |
| test | F1 A | 0.750000 | 0.555556 | -0.194444 |
| test | F1 B | 0.885714 | 0.657143 | -0.228571 |
| test | Hit@5 A | 0.333333 | 0.466667 | +0.133333 |

### Per-repeat secondary metrics

| Split | Repeat | Valid | Fallback neutral | Contradiction→entailment | Tokens | Case mean/p95 ms | API wait s |
|---|---:|---:|---:|---:|---:|---|---:|
| train | 1 | 36/36 | 0 | 6 | 663,435 | 6477.739/9975.631 | 184.204 |
| train | 2 | 36/36 | 0 | 6 | 663,301 | 5778.263/7523.660 | 163.609 |
| train | 3 | 36/36 | 0 | 6 | 663,301 | 5899.133/7440.949 | 160.037 |
| train | 4 | 36/36 | 0 | 6 | 663,301 | 5695.448/7506.238 | 161.938 |
| train | 5 | 36/36 | 0 | 6 | 663,301 | 5905.483/7466.562 | 163.502 |
| test | 1 | 18/18 | 0 | 5 | 429,288 | 6872.204/10080.712 | 99.954 |
| test | 2 | 18/18 | 0 | 5 | 429,315 | 6028.362/8169.955 | 85.462 |
| test | 3 | 18/18 | 0 | 5 | 429,315 | 6281.317/8004.691 | 88.564 |
| test | 4 | 18/18 | 0 | 5 | 429,315 | 5660.365/7626.420 | 83.320 |
| test | 5 | 18/18 | 0 | 5 | 429,315 | 6248.159/10031.051 | 88.981 |

| Split | Secondary metric mean | Baseline | v1 | Delta |
|---|---|---:|---:|---:|
| train | valid | 36.000 | 36.000 | +0.000 |
| train | fallback_neutral | 0.000 | 0.000 | +0.000 |
| train | contradiction_entailment | 5.800 | 6.000 | +0.200 |
| train | tokens | 641810.000 | 663327.800 | +21517.800 |
| train | case_mean_ms | 5780.930 | 5951.213 | +170.283 |
| train | case_p95_ms | 8556.796 | 7982.608 | -574.188 |
| train | API_wait_ms | 168990.870 | 166658.023 | -2332.847 |
| test | valid | 18.000 | 18.000 | +0.000 |
| test | fallback_neutral | 0.000 | 0.000 | +0.000 |
| test | contradiction_entailment | 3.000 | 5.000 | +2.000 |
| test | tokens | 425868.000 | 429309.600 | +3441.600 |
| test | case_mean_ms | 6065.183 | 6218.081 | +152.898 |
| test | case_p95_ms | 8310.811 | 8782.566 | +471.755 |
| test | API_wait_ms | 89378.586 | 89256.076 | -122.510 |

| Repeat | POST | Tokens | Command s | API wait s |
|---|---:|---:|---:|---:|
| 1 | 163 | 1,092,723 | 368.580 | 284.158 |
| 2 | 163 | 1,092,616 | 324.274 | 249.071 |
| 3 | 163 | 1,092,616 | 335.737 | 248.601 |
| 4 | 163 | 1,092,616 | 317.967 | 245.258 |
| 5 | 163 | 1,092,616 | 333.645 | 252.483 |

Total815 POST, **5,463,187 tokens**, **1680.203s** summed run duration.
Token increase vs five baselines5,338,390 is **124,797 (+2.338%)**.
Baseline r4 command start is missing, so a5-run baseline command-duration mean
cannot be reported as a like-for-like comparison. Case wall/API wait above are
measured secondary metrics, not proof of prompt-caused latency changes or the
official non-LLM relative processing-time score.

**Decision: reject v1 under both rules.** Test F1 A/B and train F1 A regress;
test fails both safety thresholds on every repeat. Hit@5 improves but cannot
substitute for required Q gains and qualification. Validity/fallback remain stable;
tokens increase. Production stays at v0. Candidate1 evaluated;1 nonimproving
round; do not automatically start v2. Need STOP approval for next round/scale.
No adopted prompt change to production, no model/tool/harness change.

All metrics are aggregate records. Raw outputs/transcripts/logs stay ignored
under output/cscs. No raw output committed.

## v2 candidate: six fictional GOOD/BAD pairs, evaluated and rejected

Basev0, notv1. SYSTEM alone gains6 short GOOD/BAD judgment pairs covering
negation, exception, condition, exact quantities, recommendation direction and
speaker attribution. Each alternative has a short reason; toy objects/actions
were newly invented and do not quote/paraphrase dev54. No real institutions,
votes, names or case facts. v1 final-verification policy is not included.
Prompt files committed BEFORE evaluation at459a139. Normalized word8-gram
check on all54 approved cases:0 overlaps; context maximum65522/66000 bytes.
Artifacts: prompts/v2-system.txt, v2-added.txt, v2.patch, v2.json,v2-overlap.json.

Five fresh source-only workspaces, production prompt unchanged. Only predict.py
SYSTEM differs; machine audit confirms all supplied user messages/pages/IDs
match baseline. Official evaluator/adapter/split/models unchanged. Exact jobs
output/cscs/prompt-C-v2-r1..r5, exclusive timestamps, all5 exit0, valid54/54,
fallback neutral0, usage known, no API retry/fence clearing.

After r1 successfully completed, the local reporting helper had a model-name
KeyError caused by a broad version-string substitution. No transport/model
configuration was affected. Completion/exit0/usage/fences were verified; r1
was not repeated. Only not-yet-started r2..r5 ran after the display fix.

### Per-repeat primary metrics

| Split | Repeat | Q | F1 A | F1 B | Hit@5 A | A/B gates |
|---|---:|---:|---:|---:|---:|---|
| train | 1 | 0.767488 | 0.657143 | 0.885714 | 0.500000 | pass/pass |
| train | 2 | 0.767488 | 0.657143 | 0.885714 | 0.500000 | pass/pass |
| train | 3 | 0.767488 | 0.657143 | 0.885714 | 0.500000 | pass/pass |
| train | 4 | 0.767488 | 0.657143 | 0.885714 | 0.500000 | pass/pass |
| train | 5 | 0.767488 | 0.657143 | 0.885714 | 0.500000 | pass/pass |
| test | 1 | 0.649425 | 0.555556 | 0.750000 | 0.333333 | FAIL/pass |
| test | 2 | 0.649425 | 0.555556 | 0.750000 | 0.333333 | FAIL/pass |
| test | 3 | 0.649425 | 0.555556 | 0.750000 | 0.333333 | FAIL/pass |
| test | 4 | 0.649425 | 0.555556 | 0.750000 | 0.333333 | FAIL/pass |
| test | 5 | 0.649425 | 0.555556 | 0.750000 | 0.333333 | FAIL/pass |

| Split | Baseline Q mean | v2 Q mean | Gain | Baseline noise | Literal | Strict | Paired group delta95 |
|---|---:|---:|---:|---:|---|---|---|
| train | 0.748300 | 0.767488 | +0.019188 | 0.017051 | FAIL | FAIL | [-0.019379, 0.079156] |
| test | 0.815517 | 0.649425 | -0.166092 | 0.000000 | FAIL | FAIL | [-0.301737, 0.000000] |

Literal: gain>=0.02 AND gain>noise width on BOTH splits. Train gain0.019188
exceeds temporal noise0.017051 but falls short of0.02; do not round it up.
Test gain is negative. Strict reference train threshold0.037051/test0.020000
also fails. Test A fails0.60 in all5 repeats; B meets0.75 exactly.
Candidate Q SD0 on both sides is observed repeat stability, not proof of zero
noise. Paired group bootstrap20,000 samples seed20261016 pools5 repeat
contributions before nonlinear F1; it is not unseen-generalization evidence.

| Split | Metric | Baseline mean | v2 mean | Delta |
|---|---|---:|---:|---:|
| train | F1 A | 0.620047 | 0.657143 | +0.037096 |
| train | F1 B | 0.885714 | 0.885714 | +0.000000 |
| train | Hit@5 A | 0.416667 | 0.500000 | +0.083333 |
| test | F1 A | 0.750000 | 0.555556 | -0.194444 |
| test | F1 B | 0.885714 | 0.750000 | -0.135714 |
| test | Hit@5 A | 0.333333 | 0.333333 | +0.000000 |

### Per-repeat secondary metrics

| Split | Repeat | Valid | Fallback neutral | Contradiction→entailment | Tokens | Case mean/p95 ms | API wait s |
|---|---:|---:|---:|---:|---:|---|---:|
| train | 1 | 36/36 | 0 | 6 | 679,528 | 6581.916/9394.719 | 191.944 |
| train | 2 | 36/36 | 0 | 6 | 679,528 | 5775.220/7566.613 | 169.063 |
| train | 3 | 36/36 | 0 | 6 | 679,528 | 5744.411/7779.449 | 169.110 |
| train | 4 | 36/36 | 0 | 6 | 679,528 | 5993.426/7547.080 | 174.234 |
| train | 5 | 36/36 | 0 | 6 | 679,528 | 5807.257/7629.536 | 171.430 |
| test | 1 | 18/18 | 0 | 5 | 433,154 | 6635.607/11624.858 | 100.469 |
| test | 2 | 18/18 | 0 | 5 | 433,154 | 5613.370/7161.300 | 81.870 |
| test | 3 | 18/18 | 0 | 5 | 433,154 | 5871.815/7578.949 | 83.711 |
| test | 4 | 18/18 | 0 | 5 | 433,154 | 5702.528/7040.863 | 81.733 |
| test | 5 | 18/18 | 0 | 5 | 433,154 | 6107.341/8465.386 | 92.707 |

| Split | Secondary metric mean | Baseline | v2 | Delta |
|---|---|---:|---:|---:|
| train | valid | 36.000 | 36.000 | +0.000 |
| train | fallback_neutral | 0.000 | 0.000 | +0.000 |
| train | contradiction_entailment | 5.800 | 6.000 | +0.200 |
| train | tokens | 641810.000 | 679528.000 | +37718.000 |
| train | case_mean_ms | 5780.930 | 5980.446 | +199.516 |
| train | case_p95_ms | 8556.796 | 7983.479 | -573.317 |
| train | API_wait_ms | 168990.870 | 175156.266 | +6165.396 |
| test | valid | 18.000 | 18.000 | +0.000 |
| test | fallback_neutral | 0.000 | 0.000 | +0.000 |
| test | contradiction_entailment | 3.000 | 5.000 | +2.000 |
| test | tokens | 425868.000 | 433154.000 | +7286.000 |
| test | case_mean_ms | 6065.183 | 5986.132 | -79.051 |
| test | case_p95_ms | 8310.811 | 8374.271 | +63.460 |
| test | API_wait_ms | 89378.586 | 88097.917 | -1280.669 |

| Repeat | POST | Tokens | Command s | API wait s |
|---|---:|---:|---:|---:|
| 1 | 162 | 1,112,682 | 364.983 | 292.413 |
| 2 | 162 | 1,112,682 | 317.058 | 250.933 |
| 3 | 162 | 1,112,682 | 317.883 | 252.821 |
| 4 | 162 | 1,112,682 | 328.001 | 255.967 |
| 5 | 162 | 1,112,682 | 329.765 | 264.138 |

Total810 POST,**5,563,410 tokens**,**1657.689s** summed command time.
Tokens vs baseline5,338,390: **+225,020 (+4.215%)**.
No schema repairs needed in v2. Time comparisons above are observations, not
prompt-caused latency claims or official non-LLM processing-time scores.

**Decision: rejectv2 under both interpretations; production staysv0.**
Train label/evidence improve but Q gain misses minimum; test labels regress,
Hit@5 unchanged; tokens rise. No threshold relaxation or score-based re-split.
Two consecutive nonimproving rounds now trigger eval-hillclimb stall STOP.
No candidate3 made or evaluated. Next phase is only the user-queued read-only
post-v2 research, then separately authorized no-API runbook work.
Raw outputs/transcripts/logs remain ignored; no raw outputs committed.
