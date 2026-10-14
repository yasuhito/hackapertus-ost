# Next prompt round from adopted v5

## Completed diagnosis

Read `.auto/v5-training-diagnosis.md` for verified TRAIN-only evidence. Six stable classification failures affect Task A; Task B has none. Five wrong final labels agree with the child; one is a harmful parent override. Repair errors overlap only two label failures. Deduplication and non-neutral output-pairing policies have now completed evaluation and failed quality gates; they are not unresolved backlog ideas.

Independent enumeration through actual citation restoration and the pinned official matching function confirms that TRAIN Hit@5 is already at its frozen achievable ceiling:6/12. Prompt changes cannot improve that TRAIN evidence surrogate with current supplied pages/restoration/references. Keep the metric and report non-regression; do not alter references or claim its misses are all model mistakes.

## Next bounded experiment design

1. Prepare two independent SYSTEM-only candidates from the exact adopted v5 hash. No examples, dataset names, case IDs, gold facts, or discarded additions.
2. Candidate A hypothesis: classify against all supplied source spans before choosing citation anchors. Missing decisive anchors in visible TRAIN decisions motivate a comparison-order experiment, not a claim that the hidden reasoning used that order. This differs from v9's added context-preservation policy for selected evidence and v1's final check of already-selected spans.
3. Candidate B hypothesis: move the existing semantic safeguards before the unchanged tool/citation instructions, preserving every instruction verbatim. Test presentation order rather than adding another caution or shortening the introduction. This is independent of A and differs from v6's broad shortening. Preserve full guards and submit contract; check exact block/text preservation offline.
4. Compare candidates using only the frozen36 TRAIN cases, five repeats, one configuration. A train-only execution path is needed because the current runner hardcodes54 cases. Add only research-runner case selection/count handling; preserve original54-case defaults and test the protocol before freezing it. No extraction/tool/model/grader/fixture changes.
5. New target is TRAIN Q gain versus saved v5, with F1A>=.60/B>=.75 each repeat, gain>=.02 and above conservative train temporal noise. Report paired uncertainty, canonical validity/fallbacks, TRAIN evidence non-regression, parent/child/repair usage and latency. Do not keep a candidate merely for formatting or cost savings.
6. Register candidate order, exact text/hashes, scale and a90-minute candidate-start window/120-minute finish window before inference. No initialization until experiment tools are active; changed TRAIN-only workload needs one new configuration header. Import saved TRAIN reference without new baseline inference, then two distinct candidates with at most one completed quality batch each. The proposed transport-only retry budget below needs approval at activation. Stop if both fail; no cosmetic retries.
7. Select using TRAIN only. Never inspect or mine individual internal TEST records, and do not repeatedly gate candidate selection on TEST aggregates in this new round.
8. Before adoption, freeze a genuinely unused, independently labeled validation set and evaluate saved-v5 SYSTEM versus the selected finalist under the same protocol once. Its location/provenance/scale require owner input or a separately approved public-data preparation step. The existing exposed18-case internal TEST is not an unseen holdout. Protected competition holdout remains off limits.

## Operational boundary

Preserve original STOP/inflight records and all completed/partial outputs. Proposed approval scope: after HTTP504 only, wait60seconds and start the identical entire candidate batch under a fresh attempt ID, at most two additional attempts per candidate, still bounded by the candidate-start cutoff. Never resume a failed job or reuse completed prefixes. Maximum six candidate execution attempts plus one read-only reference import; at most two completed quality batches. Test this handling offline and freeze it before inference. Other execution/unknown-error types stop the round. Record every failed attempt and unknown failed-request usage separately; completed-batch usage excludes prior failed attempts and is not total session cost. No completed quality-failure retry, favorable-repeat selection, or fence removal.

Researcher/reviewer agents may help diagnose or review offline; they do not change the evaluated parent/child configuration. Product-level subagent restructuring is deferred to a separate experiment if this prompt round does not improve classification. Adopted application v5, original sibling, push and deployment remain unchanged.

Current status: diagnosis and plan written; no new model calls. Next human input is experiment-mode activation with this bounded scope, plus validation-set provenance before the final check.
