# C prompt baseline: three real repeats

No prompt, tool, runner, model or split changes. Only approved development inputs.
Official evaluator commit: `5e6957729b77a126006049305ad1ef241211a5b4`.
Main classification objective: Q_label_norm; +0.02 minimum gain.
Second primary objective: Task A Hit@5 (20% of SA).

| Repeat | F1 A | F1 B | Q_label_norm | Hit@5 A | Valid | Fallback neutral | Gold contradiction→entailment | POST | Tokens | Mean/p95 ms | Command s |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 0.700000 | 0.885714 | 0.789655 | 7/18 | 54/54 | 0 | 8 | 164 | 1,067,678 | 5970.363/8606.353 | 330.254 |
| 2 | 0.657143 | 0.885714 | 0.767488 | 7/18 | 54/54 | 0 | 9 | 164 | 1,067,678 | 5588.618/7328.409 | 312.303 |
| 3 | 0.657143 | 0.885714 | 0.767488 | 7/18 | 54/54 | 0 | 9 | 164 | 1,067,678 | 5731.519/7786.033 | 319.675 |

All three pass A >=0.60 and safe B >=0.75. All plumbing counts zero:
API errors, timeouts, invalid/empty canonical responses, nonzero exits.
Each run includes two known duplicate-ID child repairs, not HTTP retries.
Parent: swiss-ai/Apertus-v1.5-70B; child: swiss-ai/Apertus-v1.5-8B;
nonthinking; Pi 1.1.0; pi-subagents 0.19.0; Node 26.10.0.
Production predict.py SHA-256: `39a22c77898835cfb54230b3ff109daac24d75bb1d9ce99fc1204042f76d5ead`.
Baseline r1/r2 source commit 6c2e08a; r3 source commit 88aa3e9.
Their production-source diff is empty; frozen manifest inputs are identical.
Fresh parent/child workspaces per trial; no scoring fixtures supplied to models.

## Noise and detectable difference

- Mean of run Q: **0.774877**.
- Run-to-run range: **0.022167**.
- Run SD: **0.012798**; mean SE: **0.007389**.
- Temporal t95 interval (3 repeats, df2): **[0.743084, 0.806670]**.
- Approximate temporal detectable difference `2 sqrt(2) SE_mean`:
  **0.020900**, slightly above +0.02.
- Case bootstrap 95% Q interval: **[0.641078, 0.881941]**;
  case SE **0.061323**.
- Conservative unpaired case-sampling detectable difference:
  **0.173448**.
- Hit@5 mean **7/18 = 0.388889**, run spread zero;
  case bootstrap 95% **[0.166667, 0.625000]**.

Seed 20261016, 20,000 bootstrap draws, 27 paired source-row A/B groups,
three repeat contributions averaged per case before pooling confusion counts.
The pooled nonlinear Q point is 0.775074, slightly
above the mean of three nonlinear run Q values. These are distinct aggregations.
The bootstrap uses pooled contributions; per-run scoring always uses the
unmodified official evaluator through the adapter.

**STOP: eval-hillclimb hillclimb §1 noise gate.** No split or candidate created.
Three repeats do not establish detectable +0.02 improvements on both train/test.
Do not interpret the unpaired case-sampling estimate as pure API randomness:
it measures sampling uncertainty, assumes independent runs for the difference,
and is conservative for paired candidates. Rows also share booklets/votes, so
this row-pair bootstrap may understate wider correlation. No actual paired
candidate difference can be estimated before running a candidate.

Propose approval for additional unchanged baseline repeats first, not automatic
execution. One additional 54-case repeat (~5-6 minutes, ~1.07m tokens expected)
would reduce the temporal point estimate below +0.02 if the observed SD remains
stable; four repeats alone do not establish reliable train/test sensitivity.
More independent development cases may be needed for sampling uncertainty;
this would require case-list/grader approval and must not use protected holdout.
Never silently loosen +0.02 or the both-splits criterion.

## Always-fail flags

11 cases fail every repeat (8 A, 3 B). Saved submit/tool transcripts were inspected:
all have accepted structured submissions, not infrastructure failures. Flags
include attribution/alignment, exception/condition scope, direction/quantity,
and recommendation polarity. They are hypotheses for later train-only analysis,
not proof of grader/case ambiguity. No examples or case wording added to prompt.

Stable failures: `ost-dev54-0117-A`, `ost-dev54-1117-B`, `ost-dev54-1117-A`, `ost-dev54-1316-A`, `ost-dev54-0073-A`, `ost-dev54-0240-A`, `ost-dev54-1306-B`, `ost-dev54-1306-A`, `ost-dev54-1295-B`, `ost-dev54-1295-A`, `ost-dev54-1486-A`.

## Per-case grades and local transcript links

| Case | r1 | r2 | r3 |
|---|---|---|---|
| ost-dev54-0117-B | [correct](../../output/cscs/format-C-r1/70b-00-case.json) | [correct](../../output/cscs/format-C-r2/70b-00-case.json) | [correct](../../output/cscs/format-C-r3/70b-00-case.json) |
| ost-dev54-0117-A | [wrong](../../output/cscs/format-C-r1/70b-01-case.json) | [wrong](../../output/cscs/format-C-r2/70b-01-case.json) | [wrong](../../output/cscs/format-C-r3/70b-01-case.json) |
| ost-dev54-0557-B | [correct](../../output/cscs/format-C-r1/70b-02-case.json) | [correct](../../output/cscs/format-C-r2/70b-02-case.json) | [correct](../../output/cscs/format-C-r3/70b-02-case.json) |
| ost-dev54-0557-A | [correct](../../output/cscs/format-C-r1/70b-03-case.json) | [correct](../../output/cscs/format-C-r2/70b-03-case.json) | [correct](../../output/cscs/format-C-r3/70b-03-case.json) |
| ost-dev54-1117-B | [wrong](../../output/cscs/format-C-r1/70b-04-case.json) | [wrong](../../output/cscs/format-C-r2/70b-04-case.json) | [wrong](../../output/cscs/format-C-r3/70b-04-case.json) |
| ost-dev54-1117-A | [wrong](../../output/cscs/format-C-r1/70b-05-case.json) | [wrong](../../output/cscs/format-C-r2/70b-05-case.json) | [wrong](../../output/cscs/format-C-r3/70b-05-case.json) |
| ost-dev54-0315-B | [correct](../../output/cscs/format-C-r1/70b-06-case.json) | [correct](../../output/cscs/format-C-r2/70b-06-case.json) | [correct](../../output/cscs/format-C-r3/70b-06-case.json) |
| ost-dev54-0315-A | [correct](../../output/cscs/format-C-r1/70b-07-case.json) | [correct](../../output/cscs/format-C-r2/70b-07-case.json) | [correct](../../output/cscs/format-C-r3/70b-07-case.json) |
| ost-dev54-0716-B | [correct](../../output/cscs/format-C-r1/70b-08-case.json) | [correct](../../output/cscs/format-C-r2/70b-08-case.json) | [correct](../../output/cscs/format-C-r3/70b-08-case.json) |
| ost-dev54-0716-A | [correct](../../output/cscs/format-C-r1/70b-09-case.json) | [correct](../../output/cscs/format-C-r2/70b-09-case.json) | [correct](../../output/cscs/format-C-r3/70b-09-case.json) |
| ost-dev54-1316-B | [correct](../../output/cscs/format-C-r1/70b-10-case.json) | [correct](../../output/cscs/format-C-r2/70b-10-case.json) | [correct](../../output/cscs/format-C-r3/70b-10-case.json) |
| ost-dev54-1316-A | [wrong](../../output/cscs/format-C-r1/70b-11-case.json) | [wrong](../../output/cscs/format-C-r2/70b-11-case.json) | [wrong](../../output/cscs/format-C-r3/70b-11-case.json) |
| ost-dev54-0475-B | [correct](../../output/cscs/format-C-r1/70b-12-case.json) | [correct](../../output/cscs/format-C-r2/70b-12-case.json) | [correct](../../output/cscs/format-C-r3/70b-12-case.json) |
| ost-dev54-0475-A | [correct](../../output/cscs/format-C-r1/70b-13-case.json) | [correct](../../output/cscs/format-C-r2/70b-13-case.json) | [correct](../../output/cscs/format-C-r3/70b-13-case.json) |
| ost-dev54-0830-B | [correct](../../output/cscs/format-C-r1/70b-14-case.json) | [correct](../../output/cscs/format-C-r2/70b-14-case.json) | [correct](../../output/cscs/format-C-r3/70b-14-case.json) |
| ost-dev54-0830-A | [correct](../../output/cscs/format-C-r1/70b-15-case.json) | [correct](../../output/cscs/format-C-r2/70b-15-case.json) | [correct](../../output/cscs/format-C-r3/70b-15-case.json) |
| ost-dev54-1412-B | [correct](../../output/cscs/format-C-r1/70b-16-case.json) | [correct](../../output/cscs/format-C-r2/70b-16-case.json) | [correct](../../output/cscs/format-C-r3/70b-16-case.json) |
| ost-dev54-1412-A | [correct](../../output/cscs/format-C-r1/70b-17-case.json) | [correct](../../output/cscs/format-C-r2/70b-17-case.json) | [correct](../../output/cscs/format-C-r3/70b-17-case.json) |
| ost-dev54-0073-B | [correct](../../output/cscs/format-C-r1/70b-18-case.json) | [correct](../../output/cscs/format-C-r2/70b-18-case.json) | [correct](../../output/cscs/format-C-r3/70b-18-case.json) |
| ost-dev54-0073-A | [wrong](../../output/cscs/format-C-r1/70b-19-case.json) | [wrong](../../output/cscs/format-C-r2/70b-19-case.json) | [wrong](../../output/cscs/format-C-r3/70b-19-case.json) |
| ost-dev54-0508-B | [correct](../../output/cscs/format-C-r1/70b-20-case.json) | [correct](../../output/cscs/format-C-r2/70b-20-case.json) | [correct](../../output/cscs/format-C-r3/70b-20-case.json) |
| ost-dev54-0508-A | [correct](../../output/cscs/format-C-r1/70b-21-case.json) | [correct](../../output/cscs/format-C-r2/70b-21-case.json) | [correct](../../output/cscs/format-C-r3/70b-21-case.json) |
| ost-dev54-1142-B | [correct](../../output/cscs/format-C-r1/70b-22-case.json) | [correct](../../output/cscs/format-C-r2/70b-22-case.json) | [correct](../../output/cscs/format-C-r3/70b-22-case.json) |
| ost-dev54-1142-A | [correct](../../output/cscs/format-C-r1/70b-23-case.json) | [wrong](../../output/cscs/format-C-r2/70b-23-case.json) | [wrong](../../output/cscs/format-C-r3/70b-23-case.json) |
| ost-dev54-0240-B | [correct](../../output/cscs/format-C-r1/70b-24-case.json) | [correct](../../output/cscs/format-C-r2/70b-24-case.json) | [correct](../../output/cscs/format-C-r3/70b-24-case.json) |
| ost-dev54-0240-A | [wrong](../../output/cscs/format-C-r1/70b-25-case.json) | [wrong](../../output/cscs/format-C-r2/70b-25-case.json) | [wrong](../../output/cscs/format-C-r3/70b-25-case.json) |
| ost-dev54-0826-B | [correct](../../output/cscs/format-C-r1/70b-26-case.json) | [correct](../../output/cscs/format-C-r2/70b-26-case.json) | [correct](../../output/cscs/format-C-r3/70b-26-case.json) |
| ost-dev54-0826-A | [correct](../../output/cscs/format-C-r1/70b-27-case.json) | [correct](../../output/cscs/format-C-r2/70b-27-case.json) | [correct](../../output/cscs/format-C-r3/70b-27-case.json) |
| ost-dev54-1306-B | [wrong](../../output/cscs/format-C-r1/70b-28-case.json) | [wrong](../../output/cscs/format-C-r2/70b-28-case.json) | [wrong](../../output/cscs/format-C-r3/70b-28-case.json) |
| ost-dev54-1306-A | [wrong](../../output/cscs/format-C-r1/70b-29-case.json) | [wrong](../../output/cscs/format-C-r2/70b-29-case.json) | [wrong](../../output/cscs/format-C-r3/70b-29-case.json) |
| ost-dev54-0346-B | [correct](../../output/cscs/format-C-r1/70b-30-case.json) | [correct](../../output/cscs/format-C-r2/70b-30-case.json) | [correct](../../output/cscs/format-C-r3/70b-30-case.json) |
| ost-dev54-0346-A | [correct](../../output/cscs/format-C-r1/70b-31-case.json) | [correct](../../output/cscs/format-C-r2/70b-31-case.json) | [correct](../../output/cscs/format-C-r3/70b-31-case.json) |
| ost-dev54-0835-B | [correct](../../output/cscs/format-C-r1/70b-32-case.json) | [correct](../../output/cscs/format-C-r2/70b-32-case.json) | [correct](../../output/cscs/format-C-r3/70b-32-case.json) |
| ost-dev54-0835-A | [correct](../../output/cscs/format-C-r1/70b-33-case.json) | [correct](../../output/cscs/format-C-r2/70b-33-case.json) | [correct](../../output/cscs/format-C-r3/70b-33-case.json) |
| ost-dev54-1387-B | [correct](../../output/cscs/format-C-r1/70b-34-case.json) | [correct](../../output/cscs/format-C-r2/70b-34-case.json) | [correct](../../output/cscs/format-C-r3/70b-34-case.json) |
| ost-dev54-1387-A | [correct](../../output/cscs/format-C-r1/70b-35-case.json) | [correct](../../output/cscs/format-C-r2/70b-35-case.json) | [correct](../../output/cscs/format-C-r3/70b-35-case.json) |
| ost-dev54-0092-B | [correct](../../output/cscs/format-C-r1/70b-36-case.json) | [correct](../../output/cscs/format-C-r2/70b-36-case.json) | [correct](../../output/cscs/format-C-r3/70b-36-case.json) |
| ost-dev54-0092-A | [correct](../../output/cscs/format-C-r1/70b-37-case.json) | [correct](../../output/cscs/format-C-r2/70b-37-case.json) | [correct](../../output/cscs/format-C-r3/70b-37-case.json) |
| ost-dev54-0601-B | [correct](../../output/cscs/format-C-r1/70b-38-case.json) | [correct](../../output/cscs/format-C-r2/70b-38-case.json) | [correct](../../output/cscs/format-C-r3/70b-38-case.json) |
| ost-dev54-0601-A | [correct](../../output/cscs/format-C-r1/70b-39-case.json) | [correct](../../output/cscs/format-C-r2/70b-39-case.json) | [correct](../../output/cscs/format-C-r3/70b-39-case.json) |
| ost-dev54-1140-B | [correct](../../output/cscs/format-C-r1/70b-40-case.json) | [correct](../../output/cscs/format-C-r2/70b-40-case.json) | [correct](../../output/cscs/format-C-r3/70b-40-case.json) |
| ost-dev54-1140-A | [correct](../../output/cscs/format-C-r1/70b-41-case.json) | [correct](../../output/cscs/format-C-r2/70b-41-case.json) | [correct](../../output/cscs/format-C-r3/70b-41-case.json) |
| ost-dev54-0302-B | [correct](../../output/cscs/format-C-r1/70b-42-case.json) | [correct](../../output/cscs/format-C-r2/70b-42-case.json) | [correct](../../output/cscs/format-C-r3/70b-42-case.json) |
| ost-dev54-0302-A | [correct](../../output/cscs/format-C-r1/70b-43-case.json) | [correct](../../output/cscs/format-C-r2/70b-43-case.json) | [correct](../../output/cscs/format-C-r3/70b-43-case.json) |
| ost-dev54-0816-B | [correct](../../output/cscs/format-C-r1/70b-44-case.json) | [correct](../../output/cscs/format-C-r2/70b-44-case.json) | [correct](../../output/cscs/format-C-r3/70b-44-case.json) |
| ost-dev54-0816-A | [correct](../../output/cscs/format-C-r1/70b-45-case.json) | [correct](../../output/cscs/format-C-r2/70b-45-case.json) | [correct](../../output/cscs/format-C-r3/70b-45-case.json) |
| ost-dev54-1295-B | [wrong](../../output/cscs/format-C-r1/70b-46-case.json) | [wrong](../../output/cscs/format-C-r2/70b-46-case.json) | [wrong](../../output/cscs/format-C-r3/70b-46-case.json) |
| ost-dev54-1295-A | [wrong](../../output/cscs/format-C-r1/70b-47-case.json) | [wrong](../../output/cscs/format-C-r2/70b-47-case.json) | [wrong](../../output/cscs/format-C-r3/70b-47-case.json) |
| ost-dev54-0347-B | [correct](../../output/cscs/format-C-r1/70b-48-case.json) | [correct](../../output/cscs/format-C-r2/70b-48-case.json) | [correct](../../output/cscs/format-C-r3/70b-48-case.json) |
| ost-dev54-0347-A | [correct](../../output/cscs/format-C-r1/70b-49-case.json) | [correct](../../output/cscs/format-C-r2/70b-49-case.json) | [correct](../../output/cscs/format-C-r3/70b-49-case.json) |
| ost-dev54-0924-B | [correct](../../output/cscs/format-C-r1/70b-50-case.json) | [correct](../../output/cscs/format-C-r2/70b-50-case.json) | [correct](../../output/cscs/format-C-r3/70b-50-case.json) |
| ost-dev54-0924-A | [correct](../../output/cscs/format-C-r1/70b-51-case.json) | [correct](../../output/cscs/format-C-r2/70b-51-case.json) | [correct](../../output/cscs/format-C-r3/70b-51-case.json) |
| ost-dev54-1486-B | [correct](../../output/cscs/format-C-r1/70b-52-case.json) | [correct](../../output/cscs/format-C-r2/70b-52-case.json) | [correct](../../output/cscs/format-C-r3/70b-52-case.json) |
| ost-dev54-1486-A | [wrong](../../output/cscs/format-C-r1/70b-53-case.json) | [wrong](../../output/cscs/format-C-r2/70b-53-case.json) | [wrong](../../output/cscs/format-C-r3/70b-53-case.json) |

Raw trial records and detailed local metrics stay ignored under output/. No true held-out generalization claim.
