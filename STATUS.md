# Status — deadline 2026-10-16

## SUBMITTED 2026-10-16 18:50 JST at commit f82eafb (master = main)
- Report: `report/main.pdf` (English; the Japanese draft was retired after submission, see git tag submission-2026-10-16). Repository https://github.com/yasuhito/hackapertus-ost.
- Configuration: strategy R, claim_paragraphs with section prior, escalation on; Docker image verified.
- Do not change the submitted configuration retroactively; later work belongs on a new branch.

## 2026-10-16 18:00 JST baseline: paragraph context + section prior + escalation on strategy R
- Section prior (commit f3e7661): the claim's attributive opening (summary / committee / council /
  vote text / if adopted) selects the booklet sections whose paragraphs are ranked first.
  Production runtime, 3 sets: Task A F1 0.910, Task B F1 0.922, Hit@5 0.808, 7,137 tokens, 4.0 s per case.
- Rejected: an extra SYSTEM sentence on recommendation direction (fixed 4 errors, added 8).
- Docker image built and run end to end on 2026-10-16 18:10 JST (249 MB, weights baked in, 6-case smoke
  through `make run` with injected BASE_URL/API_KEY). Branch merged to master.

## 2026-10-16 16:00 JST: paragraph context + escalation on strategy R
- Image default CONTEXT_SELECTION=claim_paragraphs: the vote's pages are split into paragraphs,
  ranked by BM25 over an Apertus 8B translation of the claim fused with a local static multilingual
  embedding (model2vec potion-multilingual-128M int8, baked into the image at build), top 8 plus
  neighbours sent; unsupported non-neutral answers are re-run once on the full vote pages.
- Production runtime on DEV60 / PUBLIC60 / 確認用60 vs the full-vote-pages default:
  Task A F1 0.881 -> 0.903 (avg), Hit@5 0.746 -> 0.812, tokens per case 10.9k -> 7.6k, 3.7 -> 4.0 s.
  Details: `docs/single-call-results-2026-10-16.md`. All sets are exposed; single runs.

## 2026-10-16 12:40 JST baseline: strategy R, one native submit call per case (commit after 7ee44e6)
- Task A (booklet) answered by Apertus 70B, Task B (reference) by Apertus 8B, no child session.
  The 70B parent had copied the 8B child's label in 420/420 recorded cases, so the two parent
  calls (63% of tokens) added no judgment. See `docs/single-call-results-2026-10-16.md`.
- Versus the 70B+8B version on DEV60 / PUBLIC60 / 確認用60: Task A F1 0.733/0.869/0.797 -> 0.875/0.967/0.804,
  Task B F1 0.815/0.931/0.929 -> 0.853/1.000/0.933, Hit@5 0.68/0.65/0.625 -> 0.74/0.75/0.75,
  tokens per case about 24k-29k -> 11k, time 6-7 s -> 3 s. Single runs; sets are all exposed.
- `make run` defaults to PIPELINE=R; C (70B+8B) and S (one model) remain selectable.

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
