# Design and ownership

Plan completed: ground template/spec, compare two shapes, synthesize, implement,
verify. Greenfield source tree; no existing subsystem to preserve.

## Caller usage

```
predict(case: dict, backend: Backend, base: Path, fallback_id: str) -> dict
score(gold: list[dict], raw_predictions: list[dict]) -> dict
```

The engine hides PDF page extraction, full-source prompting, endpoint transport,
JSON decoding and exact evidence validation behind a single per-case prediction.
`Backend.complete(messages, pages, claim) -> (raw_json, usage)` is the one inference
seam. The mock receives only source/claim, never gold labels. The OpenAI adapter
uses messages and environment settings; SDK objects do not leak into output.

The CLI streams one line at a time and resolves relative PDFs against input parent.
The scorer neither loads model weights nor invokes inference. Data scripts retain
IDs and metadata for independent evaluation and group all publication-date languages
in the same partition. Tests exercise the same entrypoint and backend seam.

## Alternatives and synthesis

1. Cohesive engine: source provenance and response invariants stay together;
   independent data/evaluation tools. Chosen for a small full-document baseline.
2. Public staged pipeline: extraction -> context -> prompt -> inference -> validate.
   Useful for retrieval experiments, but would expose ordering/provenance bookkeeping.

Retained the second proposal's per-line error isolation and diagnostic observability.
Rejected evidence segment IDs (spec requires original text/page), null labels (spec
requires 0/1/2), automatic mock fallback (misleading), and same-language-only assumptions
(spec explicitly requires cross-language cases). Fixed-schema neutral error placeholders
are valid JSON but always wrong in scorer. No architecture scrapping was needed.

## Boundaries / invariants

- Only original exact extracted page text may be quoted; physical 1-based pages.
- Model classifications are document-relative, not external truth judgments.
- Gold labels/evidence never enter inference prompts or the mock.
- Explicit endpoint errors never silently switch to mock.
- No test split used; official train-only source and derived date-group dev.
- Token proxy is an approximation, clearly separated from provider usage.
- Missing advanced page gold is unavailable, not evidence failure or invented truth.
