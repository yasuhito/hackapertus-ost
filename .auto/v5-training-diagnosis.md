# v5 TRAIN diagnosis - saved outputs only

## Coverage and frozen boundaries

Loaded `evals/c-system-prompt/split.json` first (date-balanced-v2, seed20261016): 36 TRAIN IDs, 18/task. Every individual saved record was opened only after its fixture/manifest ID was verified TRAIN. Inspected TRAIN-filtered fixtures, frozen manifests, canonical predictions, case SDK events and actual submit responses in `output/cscs/prompt-C-v5-r1..5`; no individual TEST records, protected holdout, `.auto/prompt.md` or `.auto/log.jsonl` were inspected. No network, model calls, experiment/grader execution, git commands, tests or application/infrastructure edits. This file contains no raw claims/passages/transcripts.

SYSTEM file hash verified `06c89db1756d54d04cc5f1650b855acda2e2986d4c0c84943d2e54866383313c`; every saved frozen system starts with that exact SYSTEM, followed by the fixed 192-character runner reminder. Its combined hash differs legitimately. Protocol: Apertus-v1.5-70B authoritative nonthinking parent, actual Apertus-v1.5-8B package child, Pi1.1.0/subagents0.19.0; only SYSTEM mutable (`docs/prompt-eval-log.md:5–10,178–197`). Official adapter pins evaluator commit5e6957729b77a126006049305ad1ef241211a5b4 (`evals/c-system-prompt/grader.py:10–29`). Inspected the existing local checkout's `evaluate.py:35–50,69–74,151–162`: NFKC/dehyphenation, partial-ratio>=90, first five quotes, normalized length<=5000; evidence scoring is independent of predicted label. Recomputed matches with those operations, not by running the evaluator. No fresh git verification of the external checkout was attempted.

## Complete inventory

IDs below abbreviate `ost-dev54-`; indexes are zero-based manifest/case-file indexes. E/N/C = entailment/neutral/contradiction. Fixture citations are `evals/c-system-prompt/cases.jsonl` line numbers; only verified TRAIN expectations were used.

| TRAIN case / index / fixture line | Expected→submitted | Evidence-surrogate result |
|---|---|---|
|0117-A /01 /2|E→C|miss, page16|
|1117-A /05 /6|C→E|miss, page56|
|1316-A /11 /12|C→E|miss, pages47/48|
|0073-A /19 /20|E→C|hit, page52|
|0240-A /25 /26|E→C|hit, page62|
|1306-A /29 /30|C→E|hit, page18|
|1412-A /17 /18|C→C|miss, page16|
|1142-A /23 /24|C→C|miss, pages59/60|
|0346-A /31 /32|E→E|miss, pages48/50|

All six classification failures are A: 6/18 A, 0/18 B, 6/36 overall. The six evidence misses are among 12 nonneutral A references; remaining hits are 0475-A/index13, 0092-A/37, 1140-A/41 plus the three table hits. All references exist. Per repeat: Q=.827586, F1A=.666667, F1B=1, HitA=6/12; valid36/36, fallback0. All labels and hit/miss memberships remain identical over five repeats (180 TRAIN observations). Evidence is not entirely identical: correctly neutral 0835-A/index33 changes pages36→36/37 in r5 without changing scored metrics.

## Visible clusters, not internal reasoning

Evidence locator for each row: `prompt-C-v5-r{1..5}/manifest.json:frozen[index]`, `70b-{index}-case.json:sdk.events`, and `70b-{index}-{child,parent}-{number}.json:response.choices[0].message.tool_calls`. All six wrong decisions have native calls and package-child activity, not scraped text.

* **Conditional/negation polarity:** 0117-A and correctly classified 1412-A use the same page16 offset980–2164 anchor and submit C despite opposite reference-expected propositions. The available page discusses automatic termination and includes nearby negation. This supports a scope/polarity problem, but cannot establish whether attribution or conditional wording drove it.
* **Numeric direction:** 1316-A submits E with page47 offsets889–1707 and page48 offsets1096–2043. Available pages describe an increase, whereas verified expectation requires C for reversed direction. Selected chunks contain related numeric/eligibility material; broad source relevance does not license the submitted relation.
* **Missing decisive anchor:** 1117-A selects page56 offsets867–1516, omitting the age limit present earlier on that page; 1306-A selects page18 offsets1198–1694, containing transitional material rather than the exclusion earlier on the page. Their E calls conflict with verified C metadata and available full-page context. Evidence selection and semantic comparison are competing explanations, not separable causal proofs.
* **Attribution/source proposition:** 0073-A's page52 offsets1143–1956 anchor omits the decisive percentage appearing elsewhere on the restored page; the full page overlaps the paired committee reference but the parent/child both submit C against expected E. This is a relevant-page hit, not proof the selected chunk supports the label. In 0240-A, page62 offsets1045–2231 actually includes the resource-denial proposition; repaired child submits E, then parent submits C with the identical anchor. That is an observed harmful override, not inferred hidden disagreement.

The parent accepts the child's final submitted wrong label in five failures; 0240-A is the exception. All selected IDs are supplied, licensed source anchors; no unknown-ID/nonverbatim-source diagnostic appeared. Structural validity does not establish semantic support (`track_2a/src/submission.py:65–81`).

## Repairs and overlaps

Three TRAIN cases/repeat have diagnostics: 0117-A and 0240-A child duplicates, then unique-ID repairs; 1140-B/index40 twice submits valid native JSON with C and empty IDs. The latter violates actual supporting-span requirements (`track_2a/src/source_spans.py:77–78`), mapped by lowercase-error handling to INVALID_TOOL_JSON (`track_2a/dev/format/run_comparison.py:346–363`), not malformed JSON. Parent supplies valid evidence and the correct C. No accepted child recommendation should be inferred there.

Sets per repeat: label failures L=6, evidence misses H=6, diagnostic cases R=3; L∩H=3, L∩R=2, H∩R=1, triple=1. Repairs therefore do not explain all failures. 0346-A parent removes two child anchors without label change; 0073-B removes one. These actual calls demonstrate evidence editing, not hidden reasoning.

## Reference coverage and visibility limits

For **every** miss, no nonempty supplied full page reaches90 against its estimated reference. Thus no alternative legal page selection can turn these six into hits under the frozen full-page restoration contract (`track_2a/src/source_spans.py:99–109`). Four cases (0117/1412/1316/1142) also lack any supplied chunk reaching90. Two have matching chunks but not matching full pages: 1117 best chunk90.52 versus submitted page89.49; 0346 best chunk99.57 versus submitted pages at most79.91. Coverage/extraction/fuzzy-reference granularity can explain all six surrogate misses; they are **not six demonstrated model evidence errors**. These calculations neither revise scoring nor establish official overall truth.

Frozen intended context is fully inspectable; source selection blanks excluded pages (`track_2a/src/predict.py:66–82`), and span chunking preserves provided characters. Intended child receives the same user string, no inherited parent context (`track_2a/dev/format/package-child.mjs:43,53–54`). SDK responses retain hashes, not complete outbound request bodies; prompt_text is null. Actual token-by-token child input and attention are therefore unverified; no truncation cause is established.

Offline discriminators: map paired-reference coverage to excluded versus provided source locations without exposing fixtures; compare decisive proposition positions against selected anchors and restoration; audit negative/conditional/numeric scope separately from attribution. These are evidence checks, not candidate prompts or benchmark-specific policy. Known exhausted variants (including dedup/paircheck) are not recommendations. The owner approved the improvement plan after these previous batches; concrete next-round scale/window and execution-tool activation are still to be established before model calls.

## Independent offline verification

The parent separately enumerated every supplied TRAIN Task A candidate ID through the actual `source_spans.restore()` and the pinned evaluator's `quote_matches(...,90,5000)`, including citation-context closure and restoration validity. Result: 36 TRAIN cases, six classification failures, 12 nonneutral A references, six actual v5 hits, and at most six achievable hits under any legal restored citation. No TEST records were analyzed and no model calls were made. This confirms a frozen TRAIN evidence-surrogate ceiling of0.50; it does not justify changing references, matching thresholds, extraction, or an official-generalization claim.
