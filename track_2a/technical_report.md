# Technical report — OST multilingual voting-booklet NLI

- **Track:** Track 2A — OST
- **Event:** Online, deadline 2026-10-16
- **Team / Demo:** Not assigned; local CLI prototype only.

## 1. Summary

A full-document baseline for multilingual NLI using the Apertus family through
an OpenAI-compatible endpoint, with exact evidence validation and JSONL CLI.
No actual Apertus inference was performed: no key is available and paid calls
were forbidden. Deterministic mock evaluations prove the pipeline end to end.

## 2. Architecture

`input JSONL -> reference or complete PDF pages -> prompt -> backend -> strict
JSON/evidence validation -> output JSONL -> independent ID-aligned scorer`.
The engine owns context provenance and output invariants. Scripts own public
asset acquisition and train-to-dev splitting. Two greenfield designs were
considered: cohesive engine vs exposed processing pipeline. The cohesive engine
was selected; independent scorer/download scripts and per-line error isolation
were retained. See `docs/architecture.md` for interfaces and rejected choices.

PDF text is extracted by pypdf 6.1.1, cached for up to 64 paths per process, with
physical page markers starting at one. Full-document advanced prompting uses the
vote name to distinguish proposals. Beginner prompting directly supplies its
reference. Neither path retrieves, translates, summarizes or truncates sources.
Model evidence must be a literal substring on its claimed page; invalid evidence
rejects the prediction. This proves provenance, not semantic relevance.

## 3. Use of Apertus

- **Model:** default `swiss-ai/apertus-v1.5-8b`; optional `swiss-ai/apertus-v1.5-70b`.
- **Use:** NLI inference only; no fine-tuning or auxiliary judge model.
- **Serving:** Public AI default or existing local vLLM via environment settings.

`src/predict.py` contains the complete system prompt, temperature 0, and 2048
maximum output tokens (configurable). It emphasizes document-relative inference,
qualifications, attribution, negation, DE/FR/IT combinations and original-language
evidence. JSON is required; an optional Markdown JSON fence is accepted.
User-supplied text is serialized as data and marked untrusted; prompt injection
resistance is not proven. No server-specific JSON-mode capability is required.

The mock labels entailment only for exact claim substrings and neutral otherwise;
it never inspects gold labels. It cannot establish multilingual semantic competence.

## 4. Data

Public dataset: OSTswiss/MNLIoverSwissVotingBooklets, MIT dataset metadata,
version v1.1, 1,488 train rows, 10 fields. It contains reference/claim text,
claim/reference languages, label, baseline score, publication/download dates,
booklet URL and vote title. Label counts: 495 entailment, 498 neutral,
495 contradiction. Claim languages: DE 495, FR 497, IT 496; reference languages:
DE 455, FR 569, IT 464. No test or official validation split exists in the
inspected HF metadata. Dataset download is public and ungated.

All 60 Swiss Federal Chancellery PDF URLs downloaded (~75.4 MB), outside the
repository; PDF redistribution rights were not reviewed, so PDFs are not committed.
Reference data is public political text, not collected human-subject data.
Source SHA256 and split definitions are stored in `data/dataset_stats.json`.

## 5. Evaluation

Dev is derived from train only: hash sorted publication dates with
`SHA256("ost-dev-v1:" + date)`, hold out the first rounded 20% of dates.
Four dates give 331 dev rows, with 1,157 train rows. No date appears on both sides.
Dev dates: 2020-09-27, 2021-03-07, 2024-03-03, 2024-06-09.

| Setup | Macro-F1 | Evidence exact match | Valid outputs |
|---|---:|---:|---:|
| Beginner deterministic mock, 331 dev | 0.174107 | 0/214 | 331/331 |
| Advanced full-PDF mock, 331 dev | 0.174107 | Unavailable | 331/331 |
| Apertus 8B/70B | Not run | Not run | Not run |

All 331 mock outputs were neutral. Fixed-class macro-F1 is not accuracy.
Reports in `data/results/` include per-language and cross-lingual breakdowns,
proxy input/output tokens and local latency. Advanced proxy input sum was
12,945,382 vs 730,185 for beginner; these approximations are not comparable to
actual Apertus tokenizer counts. Timing includes cold PDF extraction and warm
cache cases, so mean and p95 may have very different shapes.

Gold reference strings do not exactly occur on extracted PDF pages (0 exact
advanced dev mappings). No original gold page field exists. The scorer explicitly
excludes 214 advanced nonneutral evidence cases, giving null evidence score.
It does not silently infer pages by fuzzy matching. Beginner strict exact-passage
matching can penalize a shorter valid quotation; this local metric is conservative
and not a substitute for semantic relevance judging.

## 6. Limitations

Real endpoint accessibility, model ID availability, context limits and NLI quality
remain unverified. Docker is not installed here, so the image could not be built
or run. Full-document contexts may overflow the served model: failures are recorded,
not silently truncated. No OCR, retries, retrieval, parallel inference, automated
page-gold alignment or real tokenizer is implemented. Page numbering is physical,
not printed page labels. PDF caching assumes unchanged files during a run.
Source-only NLI does not resolve conflicting attributed claims automatically.

## 7. Reproducibility

CPU Python 3.11 client, pinned pypdf/pytest dependencies; no model weights or GPU
needed for mock mode. Root `make run` builds a Docker image and runs bundled smoke
cases without credentials, defaulting explicitly to mock. Set `LLM_BACKEND=openai`
for Apertus. For non-Docker development use the commands in root README.
`make download`, `make prepare`, `make dev-eval` reproduce assets and reports.
16 pytest cases passed, including a local loopback HTTP server for protocol testing;
no external inference request was made. Source, tests, sample cases and score
reports are locally committed; identify the exact revision with `git rev-parse HEAD`.

## 8. Next steps

Before the deadline: provision an authorized free/local Apertus endpoint, validate
full-context limits, run fixed-dev baselines for 8B and 70B, manually annotate
advanced evidence pages/spans, and build/run Docker on a Docker-enabled host.
Then compare retrieval/compression against measured full-document quality; keep
all evaluation on dev, with any future held-out test reserved for final judging.

## License

Project license retained from the template (`LICENSE`). This technical report
follows the template's CC-BY-4.0 designation. Dataset metadata declares MIT;
PDFs are linked/downloaded locally, not redistributed in git.

## References

- `docs/task_spec.txt`: pdftotext of supplied `/workspace/ost.pdf`.
- `docs/dataset_readme.md`: dataset field descriptions and license metadata.
- https://huggingface.co/datasets/OSTswiss/MNLIoverSwissVotingBooklets
- https://github.com/HackApertus/project-template
- Swiss Federal Chancellery booklet links: source `booklet_url` fields.
