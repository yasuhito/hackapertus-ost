# v16 task-routed instruction order: TRAIN result

Owner approved one candidate, TRAIN36x5, fixed scoring, stop before final validation. Full fresh attempt1 completed; no HTTP504 or retries. TaskA used exactv15SYSTEM, TaskB exactv5SYSTEM, selected solely by structured booklet/reference input type. No case/gold/label/claim routing or new semantic text. Adopted application remains v5; routing lives only in isolated research source copies.

| Metric | Saved v5 TRAIN | v16 TRAIN | Delta |
|---|---:|---:|---:|
| Q |0.8275862068965517|0.8553170966964071|+0.0277308897998554|
| F1 A |0.6666666666666666|0.7202797202797203|+0.0536130536130537|
| F1 B |1|1|0|
| Estimated-reference Hit A |0.50|0.50|0|

Every repeat had the same scores,36/36 canonical validity and zero fallbacks. Mandatory literal gain>=.02 and >conservative temporal noise.017051, per-repeat F1A>=.60/B>=.75, and evidence non-regression all pass. The stricter supplemental gain>=noise+.02=.037051 does NOT pass. Grouped paired delta95 is[0,0.09725906277630425], includes zero, and pools repeat rows before nonlinear F1 rather than forming a confidence interval directly around mean-of-repeat Q.

Decision: keep as a research candidate, not adoption or unseen validation. Routing was chosen after observing TRAIN task-specific behavior in v15, so this is adaptive TRAIN selection. Fresh inference was performed rather than reusing or composing saved prediction files. Current internal TEST remains exposed; no TEST/final-validation calls or individual outputs were used. TRAIN evidence surrogate remains at frozen reachable ceiling6/12, not an evidence improvement or official overall-score claim.

Complete-batch parent tokens2,154,058/360calls and child1,215,970/195calls,total3,370,028/555calls. Repair-window143,800tokens/15calls is a subset, not an additional role or decodedrepairreason. Token delta versus savedTRAIN is-207, effectively unchanged. APIwait1074.343161s versus840.274996s,+234.068165s; case mean increased1173.322898ms. Command duration1312.346356s; saved54 baseline lacks a comparableTRAIN-only command measurement. Latency changes are observed secondary regressions, not proven prompt causation or official relative-time score changes.

v16 bundle hash:d61868e705aacb3fc69e09485ce9b0f215d3f90a672605638380fecf8aa25ec0.
Frozen route control:e9c38425ff68adeb45e124da921306cc95f3e5fe8ea1546593acf37897396bbb.
Tool record18 imported savedreference and checkpointed controls;19 retained completed v16 research result. Candidate artifacts are in evals/c-system-prompt/prompts/v16* and immutable ignored output/cscs/candidate-archive/v16. Jobs are output/cscs/prompt-C-v16-a1-r1..5. Historical controls/fences remain intact.

Stop now, before final verification. No new candidates, adoption, push, deployment or sibling changes. A later v5-versus-v16 confirmation requires genuinely unused independently labeled validation inputs with provenance and explicit scope approval; competition holdout stays off limits. Unused attempt slots only cover504 failures and do not authorize further prompt hypotheses.
