Source URL: https://hackapertus.notion.site/ef5b4fec112a834da43101ede56300f5
Fetch date: 2026-10-12

# solution-api-guide

## 🎓 Solution API Guide

Build a solution that checks claims against Swiss voting booklets and returns a label, short evidence, and usage metrics.

### Start with the example repo

**You are free to use any programming language and tooling.** Your submission must follow the Docker and CLI input/output contract below.

[hackapertus-starter](https://gitlab.com/ifsoftware/hackapertus-starter) is an optional Python/uv example. You do not have to use the repository, Python, or uv. Its [README](https://gitlab.com/ifsoftware/hackapertus-starter/-/blob/main/README.md) shows Docker setup and real input/output examples; the commands below apply only to this example.

The starter has one `main.py` and **returns random labels**. It demonstrates the interface; replace its predictions, empty evidence, and placeholder metrics with your solution.

```Bash
uv sync --locked
uv run python main.py --input examples/cases.jsonl --output output/predictions.jsonl
```

### Two tasks

| Your job | Input | Task |

| Find the relevant information, then check the claim. | Booklet PDF, vote name, claim | **A: Document** |

| Check the claim against that passage. | Reference passage, vote name, claim | **B: Reference** |

Support both tasks, including mixed input files. Each request contains exactly one of `booklet` or `reference`. Handle all German, French, and Italian source–claim combinations; their languages can differ.

Use `vote` to identify the correct proposal within a booklet. Start task A with a full-document baseline before adding retrieval or compression.

### Input/output contract

Your Docker entrypoint must accept:

```Bash
<entrypoint> --input /data/cases.jsonl --output /output/predictions.jsonl
```

**JSONL:** one complete JSON object per line. Write one response for every input ID, in any order, and exit with code `0` on success. Missing or invalid responses count as wrong predictions.

**Examples in the repo:**

- `[examples/cases.jsonl](https://gitlab.com/ifsoftware/hackapertus-starter/-/blob/main/examples/cases.jsonl)`: input with one real task A request (booklet PDF) and one task B request (reference text).

- `[examples/predictions.jsonl](https://gitlab.com/ifsoftware/hackapertus-starter/-/blob/main/examples/predictions.jsonl)`: the matching output from the starter. Its labels are random and its evidence and metrics are placeholders; it shows the format only. See the task A example below for real evidence.

The [README](https://gitlab.com/ifsoftware/hackapertus-starter/-/blob/main/README.md#input) shows both examples expanded and explains each field.

| Request field | Contents |

| `id` | Unique string; echo unchanged. |

| `vote` | Vote name in the source language. |

| `claim` | `text` and `language` (`de`, `fr`, `it`). |

| `booklet` (A) | `path` relative to `/data` and `language`. |

| `reference` (B) | `text` and `language`. |

Example path: `booklets/2024_09_22_de.pdf` resolves to `/data/booklets/2024_09_22_de.pdf`. Cases can share PDFs; caching is allowed, but predictions must not depend on case order.

| Response field | Requirements |

| `id` | Same as the request. |

| `label`, `label_name` | `0/entailment`, `1/neutral`, or `2/contradiction`. |

| `evidence` | Array of objects with `page` and `text`. |

| `metrics.input_tokens` | Total LLM input tokens across all calls for the case. |

| `metrics.output_tokens` | Total LLM output tokens, including reasoning tokens. |

| `metrics.inference_time_ms` | Case wall-clock time in milliseconds. |

Judge against the supplied source: **supports = entailment; insufficient information = neutral; refutes = contradiction**.

For task A labels 0 and 2, include at least one evidence item with its **1-based PDF page number**: a verbatim quote in the source’s original language, or the text of the page it is on. Each item may be **at most about one page long** (5,000 characters); longer items do not count. For neutral, `evidence` may be `[]`. Only the **first five** evidence items are scored. In task B, evidence is optional and not scored; if you include it, use `null` for the page.

**Example (task A).** Claim in German: *“Der Bundesrat spricht sich für die Abschaffung der Emissionsabgabe aus.”* Booklet: `booklets/2022_02_13_it.pdf`. The quote stays in Italian, the booklet’s language, and is not translated:

```JSON
{
  "id": "v1.1-row-60-A",
  "label": 0,
  "label_name": "entailment",
  "evidence": [
    {
      "page": 43,
      "text": "Per tutte queste ragioni, Consiglio federale e Parlamento raccomandano di accettare la modifica della legge federale sulle tasse di bollo."
    }
  ],
  "metrics": {
    "input_tokens": 1304,
    "output_tokens": 46,
    "inference_time_ms": 776
  }
}
```

Quote from the section of the booklet that deals with the vote in detail. Booklets often repeat a fact in a summary at the front; a quote from there may not match the gold passage, which comes from one place in the booklet. If a fact appears in several places, cite each of them as a separate item.

- An item can be a sentence, a paragraph, or the whole page, copied from the PDF text. Line breaks and hyphenation from PDF extraction may differ; matching tolerates that.

- Put the most relevant quote first.

- For task B, the same shape with `"page": null`, or `"evidence": []`.

### Model and Docker requirements

Use only **Apertus v1.5** models (`swiss-ai/Apertus-v1.5-...`). Read `BASE_URL` and `API_KEY` at runtime, with environment variables taking precedence over local configuration.

For development, use `https://api.inference.cscs.ch/v1` and your api key. Evaluation injects a token-counting proxy URL and team key. Every remote model call must use `BASE_URL`; local parsing, OCR, or embeddings may run locally.

The [repo’s Docker example](https://gitlab.com/ifsoftware/hackapertus-starter/-/blob/main/README.md#run-with-docker) shows how to pass these variables and mount inputs and outputs.

- Target `linux/amd64`, without a GPU.

- Treat `/data` as read-only; write predictions to `/output` and caches to a writable location such as `/tmp`.

- Include dependencies and required local model weights in the image; do not download them at runtime.

- Keep API keys and `.env` files out of the image.

### Data and evaluation

Develop with [OSTswiss/MNLIoverSwissVotingBooklets](https://huggingface.co/datasets/OSTswiss/MNLIoverSwissVotingBooklets). Each row can produce an A and a B case: `claim`, `claim_language`, `vote`, and `reference_language` supply the corresponding request fields; B uses `reference_string`, while A uses the PDF from `booklet_url`.

The example repo includes `[prepare_cases.py](https://gitlab.com/ifsoftware/hackapertus-starter/-/blob/main/prepare_cases.py)` to generate `data/cases.jsonl` from the dataset’s current `main/v1.1.jsonl`. Run it from the repo root:

```Bash
uv run python prepare_cases.py
# Small sample, including task A PDFs:
uv run python prepare_cases.py --limit 10 --download-booklets
```

By default it generates both tasks; use `--task A` or `--task B` for one task. Gold labels are written separately to `data/expected-labels.jsonl` for local scoring only. Run preparation before evaluation, and keep that file outside the prediction container.

The repo also includes `[evaluate.py](https://gitlab.com/ifsoftware/hackapertus-starter/-/blob/main/evaluate.py)` to score your predictions locally with the same rules as the official evaluation:

```Bash
uv run python evaluate.py \
  --predictions output/predictions.jsonl \
  --expected data/expected-labels.jsonl \
  --cases data/cases.jsonl
```

Final evaluation uses a held-out private set.
