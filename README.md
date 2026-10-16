# Hack Apertus Track 2A, OST: multilingual NLI over Swiss voting booklets

Team yasuhito (Yasuhito Takamiya). Repository: https://github.com/yasuhito/hackapertus-ost.
Technical report: `report/main.pdf` (6 pages plus references); Markdown summary in
`track_2a/technical_report.md`.
Development log and measurements: `STATUS.md`, `docs/single-call-results-2026-10-16.md`.

## What the submitted pipeline does

One native tool call per case through Apertus v1.5 only (`BASE_URL` and `API_KEY`
injected at runtime). Booklet cases (Task A) go to `swiss-ai/Apertus-v1.5-70B`,
reference cases (Task B) to `swiss-ai/Apertus-v1.5-8B`.

1. pypdf extracts pages; the vote's pages are found by the printed running headers
   (`Erste Vorlage`, `Premier objet`, `Primo oggetto`).
2. Those pages are split into paragraphs of 200 to 700 characters. A cross-language
   claim is first translated into the booklet language by Apertus 8B (one short call,
   counted in the case's tokens). Paragraphs are ranked by rank fusion of BM25 over
   the translation, character 4-gram BM25, a local static multilingual embedding
   (model2vec potion-multilingual-128M, int8, baked into the image at build time)
   and a section prior derived from the claim's attributive opening (summary,
   committee, Federal Council and Parliament, vote text).
3. The top 8 paragraphs plus their neighbours are sent as verbatim regions. The model
   answers with the `submit` tool: label plus IDs of supplied source spans.
4. A non-neutral answer without a cited span is repaired once; if still unsupported,
   the case is re-run once on all vote pages. Evidence is restored verbatim from the
   PDF text and padded with the regions most related to the claim (at most five).

Measured on three exposed 60-case public sets through this exact runtime: Task A
macro-F1 0.910, Task B macro-F1 0.922, Task A Hit@5 0.808, about 7,100 tokens and
4.0 s per case. The official held-out score is unknown. Details in the report.

## Run from a clean checkout

Docker is the only host dependency. The image is CPU-only linux/amd64 and downloads
nothing at runtime (Pi 1.1.0 and the embedding weights are installed at build time).

```sh
make run INPUT_DIR=/path/to/input OUTPUT_DIR=/path/to/output BOOKLET_DIR=/path/to/booklets \
  BASE_URL=... API_KEY=...
# writes OUTPUT_DIR/predictions.jsonl plus .diagnostics.jsonl and .evaluation.jsonl
```

The container mounts input at `/data`, output at `/output`, PDFs at `/booklets`.
Use booklet paths `/booklets/name.pdf`, or paths relative to the input JSONL's
parent. `INPUT` and `OUTPUT` override the container filenames.

Defaults (Makefile and `Dockerfile.agent`): `PIPELINE=R`, `CONTEXT_SELECTION=claim_paragraphs`,
`CLAIM_SPANS=8`, escalation on. `CONTEXT_SELECTION=vote_pages` sends the vote's whole
pages instead; `PIPELINE=C` is the earlier 70B parent plus 8B child configuration;
`ESCALATE_ON_FALLBACK=0` disables the full-page re-run. Budgets scale with the input
size; a case whose requests fail yields a neutral fallback with its error recorded in
the diagnostics sidecar, never an aborted run.

## Input and output contract

Task B input: `{id, vote, reference:{text,language}, claim:{text,language}}`.
Task A input: `{id, booklet:{path,language}, vote, claim:{text,language}}`.
Every input line produces one JSON output with ID, label, label_name, evidence
and metrics. Mapping: **0 entailment, 1 neutral, 2 contradiction**.
Task A evidence for labels 0 and 2 is a nonempty exact original-language substring of
the claimed physical 1-based PDF page, at most 5000 characters per item; at most five
items are returned. Task B evidence uses `page: null`. Malformed input or model output,
missing PDFs and API failures produce schema-valid neutral placeholders with an
`error` diagnostic.

## Local development

```sh
python3 -m venv .venv
.venv/bin/pip install -r track_2a/requirements.txt model2vec==0.10.0
make test PYTHON=.venv/bin/python
```

The development harness pins Pi 1.1.0 (`track_2a/dev/format/package-lock.json`); see
`track_2a/dev/format/README.md`. Bundle evaluations used during development are run
with `track_2a/dev/eval/run_bundle.py` against the official evaluator.

## Data and reproducible dev evaluation

The public HF dataset exposes **train only**. Downloaded `v1.1.jsonl` is bundled
(~12.7 MB), with a checksum-enforcing re-download script. No test split was read.
A fixed SHA256 date-group split yields 1,157 train and 331 dev rows, keeping all
languages of the same voting date together. See `track_2a/data/dataset_stats.json`.

```sh
make download PYTHON=.venv/bin/python BOOKLET_DIR="$PWD/booklets"
make prepare PYTHON=.venv/bin/python BOOKLET_DIR="$PWD/booklets"
# For the existing fixed54 research workflow, use the command below.
# Public validation excludes reused problems; 2024-06-09 is not a confirmed
# competition prohibition. The official private evaluation set is separate.
./track_2a/dev/cscs/run.sh --prepare-only
```

Regenerate with `make prepare` after moving the PDF directory: advanced dev cases
contain absolute local paths. PDFs are ignored and stored outside the repository
(60 files, ~75.4 MB). Repo data is ~38 MB, below 100 MB.

Scoring aligns by ID, independent of order; missing, duplicate and error predictions
are wrong. It reports fixed-three-class macro-F1 overall/task/claim language/reference
language/same vs cross-lingual, strict task A gold-passage evidence match (including page; task B is not scored), token sums, mean latency and nearest-rank p95. Latency is end-to-end
per case, including PDF loading when uncached. Endpoint usage counts are used when
provided; otherwise tokens are estimated as ceil(UTF-8 bytes/4), **not** the official
judging proxy. Mock counters and timings are not real model efficiency measurements.

Public data lacks page annotations and its reference strings are not exact matches
in pypdf extraction. Advanced evidence scoring excludes those rows and returns null
rather than a fabricated score. A manually validated page/span mapping is a next step.
Mock full-dev reports are in `track_2a/data/results/`; they prove plumbing, not NLI quality.


### Fixed54 CSCS evaluation

See [the finite-job contract](track_2a/dev/cscs/README.md). `--prepare-only` does
not read credentials or call the API. `--user-run` explicitly authorizes a finite
live evaluation and does not require TTY/input. Never use it without approved
credits consumption. Completed or uncertain job evidence must be preserved.
The committed fixture uses relative PDF paths and excludes the protected holdout.

### Roast development measurement

The project-local Roast 1.3.0 recipe provides budgeted mock/frozen-history replay, resume, provenance, raw usage, timing and grouped evaluation. It creates no remote model calls. See [setup and commands](track_2a/dev/roast/README.md) and [coverage](track_2a/dev/roast/COVERAGE.md). The submitted runtime remains the Python Apertus CLI.
