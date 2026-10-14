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

## v5: evaluated, selected, adopted in the independent clone

On 2026-10-14 the owner approved adopting v5 in
`hackapertus-ost-autoresearch`; the original sibling and remote are unchanged.
The only production source edit replaces SYSTEM's raw JSON output instruction
with the existing submit tool's exact `label`/`candidate_ids` contract. No tools,
models, FINAL_VERIFICATION, extraction, quotes, transport, split or grader edits.
No examples. Exact evaluated SYSTEM SHA256:
`06c89db1756d54d04cc5f1650b855acda2e2986d4c0c84943d2e54866383313c`.

| Split | Baseline mean Q | v5 mean Q | Gain | v5 F1 A | v5 F1 B | Local Hit@5 baseline / v5 |
|---|---:|---:|---:|---:|---:|---|
| train | 0.748300 | 0.827586 | +0.079286 | 0.666667 | 1.000000 | 0.416667 / 0.500000 |
| test | 0.815517 | 0.885714 | +0.070197 | 0.885714 | 0.885714 | 0.333333 / 0.333333 |

Fixed54 x5 x1 completed, validity54/54 and fallback0 on every repeat. Both
literal/strict label gain rules and per-repeat F1 gates pass. Local Hit@5 uses
estimated paired references: it is a surrogate, not the official overall
score. Test evidence is unchanged. This is the same exposed internal dev split;
selection across candidates is not evidence of unseen generalization.

Secondary regression was reported before owner approval: tokens5,338,390 ->
5,506,663 (+3.1521%); requests820 ->835; repair-window calls10 ->25. v5 role
usage totals3,542,448 parent and1,964,215 child tokens;199,600 repair-window tokens
are a subset, not additional usage or decoded-payload schema-repair proof.
Command duration sum1660.326s, API wait sum1283.780s; missing baseline r4 start
prevents a like-for-like baseline full-duration comparison.

The approved continuation evaluated v5..v10 and stopped at six new candidates
and eight tool records. v5 is retained in commit532a724 as a research candidate;
v6/v7/v8/v9 failed gates, v10 passed baseline gates but was inferior to v5 and
was discarded. Local source adoption is a subsequent owner-approved edit, not
automatic tool keep adoption. Raw results remain ignored; no push or deployment.

Offline regression checks: production SYSTEM exactly matches frozen v5 hash;
91 tests pass including synthetic real parent/child SDK and canonical pipeline
checks, using the same pinned Pi1.1.0/child package environment. No new model
inference was needed for adoption.
