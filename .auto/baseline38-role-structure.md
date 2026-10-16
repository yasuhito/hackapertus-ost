# Baseline38: descriptive parent/child structure, no gold comparison

Read-only analysis of completed DEVELOPMENT60 current-v5 baseline r1..r5. No model calls, official regrading, expected/gold access, case-specific exception or source/prompt change. Only model-visible native submit arguments, accepted parent SDK recommendation, input/page context for existing strict assembler validation and ledger metadata were selected; no hidden reasoning analyzed. This is descriptive context for future architecture, not an accuracy result or causal anchoring test.

For each case, reconstruct the child's last structurally legal non-length-truncated submit via the unchanged submission.assemble_tool(inputcase,pages,zero metrics) validator. Compare numeric label with the parent's accepted submit. IDs/provenance legality is not semantic correctness. Cases without a valid child submit are unavailable, not neutral/incorrect and not silently dropped from the baseline's official scoring.

| Repeat | A valid child / agreement | B valid child / agreement | Child unavailable | Child repair calls | Parent repair calls |
|---|---:|---:|---:|---:|---:|
|1|29 /28|29 /26|2|7|0|
|2|29 /28|29 /26|2|6|1|
|3|29 /28|29 /26|2|7|0|
|4|29 /28|29 /26|2|6|0|
|5|29 /28|29 /26|2|6|0|

Across290 structurally comparable predictions, parent and child agree270times(93.10%). Twenty disagreements are all numeric child0->parent2: oneA andthreeB perrepeat. These are repeated observations on60inputs, not290independentcases. No inference about which side is correct follows without gold, nor whether agreement reflects copying, shared inputs/weights, correct convergence or shared mistakes. No per-case claims/IDs were retained in this note.

Ten child-unavailable observations occur across300canonical baseline answers; parent still produced accepted outputs in all300 (from the already completed baseline integrity result). This does NOT establish that removing the NLI helper globally is harmless. It only shows the current workflow can finish some cases without its valid recommendation.

Physical accounting reconciles:332child calls =300initial+32repairs;601parent =600normal two-call paths+1repair; total933knownHTTP200. A guaranteed second reviewer call ON TOP of ordinaryNLI +two parent calls already costs5x60=300beforeanyrepairs/retries. Baseline's6-7childrepair calls perrepeat leave no margin for that additive design. Replacing rather than adding the NLI helper with a first evidence channel permits an expected four-call path, but remains a genuinely different untested architecture and may lose useful NLI recommendations. Source-conditioned second checking is selection-dependent, not statistically independent.

Fixed baseline five-repeat Qvalues:0.7297113604282389,0.7291197444715114,0.7297113604282389,0.7291197444715114,0.7291197444715114. Mean0.7293563908542025; original conservative2*sqrt(2)*stdev/sqrt(5) noise0.00040988355824821425. Nominal candidate meanQ must reach0.7493563908542025 for the fixed.02gain AND pass every other gate, assessed without rounding. Noise across repeats is not generalization uncertainty across source claims/dates.
