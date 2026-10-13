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

## C role variant: evidence-only 8B child (rejected)

Explicit owner approval released the prior contract STOP for one role variant, dev54 54 cases x5. Production and default C remain v0. Implementation commit `28ab042616cb1d263f4f9de1a95db3dd693aef7f`; patch SHA256 `289e5d72a694f14739ecea17112103426599f7459972695d975df10057cbb4ac`. Only four archived role files change in isolated source-only workspaces. No examples added; approved54 8-gram overlap0 (not a semantic nonparaphrase proof). Offline validation:59 eval tests and242 track tests passed,1 protected test deselected.

Fixed parent `swiss-ai/Apertus-v1.5-70B`, child `swiss-ai/Apertus-v1.5-8B`, Pi1.1.0/pi-subagents0.19.0. Child submit permits only candidate_ids, strict uniqueness/membership/max5/additional-field rejection. Source restoration returns label-free original evidence. Parent receives original source/claim and supplies its label. Tool names/count, parent schema, all caps, data and scoring unchanged. HTTP projection keeps the existing compatibility omissions.

Fixed split `95c3468b1a088f3fad336136136c4069fd47ecaa`, official evaluator `5e6957729b77a126006049305ad1ef241211a5b4`. Comparison requires explicit variant and CLI-only flags; exact pinned historical v0 source maps are checked. No blanket role-file allowance. Historical dotted r4 remains read-only and its missing command time remains null. TEST individual outputs/transcripts were not opened by humans; aggregate machine scoring only. No holdout.

| Split | v0 Q mean | Role Q mean | Gain | v0 noise | Role Q SD | Role noise | Literal / strict |
|---|---:|---:|---:|---:|---:|---:|---|
| train | 0.748299976 | 0.579899794 | -0.168400182 | 0.017051044 | 0.011598820 | 0.014671476 | reject / reject |
| test | 0.815517241 | 0.529118774 | -0.286398467 | 0.000000000 | 0.000000000 | 0.000000000 | reject / reject |

Literal rule: each split gain >=0.02 and >baseline noise. Strict reference: each gain >=noise+0.02. Neither passes; train and test A<0.60/B<0.75 in every repetition. Child-label-free qualification passes but cannot override Q/safety.

| Split | Repeat | F1 A | F1 B | Q | Hit@5 | strict accepted | fallback neutral | C->E |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| train | 1 | 0.511111111 | 0.642857143 | 0.574712644 | 0.500000000 | 35/36 | 1 | 4 |
| train | 2 | 0.511111111 | 0.696581197 | 0.600648394 | 0.500000000 | 35/36 | 1 | 3 |
| train | 3 | 0.511111111 | 0.642857143 | 0.574712644 | 0.500000000 | 35/36 | 1 | 4 |
| train | 4 | 0.511111111 | 0.642857143 | 0.574712644 | 0.500000000 | 35/36 | 1 | 4 |
| train | 5 | 0.511111111 | 0.642857143 | 0.574712644 | 0.500000000 | 35/36 | 1 | 4 |
| test | 1 | 0.388888889 | 0.679365079 | 0.529118774 | 0.333333333 | 15/18 | 3 | 2 |
| test | 2 | 0.388888889 | 0.679365079 | 0.529118774 | 0.333333333 | 15/18 | 3 | 2 |
| test | 3 | 0.388888889 | 0.679365079 | 0.529118774 | 0.333333333 | 15/18 | 3 | 2 |
| test | 4 | 0.388888889 | 0.679365079 | 0.529118774 | 0.333333333 | 15/18 | 3 | 2 |
| test | 5 | 0.388888889 | 0.679365079 | 0.529118774 | 0.333333333 | 15/18 | 3 | 2 |

Strict tool acceptance50/54 each run (train35/36,test15/18), fallback4/run. Final official classification validity54/54: neutral fallback with valid integer label/name is valid under the official evaluator. Do not conflate strict acceptance with official label validity.

| Split | Secondary mean | v0 | Role | Delta |
|---|---|---:|---:|---:|
| train | valid | 36.000 | 35.000 | -1.000 |
| train | fallback_neutral | 0.000 | 1.000 | +1.000 |
| train | contradiction_entailment | 5.800 | 3.800 | -2.000 |
| train | tokens | 641810.000 | 694362.200 | +52552.200 |
| train | tokens_per_case | 17828.056 | 19287.839 | +1459.783 |
| train | tokens_per_case_p95 | 54274.000 | 54586.000 | +312.000 |
| train | API_wait_mean_ms | 4694.191 | 5271.865 | +577.674 |
| train | API_wait_p95_ms | 7446.093 | 8300.276 | +854.183 |
| train | case_mean_ms | 5780.930 | 6346.123 | +565.193 |
| train | case_p95_ms | 8556.796 | 9433.786 | +876.990 |
| train | API_wait_ms | 168990.870 | 189787.150 | +20796.279 |
| test | valid | 18.000 | 15.000 | -3.000 |
| test | fallback_neutral | 0.000 | 3.000 | +3.000 |
| test | contradiction_entailment | 3.000 | 2.000 | -1.000 |
| test | tokens | 425868.000 | 463324.200 | +37456.200 |
| test | tokens_per_case | 23659.333 | 25740.233 | +2080.900 |
| test | tokens_per_case_p95 | 60210.000 | 60772.000 | +562.000 |
| test | API_wait_mean_ms | 4965.477 | 6092.956 | +1127.479 |
| test | API_wait_p95_ms | 7086.429 | 10813.019 | +3726.590 |
| test | case_mean_ms | 6065.183 | 7208.478 | +1143.295 |
| test | case_p95_ms | 8310.811 | 11879.721 | +3568.909 |
| test | API_wait_ms | 89378.586 | 109673.200 | +20294.615 |

Train Hit@5 improves5/12 to6/12; test remains2/6. C->E mean drops5.8 to3.8(train) and3 to2(test), but overall labels, strict validity, token cost and latency regress. Timing is observational, not a causal latency claim or official non-LLM processing-time score.

| Repeat | POST | Tokens | Start UTC | End UTC | Command s | API wait s |
|---|---:|---:|---|---|---:|---:|
| 1 | 170 | 1,157,679 | 2026-10-13T07:52:44.325740+00:00 | 2026-10-13T07:59:02.821847+00:00 | 378.496 | 313.581 |
| 2 | 170 | 1,157,715 | 2026-10-13T07:59:02.825202+00:00 | 2026-10-13T08:05:37.474612+00:00 | 394.649 | 327.261 |
| 3 | 170 | 1,157,679 | 2026-10-13T08:05:37.475439+00:00 | 2026-10-13T08:11:56.946833+00:00 | 379.471 | 307.280 |
| 4 | 170 | 1,157,679 | 2026-10-13T08:11:56.952922+00:00 | 2026-10-13T08:17:56.257938+00:00 | 359.305 | 282.441 |
| 5 | 170 | 1,157,680 | 2026-10-13T08:17:56.262246+00:00 | 2026-10-13T08:23:18.783082+00:00 | 322.521 | 266.740 |

Total850 POST, **5,788,432 tokens**, **1834.442764s** command time. Tokens vs v0 5,338,390: +450,042 (+8.430295%). Each run parent114 calls/child56 (v0 parent108/child56). All jobs exit0/completed, per-job caps respected; no uncertainty, automatic retry, resume or fence clearing. Prior uncertain B fence untouched. API monetary cost unknown.

Raw child audit across all280 responses, including rejected repairs, counts **0 label fields,0 label text/class-value emissions,0 nonempty content/reasoning fields,0 unauthorized fields,0 malformed argument outputs**. Unique/known-ID failures are still strict validation failures and separately diagnosed. Baseline child label emissions280 were allowed by v0, not v0 protocol violations. A finite lexical check cannot prove absence of every implicit recommendation; observed raw child arguments have only candidate_ids.

Paired pooled group-bootstrap20,000/seed20261016 train delta95 [-0.35202183513321267, 0.05026726792660077]; mean-repeat delta95 [-0.35164210929931017, 0.05110162679330986].
Paired pooled group-bootstrap20,000/seed20261016 test delta95 [-0.5770114942528737, -0.030651340996168727]; mean-repeat delta95 [-0.5770114942528738, -0.030651340996168727].

Observed repeats and group-bootstrap uncertainty are different. Previously exposed internal split/booklet overlap is not unseen-generalization evidence. Raw outputs, model exchanges, detailed scored individual files and logs remain ignored.

Decision: **reject evidence-only-child under both rules; retain v0**. No production adoption, new variant, extra run or next improvement before the mandated log review and owner STOP decision.


### Mandatory agent-log review (complete)

Owner Takamiya's standing policy starts with this evaluation: after every evaluation, before proposing the next improvement, review both agents' exchanges/tool calls/evidence/labels. Individual details are TRAIN-only; TEST aggregate-only. Include the review in every STOP and never commit raw logs. The runbook records this policy.

All180 TRAIN case-repetitions were reviewed against matching v0/v2 TRAIN records. Across560 responses (375 parent,185 child), visible content/reasoning was empty; all185 raw child outputs have only candidate_ids and no label/class-value emissions, including rejected repairs. Source anchors and restored evidence match original TRAIN sources. Parent request messages were not persisted (payload hashes only); exact actual message bytes and independent internal reasoning are not observable. The offline SDK path and observed tool sequence establish protocol behavior, not cognitive independence.

Each run:0117-A child duplicate IDs rejected, deduplicated repair accepted.0557-A/0508-A parent contradiction with empty supporting IDs rejected, repaired outputs accepted but still incorrect.0835-B parent twice requests contradiction with empty IDs, both rejected by non-neutral-support requirement; final neutral is bridge-generated fallback, not a parent neutral decision, and happens to be gold-correct. The raw JSON is syntactically valid; existing INVALID_TOOL_JSON diagnostics misleadingly cover this semantic validation failure. No malformed JSON or child-label leak is inferred from that diagnostic. Across five runs:25 rejected TRAIN attempts,15 accepted repairs,5 failed repairs,175 accepted parent outputs/5 fallbacks. No repair limit was raised.

TRAIN correct counts22/23/22/22/22 of36, versus v0 28/27/27/27/27 and v2 28each.20 case-repetition improvements versus45 regressions. All36 child ID lists are repeat-stable; parent labels stable35/36 (1306-B varies), parent ID lists stable35/36 (0924-A varies). Final parent IDs match baseline21/36 and restored evidence26/36 each run, so the intervention changes evidence selection as well as removing child labels; their effects are not causally isolated. Unchanged-evidence improvements include0117-A/1316-A/0073-A; regressions include0508-A/0835-A. Remaining TRAIN errors include age-threshold mismatch, worship-place exceptions, attribution, and unrelated claims classified as contradiction. No individual TEST diagnosis was performed.

Detailed TRAIN review, source rationales, audit JSON and reproducible offline scripts remain in ignored output/cscs/role-C-evidence-only-train-review*. Raw model output/source quotations are not committed. No next experiment is proposed or started; wait at STATUS: SKILL-STOP.

## Single native-tool experiment: id-existence-check (offline implementation)

Owner authorized exactly one deterministic parent-only membership tool on v0 C.
Production/default paths and the child's label recommendation remain v0; the
rejected evidence-only-child patch is not applied. The separate hash-pinned
variant changes only three archived format sources, adding the forced order
subagent/check_candidate_ids/submit. Membership is not semantic support; final
IDs remain unconstrained by checked IDs and mismatch is logged. All models,
budgets, deadlines and validation caps are unchanged. Adding the check makes the
normal parent sequence three completions, so a failed final schema cannot obtain
a fourth repair request.

Offline synthetic actual Pi SDK/pinned runAgent tests exercise membership,
duplicates/unknown queries, strict arguments, role/order/repeat guards,
independent final label/IDs, unchanged source and compatibility wire schemas.
No live calls, key reads, installs, commits or pushes during implementation. A subsequent parent review found an excluded-test boundary violation; see the incident below. Do not claim that no protected data was read.
The portable recipe and exact schema/source/policy audits are in
`evals/c-system-prompt/README.md` and `variants/id-existence-check.*`.

Parent must verify the implementation commit before the approved54x5 live run.
After that run, mandatory full TRAIN log/evidence/label review precedes any next
proposal or STOP decision; TEST remains aggregate-only. No evaluation outcome,
quality gain, adoption or additional experiment is asserted here.

Verification: eval suite **79 passed**. The implementation agent's **243 passed** result included the forbidden `test_no_split_leakage` because its `-k 'not protected'` filter did not exclude that name. It is not a scope-compliant verification. Parent reran `track_2a -k 'not test_no_split_leakage'` with the pinned Pi package overrides: **242 passed,1 deselected**. An intermediate parent test invocation omitted those package overrides and failed; the failed log was preserved, then the configured offline invocation passed. No model requests were involved. `run_batch.py --variant id-existence-check --count 5
--prepare-only` prepared five54-case archives, **remote_calls0/credential_reads0**.
Automatic approved54 8-gram check: **overlapping_cases0**. Production three role
source hashes match the pinned base; package-child matches unchanged v0.
`git diff --check` passed. These are offline plumbing/regression results, not
live model accuracy, service compatibility, latency or quality measurements.

### Pre-live boundary incident: STOP, no model evaluation

Owner confirmed STOP-10 role split rejected; production/default C remain v0. During this new tool's implementation, two offline pytest invocations used `-k 'not protected'`, which does not exclude `test_no_split_leakage`. That existing test JSON-decodes train_cases.jsonl/dev_cases.jsonl, including the reserved date, and inspects date-set overlap and total row count. Thus protected data was read by the test despite the explicit exclusion. No protected-case prediction, grading, gold diagnosis, prompt selection or case text was output. This distinction does not excuse the boundary violation.

Parent identified the mistake before any live run and stopped launch. New tool live calls/tokens:0; candidate Q, safety and all model secondary metrics are unmeasured. Approved54x5 scale remains approved, but is not executed past this incident without owner direction. The original wrong test outputs remain preserved; no fence or evidence was deleted. README now uses the exact exclusion, and the new offline fixture links only the six approved-dev54 PDFs rather than all booklet files. Correctly scoped tests pass as above. No protected data was used to change the candidate.

Mandatory live TRAIN agent-log review is not claimed complete: there are no new live parent/child logs to review. Only synthetic actual-SDK membership/order/role/limit tests were reviewed; they are not Apertus quality evidence. No individual TEST transcript was inspected. A new STOP report records the incident, baseline table, unmeasured candidate metrics and continuation question. No additional tool, production change or model job was started.

A nonmutating code review found an additional offline defect: multiple check tool calls in one response, or an early out-of-order call, could poison a global counter and stop the legitimate first lookup. Two synthetic actual-SDK regressions were RED before repair. Raw attempts and admitted calls are now counted separately; extras remain visible and rejected, without blocking the legitimate one-time lookup. No source/cap/schema policy changed. GREEN validation: **81 eval tests passed;242 track tests passed,1 excluded** with the exact protected-test exclusion and pinned package overrides. Final patch SHA256 `8302ee66480c3ebacf635fe9549b9c3d3e245b1ed73b24b836eb295f7ff1952d`. Live launch remains stopped; these repairs do not authorize continuing past the boundary incident.

## Single-tool live result: id-existence-check (rejected)

Owner explicitly reviewed the pre-live boundary incident and authorized continuation with exact `-k 'not test_no_split_leakage'` exclusion. Approved54x5 completed once, no extra repetition/retry. Implementation/archive commit `06eee5d80418fe3c7109edced223c4d9c785649f`; patch SHA256 `8302ee66480c3ebacf635fe9549b9c3d3e245b1ed73b24b836eb295f7ff1952d`. Fresh exact jobs `output/cscs/tool-C-id-existence-r1` through `r5`; no renamed/reused identities. Production/default C remain v0.

Fixed parent `swiss-ai/Apertus-v1.5-70B`, child `swiss-ai/Apertus-v1.5-8B`, Pi1.1.0/pi-subagents0.19.0, nonthinking. Parent alone adds membership lookup; child keeps v0 label/IDs recommendation. No dedup/search/rulecheck/automatic correction. Caps/models/inputs/split/official scoring unchanged; explicit schema delta only adds the parent tool, unchanged submit/child schemas. Exact source/policy/frozen/schema audit passes; comparison explicitly requests variant and historical CLI-only allowance.

Split `95c3468b1a088f3fad336136136c4069fd47ecaa`, official evaluator `5e6957729b77a126006049305ad1ef241211a5b4`. Runtime input fixture unchanged; no holdout evaluated or further protected-test read in this phase. Prior incident remains documented, not erased. TEST individual outputs/transcripts not opened; aggregate machine scoring only. No key file read by agents, auth changes, sudo/force push/submission/publication.

| Split | v0 Q mean | Tool Q mean | Gain | Baseline noise | Tool Q SD | Tool noise | Literal / strict |
|---|---:|---:|---:|---:|---:|---:|---|
| train | 0.748299976 | 0.759049839 | 0.010749863 | 0.017051044 | 0.013577603 | 0.017174460 | reject / reject |
| test | 0.815517241 | 0.715900383 | -0.099616858 | 0.000000000 | 0.000000000 | 0.000000000 | reject / reject |

Literal requires both gains>=0.02 AND each >baseline noise. Strict reference requires each >=noise+0.02. Train gain .010749863 is below .02 and below .017051044 noise. Test gain is negative; B<.75 in all5 repetitions (A=.75 passes). Train A>=.60/B>=.75 each run. Tool structural compliance passes but cannot override gain/safety.

| Split | Repeat | F1 A | F1 B | Q | Hit@5 | strict accepted | fallback | C->E |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| train | 1 | 0.720279720 | 0.831168831 | 0.773812395 | 0.500000000 | 36/36 | 0 | 4 |
| train | 2 | 0.675324675 | 0.831168831 | 0.750559785 | 0.500000000 | 36/36 | 0 | 4 |
| train | 3 | 0.675324675 | 0.831168831 | 0.750559785 | 0.500000000 | 36/36 | 0 | 4 |
| train | 4 | 0.720279720 | 0.774603175 | 0.746504836 | 0.500000000 | 36/36 | 0 | 4 |
| train | 5 | 0.720279720 | 0.831168831 | 0.773812395 | 0.500000000 | 36/36 | 0 | 4 |
| test | 1 | 0.750000000 | 0.679365079 | 0.715900383 | 0.333333333 | 18/18 | 0 | 3 |
| test | 2 | 0.750000000 | 0.679365079 | 0.715900383 | 0.333333333 | 18/18 | 0 | 3 |
| test | 3 | 0.750000000 | 0.679365079 | 0.715900383 | 0.333333333 | 18/18 | 0 | 3 |
| test | 4 | 0.750000000 | 0.679365079 | 0.715900383 | 0.333333333 | 18/18 | 0 | 3 |
| test | 5 | 0.750000000 | 0.679365079 | 0.715900383 | 0.333333333 | 18/18 | 0 | 3 |

Strict submitted outputs54/54 and official label/name shape54/54 every run; fallback0. Train Hit5/12->6/12; test2/6 unchanged. Train C->E5.8->4, test3 unchanged. Train F1_A .620046620->.702297702 improves while F1_B .885714286->.819855700 worsens. Test F1_A .75 unchanged; F1_B .885714286->.679365079 regresses and fails safety.

| Split | Secondary mean | v0 | Tool | Delta |
|---|---|---:|---:|---:|
| train | valid | 36.000 | 36.000 | +0.000 |
| train | fallback_neutral | 0.000 | 0.000 | +0.000 |
| train | contradiction_entailment | 5.800 | 4.000 | -1.800 |
| train | tokens | 641810.000 | 880544.200 | +238734.200 |
| train | tokens_per_case | 17828.056 | 24459.561 | +6631.506 |
| train | tokens_per_case_p95 | 54274.000 | 73328.000 | +19054.000 |
| train | API_wait_mean_ms | 4694.191 | 9316.592 | +4622.401 |
| train | API_wait_p95_ms | 7446.093 | 15243.463 | +7797.370 |
| train | case_mean_ms | 5780.930 | 10529.488 | +4748.558 |
| train | case_p95_ms | 8556.796 | 16491.870 | +7935.074 |
| train | API_wait_ms | 168990.870 | 335397.313 | +166406.443 |
| test | valid | 18.000 | 18.000 | +0.000 |
| test | fallback_neutral | 0.000 | 0.000 | +0.000 |
| test | contradiction_entailment | 3.000 | 3.000 | +0.000 |
| test | tokens | 425868.000 | 573377.800 | +147509.800 |
| test | tokens_per_case | 23659.333 | 31854.322 | +8194.989 |
| test | tokens_per_case_p95 | 60210.000 | 80839.000 | +20629.000 |
| test | API_wait_mean_ms | 4965.477 | 9590.979 | +4625.502 |
| test | API_wait_p95_ms | 7086.429 | 15453.978 | +8367.549 |
| test | case_mean_ms | 6065.183 | 10834.450 | +4769.267 |
| test | case_p95_ms | 8310.811 | 16874.865 | +8564.054 |
| test | API_wait_ms | 89378.586 | 172637.616 | +83259.030 |

| Split | Repeat | Lookup calls/successful cases | Unknown ID query occurrences | Checked-vs-final list mismatch cases | Structural all |
|---|---:|---|---:|---:|---|
| train | 1 | 36/36 | 9 | 17 | True |
| train | 2 | 36/36 | 9 | 16 | True |
| train | 3 | 36/36 | 10 | 14 | True |
| train | 4 | 36/36 | 11 | 16 | True |
| train | 5 | 36/36 | 9 | 16 | True |
| test | 1 | 18/18 | 7 | 6 | True |
| test | 2 | 18/18 | 7 | 6 | True |
| test | 3 | 18/18 | 7 | 6 | True |
| test | 4 | 18/18 | 4 | 6 | True |
| test | 5 | 18/18 | 7 | 6 | True |

All270 cases execute exactly1 successful lookup in the fixed parent sequence. Ordered membership results independently match the frozen source candidate set. Unknown queried-ID occurrences80 (train48,test32); final list mismatch109/270 cases (train79/180,test30/90). A successful lookup can correctly return exists=false; it does not mean all queried IDs exist, nor establish semantic support. Final IDs are intentionally not forced to checked IDs; original strict submit validator remains. Child label emissions279 (train180,test99), allowed by v0; IDs-only child-label-free/extra-field counters are not this variant's protocol gates and must not be described as violations.

| Repeat | Parent / child POST | Total POST | Tokens | Start UTC | End UTC | Command s | API wait s |
|---|---|---:|---:|---|---|---:|---:|
| 1 | 162 / 56 | 218 | 1,455,515 | 2026-10-13T11:23:16.371843+00:00 | 2026-10-13T11:32:12.058233+00:00 | 535.686 | 459.780 |
| 2 | 162 / 55 | 217 | 1,447,590 | 2026-10-13T11:32:12.060810+00:00 | 2026-10-13T11:41:41.134317+00:00 | 569.074 | 488.527 |
| 3 | 162 / 56 | 218 | 1,455,526 | 2026-10-13T11:41:41.137658+00:00 | 2026-10-13T11:53:21.366993+00:00 | 700.229 | 621.757 |
| 4 | 162 / 56 | 218 | 1,455,542 | 2026-10-13T11:53:21.369384+00:00 | 2026-10-13T12:02:52.411060+00:00 | 571.042 | 495.613 |
| 5 | 162 / 56 | 218 | 1,455,437 | 2026-10-13T12:02:52.412731+00:00 | 2026-10-13T12:11:58.249934+00:00 | 545.837 | 474.498 |

Total1089 POST, **7,269,610 tokens**, **2921.868111s** command time (48.698min). Versus v0 5,338,390tokens: +1,931,220 (+36.176076%). Parent810 calls versus540baseline; child279 versus280. Child duplicate-ID schema repairs9 versus10baseline, no parent repair/fallback. Membership check raises ordinary parent requests to3, consuming its available repair slot; caps never raised.

All5 exit0/completed, usage known/consistent, reserves0/pending null/inflight absent, caps respected. No HTTP retry, rerun, resume or fence clearing. Prior uncertain B fence untouched. Financial cost unknown. Time increases are observational, not causal prompt timing or official non-LLM processing-time claims. Historical baseline r4 command start/time remains null.

Paired pooled group-bootstrap20,000/seed20261016 train delta95 [-0.08064978717938054, 0.10730832887296632]; mean-repeat delta95 [-0.08150480090588985, 0.10946907498631642].
Paired pooled group-bootstrap20,000/seed20261016 test delta95 [-0.3084291187739465, 0.0]; mean-repeat delta95 [-0.3084291187739465, 0.0].

Observed run noise differs from source-group/bootstrap case uncertainty. Previously exposed internal test/booklet overlap remains a limitation; no unseen-generalization claim. Raw outputs/transcripts/individual score files remain ignored.

Decision: **reject id-existence-check under both interpretations; retain v0**. No next tool or combined variant is created/evaluated. Mandatory TRAIN log review is recorded separately before owner STOP decision.


### Mandatory TRAIN agent-log review (complete)

All180 candidate TRAIN repetitions and180 matched v0 baseline repetitions were reviewed via exact-index parent/child responses, local tool inputs/results, final label/IDs, diagnostics and restored source evidence. No individual TEST records or frozen entries were decoded; TEST interpretation is aggregate-only. Detailed proof and reproducible read-only audit remain ignored at output/cscs/tool-C-id-existence-train-review.md and tool-C-id-existence-train-audit.json/.py. Raw logs/source quotations are not committed.

All180 TRAIN flows follow 70B subagent -> 8B submit ->70B membership check ->70B submit, with3parent/1child calls each. No TRAIN repair/fallback/truncation/rejected final submission. All neutral predictions are accepted parent submissions, not bridge placeholders. All48 nonexistent queried IDs were correctly flagged across22 case-repetitions; no nonexistent queried ID survives into final evidence. Checked/final list mismatch79cases includes57 without any unknown query. Five check lists contain duplicates, intentionally preserved; no empty check occurred. Final IDs and source evidence are valid and exactly restored, but membership is not semantic support.

TRAIN correct137/180 vsbaseline136/180:9 improvements (1142-A r2-r5,1316-A all5),8 regressions (0601-B r4,0924-A r2/r3,0924-B all5). Wrong stable labels persist on0073-A,0117-A,0240-A,1117-A/B,1306-A/B despite existing source IDs. Labels repeat-stable34/36; variable0601-B/0924-A. Ordered final IDs stable31/36; variable0073-B/0475-B/0508-B/0557-A/0826-A. Source review of0346-A observes fuller relevant pages; this is consistent with aggregate Hit improvement, but no claim is made that this case alone accounts for the measured increase. Some other TRAIN selections include unrelated evidence; valid membership cannot validate its relevance.

Child request hashes match baseline180/180; child arguments match177/180, with all child labels unchanged. Child v0 labels are allowed, not violations. Parent final labels match child157/180 and IDs118/180. No private reasoning or causal decision mechanism is recoverable: visible content empty/reasoning null, actual parent request messages not persisted, only hashes and response envelopes. Observable tool/result/label transitions and source correctness are reported, not cognitive independence or causal accuracy improvement from membership alone.

Decision confirmed after log review: reject this single-tool variant, retain v0. No next tool or combined variant is proposed/created/evaluated before owner STOP direction. Every future evaluation must repeat the TRAIN-only case review and TEST aggregate-only reporting.

All official aggregate secondary metrics (per-class precision/recall/F1/support, per-language F1/count, task accuracy, evidence counts, upstream usage means) and per-run operational/tool metrics are saved without individual outputs in evals/c-system-prompt/results/id-existence-check-aggregates.json. Upstream B threshold0.70 remains unchanged; adoption uses0.75. Output aggregate values are not a new scorer or altered adoption rule.
