# TRAIN-only v14/v15 round completed

Two predeclared independent candidates each completed36 TRAIN cases x5 repeats x1 configuration. No HTTP504, retries, TEST scoring, final-validation calls, adoption, push or sibling changes. Frozen source/control digest:3f3f98aa898f21d01b5db0ca56508632d6e1c6fad017e4c5133b1bb27102b9af.

| Candidate | TRAIN Q | Gain vs v5 | F1 A | F1 B | Hit A | Decision |
|---|---:|---:|---:|---:|---:|---|
| adopted v5 |0.8275862068965517|0|0.6666666666666666|1|0.50|retained|
| v14 classification before citation selection |0.7974439353749700|-0.0301422715215817|0.6083916083916084|1|0.50|checks_failed, gain regresses|
| v15 unchanged safeguards reordered |0.8283096214130697|0.0007234145165180|0.7202797202797203|0.9440559440559441|0.50|checks_failed, gain below.02/noise|

All repeats had canonical36/36 and zero fallback; F1 safety and evidence non-regression gates passed for both candidates. Both failed the predeclared overall TRAIN gain gate. v15's A improvement is offset by B regression; it is not an accepted overall improvement. Its grouped paired delta95[-0.08777429467084641,0.08333412277377791] includes0 and is not a confidence interval directly around mean-of-repeat Q. Current evidence surrogate remains at the frozen TRAIN reachable ceiling6/12.

v14 complete-batch parent/child tokens:2,177,171/1,228,750,555calls; repair-window15calls/144,745tokens is a subset. Command sum1176.862621s, APIwait934.508856s. Versus savedTRAIN reference:tokens+35,686 and APIwait+94.233860s.

v15 complete-batch parent/child tokens:2,154,021/1,215,970,555calls; repair-window15calls/143,800tokens is a subset. Command sum1168.402041s, APIwait928.039906s. Versus savedTRAIN reference:tokens-244 and APIwait+87.764910s. Tiny token reduction and latency variations do not establish prompt improvement or latency causation. No failed requests occurred in this round; these are complete-batch metrics, not cumulative historical session cost.

Records:tool runs15 saved-reference checkpoint,16 v14 rejection,17 v15 rejection. Immutable prompts and both attempt records/jobs remain in ignored output/cscs; adopted v5 SYSTEM hash06c89db1756d54d04cc5f1650b855acda2e2986d4c0c84943d2e54866383313c is unchanged. The approved two-candidate scope is complete. Four unused tool slots were reserved only for transport retries and do not authorize further hypotheses.

Stop before final verification as requested. No candidate qualified for independent validation. If the owner chooses another round, use a separately approved task/parent-child decomposition experiment rather than cosmetic prompt retries; characterize its model/tool/protocol tradeoffs first. Genuinely unused independently labeled validation data still requires provenance and approval, and protected competition holdout remains off limits.
