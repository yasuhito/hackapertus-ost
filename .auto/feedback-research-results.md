# Feedback reliability research results

PUBLIC60 is exposed development data, not independent validation. All original canonical outputs, including neutral decoder fallbacks, were graded unchanged. No case selection, label repair, threshold adjustment, or favorable-repeat selection occurred.

| Measurement | Final fallbacks /300 | Mean Q | F1A | F1B | HitA |
|---|---:|---:|---:|---:|---:|
| Historical original v5 | 7 | .8051187036988255 | .7009478538890304 | .9167303284950343 | .30 |
| H1 precise feedback | 10 | .7974809973486178 | .6850012732365673 | .9179949874686717 | .30 |
| H2 native conditional | 300 | .16666666666666669 | .16666666666666666 | .16666666666666666 | 0 |

Both candidates failed the fixed safeguards and primary objective. The historical reference was imported once, without new baseline inference or grading. Research retention is not deployment. The independently correct H1 diagnostic fix remains in checkpoint b3e1cb1; do not claim a measured reliability benefit. H2 production and current test changes were automatically reverted after run28.

## H1

Five complete repeats each had2 fallbacks. Known new usage:940 calls,8923286 tokens; command wall2161.205576955108 seconds, total case wall2096.3107303201687 seconds. MeanQ was below the fixed .8029455012419827 floor. Final failed-case aggregate structures were five booklet instances with22 candidate IDs/15 nonempty pages and five reference instances with4 IDs/1 page. The failure was not absence of candidate IDs in the source. Failed records contained30 SUPPORTING_SPAN_REQUIRED diagnostic events. No gold was read for this structural inspection.

Protocol SHA: 9afd74206ae8e035142f20b9c22ef2dd87f8fcf527d406f4b29b61f0ce7b4335.

## H2

The native submit declaration previously allowed nonneutral empty candidate IDs although the existing assembler rejects them. H2 added exactly the formal condition `label == 1 OR len(candidate_ids) >= 1` to Python and SDK projections. Neutral empty and nonempty IDs remained legal. Fictional exhaustive tests and an independent installed TypeBox compiler verified that no previously assembler-accepted tested tuple was excluded. Local acceptance, SYSTEM, descriptions, source extraction, IDs and caps stayed unchanged.

Generation1 was offline only. Generation2 repaired obsolete current wire-test assertions before inference;284 tests passed, with only2 prohibited historical fixtures deselected. Both generation freezes remain immutable. Exactly one live H2 batch ran, using generation2.

All five repeats had60 fallbacks and zero accepted final outputs. Known new usage:1160 calls,10948145 tokens; command wall2575.971901664976 seconds, total case wall2506.5206676239613 seconds. No API-error frames occurred. HTTP completion is not evidence that the native schema was honored.

Aggregate inspection of recorded response argument keys, without labels, claim text, IDs or gold:

| Role | Submit argument shape | Count |
|---|---|---:|
| Child | candidate_ids and label | 305 |
| Parent | label only | 440 |
| Parent | candidate_ids only | 60 |
| Parent | Unparseable JSON | 55 |

All55 unparseable parent responses ended with finish_reason=length. There were500 TOOL_SCHEMA,55 INVALID_TOOL_JSON and5 DUPLICATE_ID diagnostic events. Every parseable parent submit contained only one conditional-branch property, despite the root declaration requiring both. This is consistent with a branch-scope incompatibility in generation or interpretation. These observations do not identify whether the model or provider's constrained-decoding implementation caused it. Do not claim a specific server implementation defect without a fictional provider-level reproduction.

A mock SDK projection and a standards-level schema check did not predict actual parent behavior. No child recommendation was substituted for an invalid parent submission; doing so would change the original assembly policy.

Protocol SHA: 14ab68a6ac22e39b16a7cef3eb3b8759d80c545754d3d51d3ccbf345280c5600. Complete artifacts: output/cscs/public60-feedback-h2-g2-r1..5 and public60-feedback-h2-g2-analysis.json.

## Post-rollback verification

The restored current Root passed161 tests in49.75 seconds with `-Werror::ResourceWarning`; exactly2 prohibited historical fixtures were deselected. No non-.auto source modifications remain. Frozen H2 workspaces still preserve the measured candidate, while current production projections are back to the simple H1 checkpoint.

## Stop boundary

Do not retry H1, tune its wording, retry H2 with alternate schema spelling, raise completion caps, substitute child answers, lower safeguards, or reuse remaining slots to seek favorable noise. No authorized distinct source-contract hypothesis remains. Any future work requires a separately approved provider-compatibility investigation on fictional inputs before proposing another benchmark protocol. Keep old controls, workspaces, jobs and STOP records unchanged. PUBLIC60 cannot become unseen confirmation by being renamed.
