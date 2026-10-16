# Technical report: Multilingual NLI over Swiss Voting Booklets with Verbatim Evidence Restoration

- **Track:** Track 2A, OST
- **Event:** Online, deadline 2026-10-16
- **Team:** yasuhito (Yasuhito Takamiya)
- **Repository:** https://github.com/yasuhito/hackapertus-ost (submitted revision: latest commit on master)
- **Demo:** No demo is provided; the CLI in Reproducibility reproduces the results.

Full report (PDF, 6 pages plus references): `report/main.pdf`.

This is the submission version as of 2026-10-16. It covers the items of the official template [1]. All numbers in this report were measured on public data that we used during development. Performance on the organizers' private held-out data is unknown.

## 1. Summary

This project addresses HackApertus OST Track 2A [2]. The input is a Swiss federal voting booklet (PDF) or a short reference text, plus a claim written in German, French, or Italian. The system decides whether the claim follows from the source (0=entailment), whether the information is insufficient (1=neutral), or whether the claim contradicts the source (2=contradiction), and returns the source text that supports the decision.

The models are Apertus v1.5 70B and 8B [3, 4, 5]. The core design choice is that the model never writes quotations. A script extracts the PDF page by page, selects the pages of the target ballot item, and assigns IDs to spans of source text. The model returns only a label and IDs through one native tool call per case, and the script restores the source text and page numbers from the IDs. Task A, which reads the booklet, is answered by 70B; Task B, which has only the reference text, is answered by 8B. In Task A, the ballot item's pages are split into paragraphs of 200 to 700 characters, and only the top 8 paragraphs closest to the claim plus their neighbors are passed to the model. Paragraphs are ranked by fusing BM25 over an 8B translation of the claim with a local multilingual embedding, preferring paragraphs from the booklet section that the claim's opening points to. A non-neutral answer that still lacks evidence after a retry is answered once more using all pages of the ballot item.

On the morning of 2026-10-16 we found that the page selection of the previous version (v5) failed to pass the model the page containing the gold evidence in 36% of cases. The new version, which switched selection to a method based on the booklet's headings and added evidence completion (a two-stage setup with a 70B parent and an 8B child), beat v5 on Task A macro-F1 and on evidence hit rate on all of the development set (DEV60), the public set (PUBLIC60), and the confirmation set of 60 questions. We then found that in the new version's 420 cases the 70B parent's final answer always matched the 8B child's recommendation, so we moved to a configuration that drops the child and answers in a single call (R) (12:40 JST).

The production configuration as of 18:00 JST on 2026-10-16 is R with paragraph-level context, section preference, and full-page re-runs added. Averaged over the three question sets on the submission runtime, compared with R given all pages, Task A F1 rose from 0.881 to 0.910 and Hit@5 from 0.746 to 0.808, tokens fell from 10,939 to 7,137 per case, and time went from 3.7 to 4.0 seconds per case.

## 2. Architecture

Inference pipeline. The model returns only a label and span IDs; the script restores quotations and page numbers from the source.

- Input JSONL: ballot item name, claim, PDF or reference text.
- Page extraction with pypdf, then heading-based ballot item page selection (Task A).
- Task A: split into 200 to 700 character paragraphs; translate cross-language claims with 8B. Rank fusion of BM25, multilingual embedding, and section preference keeps the top 8 paragraphs and neighbors.
- Build spans and IDs, then one model makes one `submit` call (label and IDs). Booklet (Task A) goes to Apertus 70B, reference text (Task B) to Apertus 8B. Non-neutral without evidence: retry once, then re-run on all ballot item pages, then neutral.
- Restore source text and pages from IDs, then evidence completion (Task A, up to 5).
- Output JSONL: label, verbatim evidence, token counts, case processing time.

### PDF extraction and page selection

pypdf [9] converts the PDF to text page by page. Page numbers are physical PDF pages. In Task A, `vote_pages` in `document_selection.py` selects the ballot item's pages. Federal booklets print an ordinal heading such as `Erste Vorlage`, `Premier objet`, or `Primo oggetto` on the first page of each spread. A page on which exactly one such heading appears is assigned to that ballot item, and a page without a heading is assigned to the preceding heading page. Pages that list the headings of all items, such as the cover or table of contents, are not assigned to any item. The ordinal is chosen by word overlap between the item name and the opening words of the page; if the match score falls below 0.45, or the booklet has no headings (for example, a single-item booklet), all pages are passed. Unselected pages are replaced with empty strings, so page numbers stay physical and pages that were not passed cannot be returned as evidence.

### Paragraph narrowing (Task A)

The selected pages are split into paragraphs of roughly 200 to 700 characters at blank lines and sentence boundaries (`paragraphs` in `document_selection.py`). Each paragraph is a contiguous substring of the page text and never splits a word. If the claim's language differs from the booklet's, Apertus 8B [5] translates the claim into the booklet's language. This adds one short call, and its roughly 100 tokens are counted in the case's tokens.

Paragraphs are ranked by rank fusion of BM25 [10] over words and character 4-grams of the translation, BM25 over character 4-grams of the original claim, and cosine similarity of a static multilingual embedding. In addition, claim openings are classified into 5 types (summary, committee, Federal Council and Parliament, ballot text, if accepted), and booklet pages receive section labels (opening spread, details, committee arguments, Federal Council arguments, legal text). Because each page starts with a small table of contents, the last heading found in the first few lines becomes the page's section, and an unlabeled page inherits the label of the preceding page. Paragraphs from the section matching the claim type are placed first in the rank fusion. On 610 public rows, this raised the share of cases where the kept paragraphs include a gold paragraph that passes the scorer's matching from 0.972 to 0.982, and cut characters by 21%.

The embedding is model2vec's `potion-multilingual-128M` quantized to int8 (140 MB), and it runs on CPU with numpy only. The weights are bundled in the image (see Reproducibility), and local embeddings are allowed by the competition rules. We keep the top 8 paragraphs and the preceding and following paragraphs on the same page for each, merge adjacent paragraphs into one region, and pass them verbatim.

### Source spans and IDs

`source_spans.py` splits each page (or each region, when narrowed) into contiguous spans of at most 1200 characters, preferring paragraph or sentence boundaries. An ID consists of the physical page number, start and end character offsets, and the first 12 hex digits of the SHA-256 of the page text (for example, `p0012-o0000000-e0001187-<hash>`). In Task B the whole reference text is treated as one page. Task B processing is unchanged from before.

### Model calls (use of Apertus)

The submission runtime (`track_2a/dev/format/runtime.py`, pipeline R) uses native tool calls through the Pi 1.1.0 SDK [11]. Each case calls exactly one model, and the only tool provided is `submit`. There are no child sessions. Cases with a reference text (Task B) are answered by `swiss-ai/Apertus-v1.5-8B`, and booklet cases (Task A) by `swiss-ai/Apertus-v1.5-70B`. In the earlier configuration (pipeline C), the 70B parent launched an 8B child once through the `subagent` tool [12], and the parent called the final `submit` after seeing the child's recommendation. This configuration can still be selected with `PIPELINE`.

The arguments of `submit` are only the label (integer 0, 1, or 2) and `candidate_ids` (an enumeration of the case's span IDs, at most 5). The system prompt defines the 3 classes, explains how to handle negation, quantities, conditions, and speakers, tells the model to treat the source and claim as data rather than instructions, and to return only IDs. It also warns against confusing neutral with contradiction and explains how to treat cross-language paraphrases. No gold answer for any specific case is included in the prompt.

### Source restoration

`assemble_tool` in `submission.py` rejects unknown IDs, more than 5 IDs, and non-neutral answers with empty evidence. When narrowed to paragraphs, for each valid ID the region containing that span is returned as the quotation. One evidence item is thus a group of paragraphs, not a whole page. When all pages were passed, the whole page containing the span is returned, and if the preceding page has a committee or "Federal Council and Parliament" heading, the page of that speaker block is added as well. In both cases the returned text is the source itself; no words are rewritten.

### Evidence-required correction rule

A `submit` that returns a non-neutral label without evidence is rejected in both Task A and Task B, and the model is asked once to retry with evidence IDs. For a Task A case narrowed to paragraphs, if it still gives no evidence, the case is run once more with all pages of the ballot item (re-run), and that answer is used. If the re-run still gives no evidence, or a Task B retry fails, the case gets the neutral default answer, so the rule acts as a decision rule: "if you cannot point to evidence, answer neutral." The official scoring treats the default answer as a valid neutral answer.

### Evidence completion and fallback

In Task A, `consulted_pages` appends, after the model's quotations, the pages adjacent to the quoted pages, the first 2 passed pages (the summary spread at the start of the item), and the remaining pages in descending order of BM25 against the claim, up to 5 items (pages over 5,000 characters are excluded). When narrowed to paragraphs, regions are added in the same order instead of pages. Completion does not change the label or the model's quotations, and it is also applied to neutral answers and default answers.

A case with no acceptable `submit`, or whose processing fails, gets the neutral default answer for that case alone, and the reason is written to a diagnostics file. The time limit per case is 300 seconds. `input_tokens` and `output_tokens` are the sums of the API `usage` over all calls in the case, and `inference_time_ms` is the time for the whole case, including context preparation.

## 3. Data

We use only the train split of the public dataset [8]. DEV60, PUBLIC60, and the confirmation set (30 rows used in both Task A and Task B form) are each 60 questions drawn from it, and all were used during development, so the numbers here are not estimates of performance on unseen data.

The card of the public dataset states MIT, and its creator is OST's AI Applications and Deployment Lab. Redistribution rights for the voting booklet PDFs need separate confirmation, and they are not bundled with this report.

## 4. Evaluation

Task A (Document) receives a whole booklet PDF and the ballot item name (vote); Task B (Reference) receives a short reference text. Both return one JSONL line per case. According to the official Solution API Guide [6], a Task A answer of entailment or contradiction must return at least one verbatim quotation in the source language with its physical page number (1-based), and the first 5 quotations (each up to about 5,000 characters) are scored. Evidence in Task B is optional and not scored; if returned, its page is `null`.

The official evaluation is 3-class macro-F1 on private held-out data, and it also considers evidence accuracy, token count, and time per case [2, 6]. In this report we run the organizers' scoring script locally (evidence matching uses rapidfuzz [7] partial matching) and compare:

- Task A and Task B macro-F1;
- Hit@5: the share of Task A questions with gold evidence where the first 5 returned quotations contain the gold passage;
- tokens and time per case;
- format failures: cases that fell back to the default answer.

## 5. Results

### Development history and diagnosis

On 2026-10-14 we adopted a version (v5) whose system prompt output instructions matched the argument format of `submit` (`docs/prompt-eval-log.md`). Averaged over 5 runs on DEV60, v5 scored Task A F1 0.650, Task B F1 0.815, and Hit@5 0.263. On the night of 10-15, motivated by work on verifiers and multi-agent setups [13, 14, 15, 16], we tried 3 configurations that add an 8B role to the parent, but format failures increased and evidence did not improve, so none were adopted.

On the morning of 10-16 we examined, without calling the model, the 39 Task A questions with gold evidence in DEV60 and PUBLIC60, and found that in 14 of them (36%) the page with the gold evidence was not passed to the model. The old method searched for words such as `im Detail` to find the start of the item's detail section, but these words falsely matched the table of contents page, and the item's summary spread (In Kürze, En bref, In breve), which is a frequent source for reference texts, was dropped. In another 3 questions the gold evidence matched none of the pages that pypdf extracted. We replaced it with the heading-based method and checked the 501 public rows, excluding the 30 confirmation rows, whose gold evidence matches a page (no tuning was done for individual gold rows).

Page selection audit (no model calls, 501 rows):

| Selection method | Contains gold evidence page | Context chars, mean | Max |
|---|---:|---:|---:|
| Old (table-of-contents regex) | 352 / 501 | 38,764 | 236,824 |
| New (headings) | 501 / 501 | 33,463 | 162,973 |

Fixing page selection alone left DEV60 Hit@5 at 0.263: even when given the correct page, the model quoted other pages. This matches reports that relevant passages in the input are not necessarily used [17, 18], so we added evidence completion. Commit 650de65 added merging of duplicate IDs, optional Task B evidence, and completion with adjacent pages; rescoring saved answers raised the number containing the gold evidence from 89 to 98 out of 149. The new-version values in the results table below come from a version before this change.

In 7 runs of the new version (DEV60 3 times, PUBLIC60 once, the confirmation set 3 times, 420 cases in total), the 70B parent's final answer matched the 8B child's recommendation in all 420 cases, and the parent's 2 calls accounted for 63% of all tokens and 65% of wait time. We therefore added configurations in which one model answers with a single `submit`: S, which uses only 70B, and R, which routes Task A to 70B and Task B to 8B. A single 8B call scored Task A F1 0.714 on DEV60 (0.361 when asked to answer in text JSON), short of 70B on booklet questions, so Task A stayed on 70B. While Task B accepted non-neutral answers without evidence, 70B answered off-topic claims as contradictions without evidence and Task B F1 dropped to 0.693, so commit 8d5c7e6 restored the evidence-required rule for Task B.

Next we tried passing only the paragraphs of the item's pages that relate to the claim. On 610 public rows, the share where some kept paragraph passes the scorer's matching was 0.970 with translation BM25 alone, 0.915 with the embedding alone, and 0.975 with fusion (0.968 for cross-language pairs), with about 8,700 characters passed. With paragraphs alone, however, Hit@5 rose but Task A F1 fell (0.833 on DEV60, 0.857 on PUBLIC60, 0.734 on the confirmation set). More questions fell back to the default answer because the model could not quote a passage supporting a contradiction, and raising the paragraph count to 12 or 16 did not recover it (0.826, 0.806). We then added a re-run that answers only the questions falling back to the default answer again with all of the item's pages. On the development runtime, the average Task A F1 over the three question sets became 0.900, against 0.882 when passing all pages. Re-runs occurred in 11, 8, and 6 of 60 questions, and yielded answers with evidence in 6, 4, and 3 of them.

96% of claims name their source in their opening words, and for claims whose source is the summary, the gold evidence was on the summary spread in 96% of the public data. Section preference uses this. On the other hand, adding one sentence to the system prompt asking the model to check the direction of the recommendation (accept or reject) fixed 4 of 5 direction errors but added 8 errors labeling neutral as contradiction, raising errors on the three question sets from 15 to 17 out of 180, so we reverted it.

### Comparison

The table compares v5, the new version (70B parent and 8B child, commit 76a0e6e), R with all pages, and the adopted R with paragraphs, section preference, and re-runs. On the confirmation set, v5 and the new version were run alternately 3 times each and scored only after all runs finished. The two R rows were obtained by running each question set once on the submission runtime (`runtime.py`) and scoring with the official scorer. Even at temperature 0, the same input differs by a few cases between runs, so we treat a difference of about 0.03 between single runs as within chance.

Values are means; the number of runs for DEV60, PUBLIC60, and the confirmation set is 5, 5, 3 for v5, 3, 1, 3 for the new version, and 1 each for both R rows. The time for v5 on PUBLIC60 is not recorded in the materials we consulted.

| Question set | Configuration | Task A F1 | Task B F1 | Hit@5 | Tokens/case | s/case |
|---|---|---:|---:|---:|---:|---:|
| DEV60 | v5 | 0.650 | 0.815 | 0.263 | 28,232 | 6.3 |
| | 70B+8B | 0.705 | 0.815 | 0.544 | 24,361 | 5.8 |
| | R all pages | 0.875 | 0.853 | 0.737 | 10,864 | 3.9 |
| | R para.+sect.+re-run | 0.867 | 0.897 | 0.842 | 8,223 | 4.2 |
| PUBLIC60 | v5 | 0.701 | 0.917 | 0.30 | 30,382 | not recorded |
| | 70B+8B | 0.869 | 0.931 | 0.65 | 28,964 | 6.5 |
| | R all pages | 0.967 | 1.000 | 0.750 | 11,000 | 3.8 |
| | R para.+sect.+re-run | 1.000 | 0.967 | 0.750 | 7,314 | 4.1 |
| Confirmation 60 | v5 | 0.734 | 0.929 | 0.569 | 25,980 | 6.7 |
| | 70B+8B | 0.797 | 0.929 | 0.625 | 28,843 | 6.8 |
| | R all pages | 0.802 | 0.904 | 0.750 | 10,954 | 3.5 |
| | R para.+sect.+re-run | 0.863 | 0.903 | 0.833 | 5,874 | 3.7 |

### v5 and the new version

On DEV60 the new version's Task A F1 beat v5 in all 3 runs (0.690 to 0.728). On the confirmation set, v5 recorded one question that exceeded the 240,000-byte request limit as a default answer with 0 tokens, so on the 59 questions both versions processed, v5 used 26,420 and the new version 26,692 tokens per case. The new version failed two of the preregistered criteria, Hit@5 (at least 0.10 above v5; actual +0.056) and tokens (no more than v5; actual +11%), but the owner judged these two criteria to be absent from the competition rules, recompared on the competition's evaluation items, and adopted the new version (`docs/confirmation-protocol-2026-10-16.md`).

### The new version and R

R with all pages had higher Task A F1 and Hit@5 than the new version on all three question sets, at less than half the tokens, but on the confirmation set the Task A F1 difference (0.797 vs. 0.802) is within chance, and Task B F1 was 0.904 against the new version's 0.929. S, which uses only 70B, also beat the new version on Task A F1 and Hit@5, but it produced many default answers (15, 10, and 8 on DEV60, PUBLIC60, and the confirmation set) and tended to answer off-topic Task B claims as contradictions, so we chose R (`docs/single-call-results-2026-10-16.md`).

### All pages vs. paragraphs+sections+re-run

Averaged over the three question sets, the adopted configuration raised Task A F1 from 0.881 to 0.910 and Hit@5 from 0.746 to 0.808, cut tokens from 10,939 to 7,137 per case, and increased time from 3.7 to 4.0 seconds per case due to translation and re-runs. The Task A F1 gain comes from PUBLIC60 (0.967 to 1.000) and the confirmation set (0.802 to 0.863); on DEV60 it went from 0.875 to 0.867. Task B does not use the booklet, so the Task B F1 difference (means 0.919 and 0.922) is run-to-run variation.

## 6. Limitations

### Evaluation limits

All numbers are on public data used during development, with 60 questions and 1 to 5 runs. The adopted configuration was measured only once per question set. Performance on the official held-out data is unknown.

### Extraction limits

Of the new version's 420 cases described above, we examined the 149 Task A cases whose evidence is scored, and in 26 the gold evidence text does not match pypdf's extracted text. We believe most of these mismatches are resolved by making evidence region-level, because quotations become shorter than whole pages and pass the scorer's partial matching more easily. However, we have not rescored these 26 cases individually. PDFs whose text cannot be extracted are reported as errors without OCR. Booklets without headings are passed in full, so the input becomes long.

### Re-run cost and runtime environment

A re-run adds one call for booklet questions where the paragraphs gave no evidence. The Docker image that bundles the embedding weights was built and run end to end on 2026-10-16 (see Reproducibility).

### Remaining classification errors

On the final configuration's three question sets (one run each, 180 questions), 15 label errors remain. Of these, 5 confuse whether the Federal Council or Parliament recommends acceptance or rejection, and this also happens in Task B. Adding a rule to the system prompt reduced direction errors but increased other errors, and we have not yet found a fix without side effects.

### Nature of the evidence

A source ID guarantees where in the source a quotation comes from, but not that the quotation supports the decision [19]. Paragraph narrowing and the pages or regions added by completion are chosen by retrieval, not by the model's judgment.

### Next steps

Run the adopted configuration several times per question set to estimate run-to-run variance. Check whether region-level evidence hits the 26 extraction mismatches, and for the rest compare PDF extraction libraries other than pypdf.

## 7. Reproducibility

The submission runs in Docker. The official contract [6] requires a CPU-only linux/amd64 image that uses the injected `BASE_URL` and `API_KEY` for every model call (host keys are not read) and downloads nothing at run time. `Dockerfile.agent` installs Pi 1.1.0 and `@tintinweb/pi-subagents` from `package-lock.json` in a Node 26.10.0 stage, copies `track_2a/src` and the runtime into `python:3.11-slim-bookworm`, and bundles `model2vec==0.10.0` and the embedding weights at `docker build` time.

The entry point is `runtime.py`, with defaults `PIPELINE=R` (in both `Dockerfile.agent` and `Makefile`), `CONTEXT_SELECTION=claim_paragraphs`, and `CLAIM_SPANS=8`. `ESCALATE_ON_FALLBACK=0` disables re-runs, and `CONTEXT_SELECTION=vote_pages` passes all of the item's pages. `PIPELINE=C` selects the 70B parent with 8B child, and `PIPELINE=S` the 70B-only configuration. In R, `LLM_MODEL` is ignored even if set.

```
make run INPUT_DIR=/path/to/input INPUT=/data/input.jsonl \
  OUTPUT_DIR=/path/to/new/output
```

Besides the canonical JSONL, the output directory receives `.diagnostics.jsonl` and `.evaluation.jsonl`. On 2026-10-16 we built the Docker image for linux/amd64 and confirmed with `make run` on 6 questions that the official scorer can read the output (image 249 MB, including the 140 MB embedding weights).

In the development harness, Pi 1.1.0 is placed in `~/.cache/ost-pi-1.1.0`, and `PI_PACKAGE_ROOT` and `PI_SUBAGENTS_ROOT` point to that location. The repository is https://github.com/yasuhito/hackapertus-ost, and the submitted revision is the latest commit on master. No demo is provided; the CLI above reproduces the results.

## License

The repository code is licensed under the Apache License 2.0 (`LICENSE` at the repository root). This report is licensed under CC-BY-4.0. The competition terms require code and weights under Apache-2.0, documents under CC-BY-4.0, and submitted datasets under CDLA-Permissive-2.0. The bundled pypdf is subject to the terms of its bundled license file. The card of the public dataset [8] states MIT, and its creator is OST's AI Applications and Deployment Lab. Redistribution rights for the voting booklet PDFs need separate confirmation, and they are not bundled with this report.

## References

1. Hack Apertus. Track 2A technical report template. https://github.com/HackApertus/project-template/blob/main/track_2a/technical_report.md
2. Hack Apertus and OST. Track 2A: Multilingual Natural Language Inference over Swiss Official Voting Booklets. 2026. https://hackapertus.notion.site/3deb4fec112a80258fd2ddc61616011d
3. Swiss AI Initiative. Apertus: Democratizing Open and Compliant LLMs. https://arxiv.org/abs/2509.14233
4. Swiss AI Initiative. swiss-ai/Apertus-v1.5-70B (model card). https://huggingface.co/swiss-ai/Apertus-v1.5-70B
5. Swiss AI Initiative. swiss-ai/Apertus-v1.5-8B (model card). https://huggingface.co/swiss-ai/Apertus-v1.5-8B
6. Hack Apertus and OST. Solution API Guide. 2026. https://hackapertus.notion.site/ef5b4fec112a834da43101ede56300f5
7. rapidfuzz 3.14.6. Imported by the official evaluator (`evaluate.py`, `fuzz.partial_ratio`); version from the evaluator's `uv.lock`.
8. OST AI Applications and Deployment Lab. MNLI over Swiss Voting Booklets. https://huggingface.co/datasets/OSTswiss/MNLIoverSwissVotingBooklets
9. pypdf 6.1.1. https://pypi.org/project/pypdf/
10. Stephen Robertson and Hugo Zaragoza. The Probabilistic Relevance Framework: BM25 and Beyond. Foundations and Trends in Information Retrieval, 2009.
11. @earendil-works/pi-coding-agent 1.1.0. npm package; version pinned in `track_2a/dev/format/package.json`.
12. @tintinweb/pi-subagents 0.19.0. npm package; version pinned in `track_2a/dev/format/package.json`.
13. Dhuliawala and others. Chain-of-Verification Reduces Hallucination in Large Language Models. 2023. https://arxiv.org/html/2309.11495v2
14. Huang and others. Large Language Models Cannot Self-Correct Reasoning Yet. 2024. https://arxiv.org/html/2310.01798v2
15. Du and others. Improving Factuality and Reasoning in Language Models through Multiagent Debate. 2023. https://arxiv.org/html/2305.14325v1
16. Smit and others. Should we be going MAD? A Look at Multi-Agent Debate Strategies for LLMs. 2024. https://arxiv.org/html/2311.17371v3
17. Liu and others. Lost in the Middle. 2023. https://arxiv.org/abs/2307.03172v3
18. Hsieh and others. RULER. 2024. https://arxiv.org/abs/2404.06654v3
19. Gao and others. Enabling Large Language Models to Generate Text with Citations. 2023. https://arxiv.org/abs/2305.14627v2
