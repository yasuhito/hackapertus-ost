Source URL: https://gitlab.com/ifsoftware/hackapertus-starter/-/raw/main/README.md
Fetch date: 2026-10-12

# HackApertus starter

A minimal uv project with one `main.py` and a Dockerfile. It shows how to read
benchmark requests and write predictions using the required CLI:

```bash
python main.py --input cases.jsonl --output predictions.jsonl
```

The starter **randomly chooses entailment, neutral, or contradiction** for every
case. It does not read PDFs, call an LLM, or check claims. No API key is needed.

## Run locally

With [uv](https://docs.astral.sh/uv/getting-started/installation/) installed:

```bash
uv sync --locked
uv run python main.py --input examples/cases.jsonl --output output/predictions.jsonl
cat output/predictions.jsonl
```

Each run can produce different labels. Output directories are created automatically;
an existing output file is overwritten.

## Generate cases from Hugging Face

`prepare_cases.py` downloads `v1.1.jsonl` from the dataset's current `main` branch
and creates input requests. It follows updates to that file rather than a pinned commit.
It uses Python's standard library; no additional dependencies or API key are needed.

```bash
# All dataset rows, with one task A and one task B case per row:
uv run python prepare_cases.py

# Or start with 10 rows (20 cases) and download the task A PDFs:
uv run python prepare_cases.py --limit 10 --download-booklets

# Reference-only cases, without PDFs:
uv run python prepare_cases.py --task B --limit 10

uv run python main.py --input data/cases.jsonl --output output/predictions.jsonl
```

The script writes `data/cases.jsonl` and `data/expected-labels.jsonl`. The latter
contains gold labels for local scoring only: **never pass it to your predictor**.
Use `--output-dir` to choose another directory. Each run overwrites both JSONL files;
previously downloaded PDFs are reused. `--limit` selects the first N rows, which
are not necessarily balanced across labels. Generated IDs use row positions, so
they can change if the dataset is reordered or rows are added or removed.

Task A PDF downloads are optional for the random starter; use `--download-booklets`
when your solution actually reads them. Downloads happen during preparation, before
evaluation. The generator preserves references and dataset labels, including the
title-only reference rows.

To use generated cases with Docker, replace the example input mount below with:

```bash
-v "$PWD/data/cases.jsonl:/data/cases.jsonl:ro" \
-v "$PWD/data/booklets:/data/booklets:ro" \
```

Include the booklet mount after downloading PDFs for task A. Keep
`expected-labels.jsonl` outside the prediction container.

## Input

JSONL means one JSON object per line. `examples/cases.jsonl` has two real dataset
examples: one PDF request (task A) and one reference request (task B).

Here is the task A request, expanded for readability:

```json
{
  "id": "v1.0-row-1158-A",
  "booklet": {
    "path": "booklets/2024_09_22_de.pdf",
    "language": "de"
  },
  "vote": "Volksinitiative «Für die Zukunft unserer Natur und Landschaft (Biodiversitätsinitiative)»",
  "claim": {
    "text": "Laut dem Abstimmungstext stammt der Bundesbeschluss über die Volksinitiative «Für die Zukunft unserer Natur und Landschaft (Biodiversitätsinitiative)» vom 15. Juni 2024.",
    "language": "de"
  }
}
```

For task B, `reference` replaces `booklet`. Here is the real second example:

```json
{
  "id": "v1.0-row-414-B",
  "reference": {
    "text": "Volksinitiative «Für die Zukunft unserer Natur und Landschaft (Biodiversitätsinitiative)»\n\n\nAbstimmungstext Bundesbeschluss über die Volksinitiative «Für die Zukunft unserer Natur und Landschaft (Biodiversitätsinitiative)» vom 22. Dezember 2023",
    "language": "de"
  },
  "vote": "Volksinitiative «Für die Zukunft unserer Natur und Landschaft (Biodiversitätsinitiative)»",
  "claim": {
    "text": "Il testo di voto afferma che il Bundesbeschluss (decreto federale) relativo all’iniziativa popolare «Für die Zukunft unserer Natur und Landschaft (Biodiversitätsinitiative)» è datato 22 dicembre 2023.",
    "language": "it"
  }
}
```

The random starter uses only `id`, so you do not need any PDFs to run it.

## Output

Write one response per input, echoing its `id`. For example:

```json
{
  "id": "v1.0-row-1158-A",
  "label": 2,
  "label_name": "contradiction",
  "evidence": [],
  "metrics": {
    "input_tokens": 0,
    "output_tokens": 0,
    "inference_time_ms": 0
  }
}
```

| Label | Name |
| --- | --- |
| 0 | entailment |
| 1 | neutral |
| 2 | contradiction |

`examples/predictions.jsonl` shows a sample run. Labels are random, evidence is
empty, and metrics are placeholders. This demonstrates the CLI and response shape.
For a real submission, task A labels 0 and 2 require evidence with 1-based PDF pages:
a verbatim quote or the text of the page it is on, at most about one page long (only the
first five items are scored). Task B evidence is optional;
if you give it, use `null` for the page. Report actual usage and timing.

## Run with Docker

```bash
docker build --platform linux/amd64 -t hackapertus-starter:dev .
mkdir -p output
docker run --rm --platform linux/amd64 \
  -e BASE_URL=https://api.inference.cscs.ch/v1 \
  -e API_KEY="your-cscs-api-key" \
  -v "$PWD/examples:/data:ro" \
  -v "$PWD/output:/output" \
  hackapertus-starter:dev \
  --input /data/cases.jsonl --output /output/predictions.jsonl
```

`BASE_URL` is the LLM endpoint and `API_KEY` is its key. Replace the placeholder
with your own key for a real solution. The random starter ignores these variables,
so the placeholder works for this example. During evaluation, the organizers pass
the token-counting proxy URL and a team-specific key using these same names.

Docker passes the two CLI arguments to `main.py`. The image installs dependencies
at build time and runs on CPU. Once your solution reads PDFs, mount them under
`/data/booklets/`; `booklet.path` is relative to `/data`.

## Evaluate locally

`evaluate.py` scores a predictions file against the gold labels from `prepare_cases.py`,
using the same rules as the official evaluation as far as they can be reproduced offline:

```bash
uv run python evaluate.py \
  --predictions output/predictions.jsonl \
  --expected data/expected-labels.jsonl \
  --cases data/cases.jsonl
```

`--cases` is optional; it adds scores per language pair. Add `--json output/score.json`
to save the full report.

### What it reports

1. **Macro-F1 per task.** The unweighted mean of the entailment, neutral and
   contradiction F1 scores, computed separately for task A and task B from the
   predicted `label` only. Evidence never turns a correct label into a wrong one.
   A missing or duplicated `id`, an invalid `label`, or a `label_name` that does not
   match the label counts as a wrong prediction. Accuracy and per-class precision,
   recall and F1 are shown too.
2. **Minimum macro-F1.** A submission is only valid if it reaches **0.70 on task B**
   and **0.60 on task A**. The report marks each task `pass` or `BELOW`.
3. **Evidence score (task A only).** For every case whose gold label is entailment or
   contradiction, a case counts as found if one of the **first five** evidence items
   overlaps the gold reference passage: either the item lies inside the passage (a short
   quote) or the passage lies inside the item (for example the whole page it is on). Each
   item may be **at most about one page long** (5,000 characters, longer than 95% of
   booklet pages); longer items do not count. The score is found ÷ those cases. Matching
   is fuzzy and ignores case, whitespace and words hyphenated across lines, so small PDF
   extraction differences do not matter. `--min-ratio` sets how close the match must be
   (default 90 of 100) and `--max-quote-chars` the length limit. Task B evidence is
   optional and not scored.
4. **Usage.** Your self-reported tokens and time per case are shown as averages. The
   official token and time scores come from the proxy and are relative to the other
   teams, so they cannot be computed locally.

The gold passages for the evidence score are stored in `expected-labels.jsonl`. If yours
was generated before this was added, run `prepare_cases.py` again.

### Where this differs from the official evaluation

- The official score uses a held-out private set, so local numbers are only an
  estimate. `--limit` samples are also not balanced across labels.
- Evidence pages are not checked yet.
- The final score also includes the relative token and time scores; see the
  evaluation notes for the formula.

## Build your solution

Replace the random prediction in `main.py` with your implementation. Add dependencies
using `uv add`. When adding LLM calls, read `BASE_URL` and `API_KEY` from the runtime
environment so the evaluation can inject its endpoint and key.

See the [course API guide](https://notes.rehash.ch/s/7912e1d2-5d79-4c93-add9-12ec4a6d1b1e)
for the full requirements.

The checked-in example inputs come from zero-based rows 1158 and 414 of
[OSTswiss/MNLIoverSwissVotingBooklets](https://huggingface.co/datasets/OSTswiss/MNLIoverSwissVotingBooklets),
`v1.0.jsonl` at revision `adca9a5ee87e9813cef80b305c3b12e3e8a05959` (MIT dataset
license). The IDs are generated for these examples.
