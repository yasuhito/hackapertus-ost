# Status — deadline 2026-10-16

## 2026-10-16 baseline: running-header page selection + consulted-page evidence (commit 76a0e6e)
- Replaces v5 after a one-time comparison on the reserved confirmation 60 (3 runs each):
  Task A F1 0.734 -> 0.797, Task B F1 0.929 -> 0.929, Hit@5 0.569 -> 0.625, fallbacks 3 -> 0,
  tokens on the 59 cases both versions processed 26,420 -> 26,692, time 6.7 -> 6.8 s/case.
- Decision and gates: `docs/confirmation-protocol-2026-10-16.md`. Diagnosis and dev/public
  measurements: `docs/next-strategy-2026-10-16.md`. Reserved 60 is now exposed.
- Dev harness pins Pi 1.1.0 (`~/.cache/ost-pi-1.1.0`); the Docker image installs it from the lock file.


## Data
- Public HF `OSTswiss/MNLIoverSwissVotingBooklets`, **ungated**; curl download succeeded.
- `v1.1.jsonl`: 1,488 rows, 12,742,710 bytes; only official split is `train`.
- Fields: claim, claim_language, reference_string, entailment_label, baseline_score,
  reference_language, booklet_publish_date, booklet_download_date, booklet_url, vote.
- Labels: **0 entailment=495; 1 neutral=498; 2 contradiction=495**.
- Claim languages DE/FR/IT: 495/497/496; reference languages: 455/569/464.
- Deterministic date-group train/dev: **1,157 / 331**. No test split used.
- **60/60 PDFs downloaded**, 75,379,251 bytes, in `/workspace/ost-booklets` (ignored,
  outside repo). Dataset directory ~38 MB, below 100 MB.

## Working
- Required `track_2a/` layout retained; CLI supports beginner and full-document
  advanced cases, page markers, exact original-language evidence, per-case metrics,
  valid error placeholders and ID-independent scoring.
- Env-configured OpenAI-compatible Apertus client, Public AI defaults, local vLLM
  configuration, custom User-Agent, and explicit mock backend.
- Scorer: overall/task/language/same-vs-cross macro-F1, evidence/page match,
  token sums, mean/p95 latency; malformed/missing/error/duplicate rows are wrong.
- Dockerfile and both Makefiles supplied; non-Docker `make run-local` verified.
- **16 pytest tests pass**, including PDF extraction and local HTTP protocol tests.
- All **331 beginner + 331 advanced dev cases** processed with mock, zero invalid
  outputs. Macro-F1 **0.174107** for both; this proves wiring, not Apertus quality.
  Reports: `track_2a/data/results/`. Beginner evidence match 0/214.

## Blockers / next steps
- No API key/model server: no real Apertus inference or paid API call made.
- Docker unavailable here: image/run configuration not executable-tested.
- Dataset has no page gold; reference strings do not exactly match PDF extraction.
  Advanced evidence metric is **unavailable**, with 214 nonneutral rows excluded.
- Before deadline: test Docker on a capable host, use an authorized free/local
  Apertus endpoint, annotate/validate advanced evidence pages, run 8B/70B dev
  baselines, verify tokenization/context limits. Mock tokens are estimates only.
- Local git initialized and committed only; no remote, push, signup or submission.
