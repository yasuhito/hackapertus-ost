# Predeclared general hypotheses for the approved window

These are general instruction-design alternatives, not fitted to test scores.
Use train evidence or independent interface/semantic reasoning for selection.
All preserve uncertain-source guards, model roles, tools and output behavior.

- v5: Align the SYSTEM output sentence with the existing submit tool's label/candidate_ids contract instead of asking for the overridden raw evidence/span_id JSON. Existing tool reminder already overrides it, so no improvement is assumed.
- Simplify the introductory SYSTEM wording while keeping NEUTRAL_GUARD and PARAPHRASE_GUARD verbatim. Remove redundant imperatives rather than add more cautions.
- Separate a source's attributed report from the truth of the reported proposition. Speaker assertions and different speakers' positions are not interchangeable; do not add dataset entities/examples.
- Cross-language semantic normalization: privately align source/claim propositions in a common language while retaining original-language evidence IDs. No output translations or external knowledge.
- Focus evidence selection on the exact relationship that determined the label, with co-reference resolved from supplied neighboring spans. Avoid blanket requests for extra citations or inventing attribution.
- Distinguish a claim's assertive content from evaluative framing without assuming all advocacy sentences support one stance. Preserve explicit negation, conditions and real uncertainty.

Do not turn these into retries of v1/v3/v4. No disagreement quota, test-topic exceptions, seed selection, grader changes or model/tool changes. Quality gate rejection alone permits the next distinct candidate; execution/usage uncertainty stops the whole window.
