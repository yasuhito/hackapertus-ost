# Missing-evaluation inventory (read-only source review)

As of the requested overnight window through `2026-10-16T06:00 JST` (epoch `1792098000`): **no still-outstanding, eligible transient-failure comparison was identified. Do not create work or rerun anything on this inventory alone.** This is a status reconciliation, not authorization to execute.

| Original status / identity | Classification | Result / disposition |
|---|---|---|
| #11 `prompt-C-v12-r4`, #12 `prompt-C-v13-r1` | Already completed later | Permanent STOP files retain HTTP504 (`RUN_FAILED_NO_AUTOMATIC_RESUME`). Ideas/current result summaries bind later identical retries as #13 and #14; both completed and were rejected on quality. Do not compare the STOP sentinel as data or rerun the rejected candidates. |
| #20/#21 | Setup failures, later corrected | Not model-evaluation results; later frozen PUBLIC setup/comparison produced completed #22/#24 baseline and #25 v16 candidate. #22's initial baseline was 59/60 due to original zero-fallback gate; approved completion #24 is the actual five-repeat baseline. #23 is a phase fence, not inference. Comparison complete; v16 rejected. Keep datasets/comparisons separate. |
| #29/#30 | Publication failure, then recovered | All 12 captures were already complete; read-only #30 recovered metric3 with no new calls. Not missing model results. |
| #33 | Incomplete transient, but not outstanding | First 70B control returned HTTP500; primary/full usage unavailable and STOP/inflight retained. Fresh, retry-aware run #34 completed all 12 requests, all HTTP200; fictional metric is 0/6 specialization vs 4/6 control. It did not yield a production NLI result and does not authorize resuming #33. No further comparable missing result is established. |
| #35 | Deterministic provider incompatibility, not capacity | HTTP400 `Grammar error: Unimplemented keys: ["uniqueItems"]` on first candidate; batch metrics unavailable. Do not retry or recommend unsupported variants; 0 sentinel is not data. |
| #27/#28/#37 | Completed quality failures | All five repeats completed; not transient-resume candidates. Do not retry merely to reverse quality decisions. |
| Pre-autoresearch v1-v3 | Aggregate-only historical records | `docs/prompt-eval-log.md` provides completed aggregate v1 and baseline comparisons; no specific incomplete transient job or unmeasured comparison was identified in the reviewed aggregates. No individual cases/results were inspected. |

There is therefore **no candidate requiring an exact saved prompt/code/protocol SHA, control-row set, or baseline-binding proposal for a fresh frozen rerun**. Existing approved broad retry policy does not waive old permanent STOPs or quality decisions. Missing/failed sentinels remain unavailable, never zero-valued observations.

Sources reviewed: `.auto/ideas.md`, the relevant `.auto/*results*.md` and summary records, `docs/prompt-eval-log.md`, and status-only `output/cscs/*/STOP.json`. The permanent STOPs for #11/#12 contain HTTP504; #33/#35 contain `terminal_unavailable`. No raw claims, individual evaluation cases, model argument bodies, protected holdout material, `.auto/prompt.md`, or `.auto/log.jsonl` were read. No calls, tests, grading, or source edits were made.
