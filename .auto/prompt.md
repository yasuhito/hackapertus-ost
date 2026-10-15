# Autoresearch: generic submit-repair feedback

## Current user-approved HTTP500 policy

The user approved bounded HTTP500 retries for future runs. Use the separate retry-aware provider driver and its fresh protocol, documented in `.auto/provider-schema-empty-retry-plan.md`. The user subsequently set maximum5 total attempts per logical request (initial attempt plus4 retries), with2s/4s/8s/16s waits; only HTTP500 is retryable. Preserve each attempt and enforce the60s total logical deadline, phase and charged-budget limits. Failed-attempt usage stays unknown, with conservative reservations kept separate from measured token subtotals. This does not relax successful-response validation or retry other HTTP/transport/usage errors.

The retry driver has offline regression coverage, including fifth-attempt success and exhaustion without a sixth attempt; no live retry run has been executed or prepared. Future entrypoints are `bash .auto/measure.sh --provider-schema-empty-retry-prepare` and `bash .auto/measure.sh --provider-schema-empty-retry`. Freeze the new protocol before execution. Existing stopped jobs, prefixes, controls and no-retry entrypoints remain unchanged. Historical no-retry clauses below continue to describe their original frozen protocols; they are not the policy for this new retry-aware driver. No production or PUBLIC60 changes are authorized by the retry policy alone.

## Completed experiment boundary

H1 and H2 each completed five live repeats and FAILED. H1 had10 vs7 original fallbacks and meanQ below its fixed safeguard. H2 had300 fallbacks/zero accepted, F1A/F1B .16666666666666666 and HitA0. H2 was reverted; the independently correct H1 diagnostic fix remains without a measured reliability claim. See `.auto/feedback-research-results.md`.

H2's actual parent responses contained440 label-only objects,60 IDs-only objects and55 unparseable/truncated submits; all305 child submits contained both keys. There were no HTTP error frames. Standards-level and mocked schema checks did not establish real provider behavior. Do not retry either completed hypothesis, change wording/schema spelling/caps, substitute child recommendations, or alter guards. No authorized distinct source-contract hypothesis remains. STOP rather than manufacture an iteration. New provider-level work on fictional inputs requires separate approval and a fresh protocol. The sections below preserve the prospective H2 specification, not permission to rerun it.

## Objective and approved scope

Owner approved the generic missing-support feedback fix and now requested autoresearch to test it. Reduce answer-format fallbacks of unchanged v5 using the precise, source-contract feedback already tested. This is NOT a retry of rejected v16. Keep v5 SYSTEM, models, source extraction, labels, IDs, assembly acceptance, role structure, completion/request caps, cases, expected labels, and original official scorer unchanged.

PUBLIC60 has already been evaluated and its failure logs inspected. Treat it as an exposed DEVELOPMENT benchmark, never unseen validation or evidence of competition holdout performance. Do not inspect gold to choose changes, add case-specific rules, alter references/thresholds after results, omit failures, or rerun a completed candidate to seek favorable noise.

H1 completed once and FAILED: precise feedback produced10 vs7 fallbacks and Q .7974809973486178, below .8029455012419827. Do not retry H1 or vary its wording. Keep its independently correct diagnostic behavior; do not claim measured reliability benefit.

H2 is a different source-contract hypothesis, not a repeat: the current native tool schema permits label0/2 with zero candidate IDs even though the unchanged assembler rejects that combination. Expose the existing non-neutral-support relationship in native parameters via a formal conditional, without changing the v5 SYSTEM or prose, label meanings, tool names/argument keys, caps or acceptance rules. Neutral may still have empty OR nonempty IDs as the original assembler allows. Do not introduce a neutral-empty-only restriction. Prove on fictional inputs that no previously accepted assembler input is excluded. Prospective payloads must match Python and SDK projections exactly. Provider support is unconfirmed; any transport rejection stops without retry or bypass. Freeze a separate H2 protocol and five fresh jobs before inference. Retain the same historical original-v5 reference and quality safeguards; all H1 artifacts remain immutable.

Additional hypotheses require a demonstrable generic source-contract defect reproduced with fictional tests; do not vary wording speculatively or tune on validation answers. Stop rather than fabricate another iteration if no authorized useful hypothesis remains; zero fallbacks is the primary floor.

## Workload and metrics

Same immutable 30 source rows, paired A/B PUBLIC60 inputs, five complete repeats. Completion bundle output/validation/v16-public-v2-completion and existing case/gold/PDF/source hashes must remain unchanged. All 60 actual canonical outputs, including legal neutral fallbacks, are officially graded without omission, relabeling or synthetic penalties.

Primary: format_fallbacks, lower is better, total final decoder fallbacks across all 300 answers.

Reference: the five actually completed ORIGINAL v5 repeats from approved PUBLIC60 continuation, including original r1 exactly once. Known total fallbacks 7, accepted293/300, Q .8051187036988255, noise .0021732024568427814, mean HitA .30. A read-only verified reference checkpoint may import these measured observations; mark command duration as import time, not inference time. Reference API usage941 calls/8950166 tokens is historical observation, not new candidate cost. Do not generate the reference again merely to chase a cleaner baseline.

Candidate: five NEW exclusive jobs using fixed v5 feedback. No automatic model retries or prefix reuse. Finish collection after decoder failures; abort/fence transport errors, unknown usage, budget/deadline failure or storage uncertainty. Preserve failed identities permanently.

Backpressure preregistered BEFORE new candidate inference: full 60 canonical answers per repeat, correct IDs and original assembly schema; all usage known and source/runtime/protocol unchanged; each repeat F1A>=.60 and F1B>=.75; mean Q >= original reference Q minus its measured conservative noise; mean HitA >= .30. These are safeguards for a FORMAT-reliability objective, not the old instruction-order gain>=.02 gate. Do not reinterpret the earlier v16 failure as passing. Allow nonzero candidate fallbacks to be measured honestly; keep/discard depends on primary improvement only after safeguards pass. Report all classification, evidence, validity, per-repeat fallbacks, API calls, token usage and latency regressions.

No significance claim from a small count change. No favorable-repeat selection. Keep means research retention, not independent confirmation or deployment.

## Execution

Use separate feedback-research controller/protocol, measure.sh entry points, and check-context modes. Reuse original Strategy-C SDK/ledger/assembler and official grader. Freeze both the historical-reference binding and new source/runtime/input/feedback before candidate inference. Do not rewrite old controllers, archived workspaces, jobs, phases, STOP/inflight records or controls.

Required runtimes: /tmp/hackapertus-ost-contract/.venv/bin/python; Pi1.1.0 SDK and child0.19.0 as in existing controllers; official evaluator commit5e6957729b77a126006049305ad1ef241211a5b4 under /tmp/ost-official-evaluator-3U4yO9. Parent70B/child8B, temperature0, output256, parent<=3/child<=2, repair1, request60sec/socket45sec/case300sec, 300 POST/job and declared reservation budget78720000, input byte guard240000 with native token usage checks unchanged. Each five-job phase has actual90minute budget with existing bounded in-progress case allowance.

Use run_experiment via mandatory .auto/measure.sh and immediately log_experiment with parsed exact primary/secondary metrics and ASI. Initialize format_fallbacks once because objective changed from classification gain; never import unavailable crash-zero observations as references. Failed/unknown metrics use explicit unavailable sentinels and explanations, never fabricated success. Protect the already owner-approved engineering fix and unrelated changes via the measured-reference checkpoint before candidate runs, because failed log operations revert non-.auto changes.

## Files in scope

Current generic implementation track_2a/dev/format/run_comparison.py and fictional regression tests. H1's accurate feedback stays unchanged. H2 may additionally align its native schemas() and SDK sdk.ts nativeTools() parameter projections with the existing supporting-ID acceptance condition, and add matching fictional/schema tests. No other SDK API or role behavior changes. New .auto feedback-research controller/tests/report/dispatcher branches and this playbook. Historical prompt/playbook copies are in .auto/protocol-archive.

No changes to production v5 SYSTEM, source_spans.py, submission.py, predict.py, official grader or evaluator, SDK package files, existing role definitions, tool names/argument keys/local acceptance, source span schemas, data fixtures, old protocols and outputs. Only the explicitly preregistered H2 native parameter conditional may differ from H1's tool projection. No gold-based repairs. No private competition set access, push, merge or deployment.

## Existing evidence

Diagnosis across1884 model responses: no malformed JSON, no truncated completions. Final19 failures ended with missing supporting IDs; four duplicate-ID violations occurred earlier. Generic INVALID_TOOL_JSON feedback hid the actual validation reason. Current patch forwards only strict label0/2 with empty IDs to the existing submit handler, which still rejects and returns precise fixed feedback. All other strict rejection gates remain. 162 tests passed/2skipped; 19 cached failures remain failures with the same response bodies. Real model benefit has not yet been measured. Do not claim fictional provider repair success as real model evidence.
