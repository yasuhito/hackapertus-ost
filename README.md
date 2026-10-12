# Hack Apertus Track 2A — OST

Multilingual NLI over Swiss voting booklets. Deadline: **2026-10-16**.
Original track requirements remain in `track_2a/README.md`; report in
`track_2a/technical_report.md`. Private repository: `yasuhito/hackapertus-ost`. No submission has been made.

## Run from a clean checkout

Docker is the only host dependency. The default is an explicit **mock smoke run**
with bundled example cases: no credentials, GPU, weights or API calls needed.

```sh
make run
# output/predictions.jsonl
```

For judge-supplied cases/PDFs:

```sh
make run INPUT_DIR=/data OUTPUT_DIR=/output BOOKLET_DIR=/path/to/booklets \
  LLM_BACKEND=openai
```

The container mounts input at `/data`, output at `/output`, PDFs at `/booklets`.
Use booklet paths `/booklets/name.pdf`, or paths relative to the input JSONL's
parent (e.g. `booklets/name.pdf` if PDFs are inside the input mount).
`INPUT` and `OUTPUT` override the container filenames. Root and track Makefiles work.

## Entrypoint and local path

```sh
python3 -m venv .venv
.venv/bin/pip install -r track_2a/requirements.txt
.venv/bin/python track_2a/src/predict.py \
  --input /data/cases.jsonl --output /output/predictions.jsonl --backend mock
make test PYTHON=.venv/bin/python
make run-local PYTHON=.venv/bin/python
```

Beginner: `{id, vote, reference:{text,language}, claim:{text,language}}`.
Advanced: `{id, booklet:{path,language}, vote, claim:{text,language}}`.
Every input line produces one JSON output with ID, label, label_name, evidence
and metrics. Mapping: **0 entailment, 1 neutral, 2 contradiction**.
Task A evidence for 0/2 must be a nonempty exact original-language substring of
the claimed physical 1-based PDF page, at most 5000 characters per item. Only the
first five items are returned. Task B evidence is optional and uses `page: null`.
Malformed input/model output, missing PDFs, non-verbatim evidence and API failures
produce schema-valid neutral placeholders with an `error` diagnostic. These are
**always wrong in the local scorer**, even when the gold label is neutral.
Blank/malformed JSON lines get `invalid-line-N` IDs when no ID can be recovered.
No silent mock fallback, retrieval or document truncation is performed.

## Apertus endpoint configuration

Select `LLM_BACKEND=openai` for actual inference. The CLI defaults to openai;
`make run` defaults to mock to keep a clean-checkout smoke test safe.

| Variable | Default / purpose |
|---|---|
| `BASE_URL` | Official proxy/development URL; overrides `LLM_BASE_URL`; default `https://api.inference.cscs.ch/v1` |
| `LLM_MODEL` or `LLM_NAME` | `swiss-ai/apertus-v1.5-8b` |
| `API_KEY` | Overrides `LLM_API_KEY` / `PUBLICAI_API_KEY`; required for CSCS/Public AI, optional for local vLLM |
| `LLM_USER_AGENT` | `HackApertus-OST/1.0 (Track-2A)` |
| `LLM_TIMEOUT` | 180 seconds |
| `LLM_MAX_OUTPUT_TOKENS` | 2048 |

The 70B alternative is `swiss-ai/apertus-v1.5-70b`. For an already running local
vLLM server set `BASE_URL=http://localhost:8000/v1` and `LLM_MODEL` to its
served Apertus model name. Inside Docker, localhost is the container: use a
reachable host/network address instead. Serving model weights is external to this
CPU client image; GPU/VRAM needs depend on serving configuration.
No live endpoint was called in development. Keys are never included in git.

## Data and reproducible dev evaluation

The public HF dataset exposes **train only**. Downloaded `v1.1.jsonl` is bundled
(~12.7 MB), with a checksum-enforcing re-download script. No test split was read.
A fixed SHA256 date-group split yields 1,157 train and 331 dev rows, keeping all
languages of the same voting date together. See `track_2a/data/dataset_stats.json`.

```sh
make download PYTHON=.venv/bin/python BOOKLET_DIR="$PWD/booklets"
make prepare PYTHON=.venv/bin/python BOOKLET_DIR="$PWD/booklets"
# Do not run dev-eval on the historical full dev files: they include the
# protected 2024-06-09 holdout. Use the approved fixed54 workflow instead.
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
