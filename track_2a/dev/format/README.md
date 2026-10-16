# Bounded format comparison

A is deterministic text parsing plus source restoration. B uses real Pi 1.1.0
SDK sessions and native OpenAI tool calls: parent `subagent`, child `submit`
(recommendation only), then authoritative parent `submit`. The child is launched
by installed `@tintinweb/pi-subagents@0.19.0`'s actual `runAgent()` API, not a
manual session disguised as that package. C uses the same protocol and frozen
source/question, with authoritative `swiss-ai/Apertus-v1.5-70B` parent and
source-only `swiss-ai/Apertus-v1.5-8B` child. B keeps its same-model child.
There are no task/model selectors, additional tools, deeper agents or retries.
All three use
`track_2a/src/submission.py`. Legacy predict/Client defaults are unchanged.
This does not establish CSCS/proxy native tool support or model accuracy.

## Contracts

Text: one JSON object with exactly `label` and `evidence`, no duplicate keys.
Labels accept integer 0/1/2 or exactly strings `0`, `1`, `2`, `entailment`,
`neutral`, `contradiction`. Evidence is a homogeneous string-ID array or
an array of exact `{ "span_id": "ID" }` objects. Maximum five IDs. No trimming,
ID completion, hash correction, duplicate removal, quotation generation or gold.

Tool: exact `{ "label": 0, "candidate_ids": ["ID"] }`, integer enum 0/1/2,
case-specific literal ID union, unique items, maximum five, no extra keys.
The TypeBox declaration and Python assembler both validate. Python also checks
raw arguments before Pi's coercing validator; string tool labels stay invalid.
Source membership and existing page/speaker closure are authoritative.

Native HTTP declarations are a wire-only compatibility projection: integer label
enum, string ID enum array with maxItems=5, exact required fields and no additional
properties. They omit anyOf, const and uniqueItems; local Pi/Python still reject
unknown labels/IDs and duplicate IDs. Python compares native parameters to the
canonical wire schema exactly. Subagent has only fixed `mode: "source_only"`
(Pi literal, native string enum), no task/model/path/source arguments. The parent
prompt/tool description shows compact `{"mode":"source_only"}` without blank lines.
Parent/child submit tails explicitly override raw evidence JSON instructions:
exactly integer label and candidate_ids, no evidence/label_name keys. Frozen
source/question messages are unchanged.
This is a candidate for the observed HTTP400, not proven server compatibility.
Truncated tool calls with finish_reason=length still produce flagged fallback;
there is no new length/empty-object repair loop. Known usage remains accounted.

Canonical output has exactly `id`, `label`, `label_name`, `evidence`, `metrics`.
Evidence contains only original `page`/`text`; B page is null. Metrics contains
nonnegative integer `input_tokens`, `output_tokens` and finite nonnegative
`inference_time_ms`. No accepted submit means canonical neutral plus
`NO_ACCEPTED_SUBMIT` diagnostics. Evaluation JSONL adds `error`, so neutral
fallbacks are wrong even against neutral gold. Text from B is never scraped.

## Offline checks

No dependency installation is required when the approved Pi installation exists:

```sh
export PI_PACKAGE_ROOT=/path/to/node_modules/@earendil-works/pi-coding-agent
export PI_SUBAGENTS_ROOT=/path/to/node_modules/@tintinweb/pi-subagents
PYTHONDONTWRITEBYTECODE=1 /tmp/hackapertus-ost-contract/.venv/bin/python \
  -m pytest -q -p no:cacheprovider track_2a/dev/format
python3 track_2a/dev/format/run_comparison.py --prepare-only --strategy A
python3 track_2a/dev/format/run_comparison.py --prepare-only --strategy B
python3 track_2a/dev/format/run_comparison.py --prepare-only --strategy C
PYTHONDONTWRITEBYTECODE=1 python3 track_2a/dev/format/offline_check.py \
  --strategy B --job /tmp/ost-format-offline-B
PYTHONDONTWRITEBYTECODE=1 python3 track_2a/dev/format/offline_check.py \
  --strategy C --job /tmp/ost-format-offline-C
```

The offline CLI freezes the approved portable dev54, uses synthetic neutral
responses (not gold), denies Python network/key reads and Node network/global
config discovery, and executes actual SDK parent/child sessions. Its metrics
are synthetic and must never be reported as inference accuracy or latency.
Use a new dedicated offline directory after code changes. Historical 33-raw
regression checks are skipped on clean machines without saved evidence.

`package.json` and generated `package-lock.json` pin dependencies. `npm ci` is
for separately authorized dependency/image preparation. The explicit override
is only a package-code location. No personal absolute imports are committed.
Node 26.8.1 or newer in the 26 series is required for native TypeScript loading.
The pinned SDK lacks a public AuthStorage export; the bridge imports its
1.1.0 internal module, so upgrading Pi requires fresh compatibility QA.

The package adapter uses the pinned published `dist/agent-runner.js` and its
agent registry, with exact child Model object and shared in-memory ModelRuntime.
Node resolution hooks align package host peers with the same Pi 1.1.0 modules.
Each Python-owned `/tmp/ost-pi-*` directory contains only private noncredential
settings and an empty child workspace. Package discovery stays there; auth/model
files are forbidden by the offline guard even in that temp directory. Only the
explicit `safe-submit-child.ts` plugin loads, with built-ins, skills, parent
history, persistent sessions, memory and nested subagents disabled. Package git
probes receive an execution-denying host facade; no Git process is run.

Package maxTurns/grace are soft (grace cannot be zero in 0.19.0). The adapter
uses soft maxTurns=3/grace=1 to avoid steering after a valid second-turn repair;
the provider and Python ledger still enforce two child completions. Successful
submit terminates without follow-up. Package-generated cwd metadata is normalized
before sending, so confirmed-attempt replay is stable across private temp paths;
supplied source/claim text is never normalized. Package start/completion events
record `runAgent`, version, exact model/provider and active submit-only tools.

## Parent-operated live comparison only

```sh
python3 track_2a/dev/format/run_comparison.py --user-run --strategy A --repeat 1
python3 track_2a/dev/format/run_comparison.py --user-run --strategy B --repeat 1
python3 track_2a/dev/format/run_comparison.py --user-run --strategy C --repeat 1
python3 track_2a/dev/format/run_comparison.py --user-run --strategy C --repeat 2
# A/B can also repeat with --repeat 2 for independent round directories.
```

`--repeat` is the round index, not an automatic loop. `--job DIR` overrides the
new directory. Do not use any legacy directory, delete fences or change job
identity to bypass a stop. Only explicit `--user-run` creates a CSCS transport;
its key is read internally in Python, never supplied to Node. No HTTP retries.

A: at most 216 POSTs. B: at most 540 POSTs, parent 3/child 2 per case, depth one,
one delegation, at most two submit attempts per session. C: only 54 owner-70B
cases, at most 270 POSTs (parent 3 + child 2 per case), with fixed 70B/8B roles.
C round directories are `output/cscs/format-C-r1` and `format-C-r2`. All runs have a
6,000,000-token budget and reserve 262,400 before each POST. Output cap 256,
request wall cap 60 seconds, socket 45 seconds, case cap 300 seconds. Only
schema/source validation permits one repair, never gold/semantic quality.

Each job has flock, manifest/code/source/schema hashes, fsynced immutable raw
attempts, state, completed case markers, summary models map, and
`8b-predictions.jsonl`/`70b-predictions.jsonl` for local scoring. Separate
`*-canonical.jsonl` files omit error flags. All parent/child/failed known usage
is counted. C filenames retain the `70b-` case-owner prefix; attempt `model`
is the owner, while `request_model` records the actual transport target.
Manifest/summary `role_models` records the fixed pair and summary
`calls_by_actual_model` separates transport calls. Whole-case metrics sum
parent, child and repairs exactly once. Response model must match the actual
target; invalid role/target pairs stop before reserving or sending. Old B
attempts lacking `request_model` remain replayable with their owner as target
(subject to unchanged manifest/code identity). Resume replays confirmed raw attempts without sending them again;
changed payloads fail. Inflight, state.pending or STOP.json fences block all
resume after uncertainty, deadline or storage failure. Unknown usage is not
filled with zero. API wait and case mean/p95 are separate. Comparison case
wall measures processing of frozen context; dev54 PDF/context freeze is outside
that timing. Submitted runtime includes per-case context preparation.

## Submitted JSONL runtime / proposed Docker

```sh
# With BASE_URL and API_KEY injected by the organizer, not host credentials:
python3 track_2a/dev/format/runtime.py --pipeline B --input INPUT --output OUTPUT
make run PIPELINE=B LLM_MODEL=swiss-ai/Apertus-v1.5-8B \
  INPUT_DIR=/path/to/approved/input INPUT=/data/input.jsonl OUTPUT_DIR=/path/to/new/output
make run PIPELINE=C LLM_MODEL=swiss-ai/Apertus-v1.5-70B \
  INPUT_DIR=/path/to/approved/input INPUT=/data/input.jsonl OUTPUT_DIR=/path/to/new/output
# Makefile and Dockerfile default: PIPELINE=R, one native submit call per case,
# booklet cases on Apertus 70B and reference cases on Apertus 8B. PIPELINE=S is
# the same single call with one model (LLM_MODEL). PIPELINE=A selects the same
# assembler's text path. CONTEXT_SELECTION=claim_pages (default vote_pages) narrows
# each booklet case to the vote's opening spread plus the pages of the eight spans
# closest to the claim and their neighbours; cross-language claims are first
# translated into the booklet language by Apertus 8B (one short call, recorded in
# tmp/format-runtime/translations.jsonl and counted in the case's tokens).
```

The Node executable is resolved before child environment sanitization, including
Docker's `/usr/local/bin/node`. Submitted model selection accepts LLM_MODEL or
LLM_NAME only when casefold matches the two canonical allowed IDs; thinking and
unknown models remain refused. C defaults to canonical 70B when neither
variable is set and rejects an injected 8B parent before input/key reads.
Makefile includes C in agent-image/read-only selection. Runtime adds the same protocol reminder as dev.
Submitted transport requires injected BASE_URL/API_KEY for every parent/child
call. It never reads a host key or uses a default CSCS endpoint. Output is
canonical JSONL; sibling `.diagnostics.jsonl` and `.evaluation.jsonl` files
retain fallback flags. Durable state is under the output directory's `tmp/`.
Request and token budgets scale with the input size (five requests per case); a case whose requests fail yields the neutral fallback with its error in the diagnostics sidecar. Use a dedicated output directory; changed
inputs/code/output refuse reuse. Runtime sources hash every local Python, TS,
MJS and JSON dependency/entry/plugin file, including package and lockfile, so
changed child code cannot resume an existing deployment. Empty input produces
an empty output.

Dockerfile.agent is a proposed Linux amd64 CPU image with pinned Node/Pi,
vendored pypdf, no credentials, no runtime downloads, read-only root and writable
/output and /tmp. Build-time registry access is required. Docker build/run has
not been validated because the host daemon is inaccessible. SDK fake-provider
checks are not Docker, CSCS or organizer proxy validation.
