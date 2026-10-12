# Local development measurement with Roast

Ruby owns stages, budgets, resume/cache, provenance, usage and statistics. Python owns PDF extraction, physical pages, context selection and the NLI/quote contract. The submitted Python CLI remains the Apertus implementation. This recipe has only mock and frozen-history replay providers. It never sends a new remote request, reads API keys, or runs a live hillclimb.

## Versions and installation

Verified Ruby 3.4.10, Bundler 4.0.10, Roast 1.3.0, ruby_llm 2.1.1. `Gemfile.lock` pins all 37 gems including checksums. Ruby >=3.3,<4 is required. ERB is explicit because upstream Roast omits the bundled-gem dependency on Ruby 3.4. Python requirements stay pypdf 6.1.1 and pytest 8.4.2. Select Ruby 3.4.10 on PATH. Dependencies are isolated in repository `vendor/roast/`; no global gem/config changes.

```sh
cd ~/Work/hackapertus-ost
python3 -m venv .venv
.venv/bin/pip install -r track_2a/requirements.txt
# After review of the pinned lock, download/install only these dependencies:
track_2a/dev/roast/bundle.sh install
make roast-version
make roast-test PYTHON="$PWD/.venv/bin/python"
make test PYTHON="$PWD/.venv/bin/python"
make roast-smoke PYTHON="$PWD/.venv/bin/python"
```

The current verified environment uses `/tmp/hackapertus-ost-contract/.venv/bin/python` in place of `.venv`. Dependencies have already been installed locally. The historical replay paths, `evaluation/fixed18_assistant_verified.jsonl`, and `pi_trace.mjs` are local-only artifacts excluded from Git; obtain the approved nonsecret artifacts separately before using those examples. Clean-checkout mock tests do not require them. Repeated smoke/replay commands resume without creating extra model attempts. A changed artifact is rejected; choose a fresh output directory for a new experiment. A workflow flock prevents concurrent duplicate execution.

## Frozen replay and comparison

The external history is an existing development dataset, not a public portable fixture. Paths below are local evidence dependencies; absence is an explicit error. Do not point the recipe at final holdout cases.

```sh
ROAST_MODE=replay ROAST_STRATEGY=vote_pages \
ROAST_INPUT=/tmp/hackapertus-ost-takeover/gpt-dev54/cases.jsonl \
ROAST_GOLD=/tmp/hackapertus-ost-takeover/gpt-dev54/gold.jsonl \
ROAST_REPLAY_ROOT=/tmp/hackapertus-ost-takeover/gpt-dev54 \
ROAST_ANNOTATIONS="$PWD/track_2a/dev/roast/evaluation/fixed18_assistant_verified.jsonl" \
ROAST_OUTPUT="$PWD/output/roast/replay54-v2" \
ROAST_PYTHON=/tmp/hackapertus-ost-contract/.venv/bin/python \
track_2a/dev/roast/bundle.sh exec roast execute track_2a/dev/roast/workflow.rb

track_2a/dev/roast/bundle.sh exec ruby track_2a/dev/roast/import_history.rb \
 /tmp/hackapertus-ost-takeover/gpt-dev54 output/roast/history81
track_2a/dev/roast/bundle.sh exec ruby track_2a/dev/roast/compare_history.rb \
 /tmp/hackapertus-ost-takeover/gpt-dev54 output/roast/history81 \
 output/roast/replay54-v2 track_2a/dev/roast/evaluation/fixed18_assistant_verified.jsonl
```

Outputs: config/provenance, per-stage events and content hashes, observations with raw usage, schema/quote checks, A/B macro-F1/class metrics/confusion, grouped bootstrap 95% intervals, scoped reference-page diagnostics and paired historical comparison. Historical source events are checked against saved usage, including one pre-send setup failure; B is shared and counted once. Source model/effort/prompt/data hashes must agree before replay. Case, attempt and run IDs prevent duplicate usage aggregation.

Budgets: new remote calls/tokens always zero; mock cases <=108, retries <=2 (default zero, only explicit transient exit75), command timeout120s, run600s, cache repeats <=3. Exceeding a budget stops. Output-token budget is zero for live calls because live is unavailable. Timeout/failed usage is unknown, never zero-filled. Mock/replay repeats are plumbing checks, not independent model trials. The protected date is 2024-06-09; the approved replay manifest rejects it before case reads. Generic mock inputs must not contain gold fields; replay is pinned to the approved source hash.

## Timing and usage

`Backend('openai', observer=...)` records request-start and response-read completion around urllib, then parses JSON outside that interval. Local fake HTTP tests verify raw usage presence/absence, request failure, measured wait, response identity and no header logging. Default CLI output is unchanged. Request wait includes transport and server time; it is not server inference alone. Historical Codex subprocess time cannot reconstruct exact request wait, so API wait stays null. PDF/context/selection/replay timings are separate local measurements; the cached local benchmark is preserved outside this recipe.

Codex CLI and Apertus chat input totals include cache-read; output includes reasoning. Their total is input+output, without adding those subsets. Pi input is fresh input; canonical input adds cacheRead+cacheWrite; output already includes reasoning. Missing raw usage/reasoning remains null. Pi terminal `message_end` is counted once, ignoring `message_start` defaults and repeated `agent_end`. Error default zeros are not measurements. `provider_probe.rb` is parser/isolated command preparation only. `pi_trace.mjs` is a version-specific unexecuted extension prototype; live Pi and actual streaming wait are unverified and excluded from completion claims.

## Evidence and decision limits

All 18 nonneutral fixed-source rows have assistant direct-source reviewed reference-page mappings; 9 neutral rows need no page mapping. Every reviewed PDF/page text hash must match. The first-five exact-quote/reference-page hit diagnostic covers only these verified cases. It does not certify semantic sufficiency, exhaustive equivalent pages, official scoring or human review. Remaining development nonneutral rows:127. Gold is consumed only by grading, never included in inference messages.

Historical A raw labels were all correct, but full context produced two invalid quotes under the strict pipeline: macro-F1 .960784 vs selected1.0; B1.0 in both. Keep selection as a development candidate; promotion waits for Apertus and independent QA. Only two date groups are in this 54-case comparison, so bootstrap intervals are not generalization proof. Official composite remains unknown without Apertus, organizer proxy and peer normalization. GPT development eligibility is unconfirmed.

See `COVERAGE.md` and `EVAL_HILLCLIMB_ADAPTATION.md` for completion boundaries. No container, report PDF, submission or external publication is performed here.


### Final local observation

The assistant-reviewed reference-page diagnostic is full16/18 vs selected12/18. Selection has six page-scope losses and two gains. Its quotes remain exact on their actual physical pages, but those alternative pages are outside the annotated reference-page scope. These six cases are independent-QA flags, not automatic semantic evidence failures. They are preserved in `comparison.json`; they are not cleared by inventing equivalent gold pages. Runtime/report promotion remains pending.


### Cache integrity revision 2

A completed stage is reused only after its own artifacts, every upstream artifact and the original input/PDF/replay-source content hashes pass validation. This runs before any cache-hit return, including grade. Changes to source files stop with nonzero exit rather than resetting the fixture or serving an old result. Intentional source changes require a fresh output directory. Gold/annotation changes invalidate only grading; inference remains reusable.

Interrupted per-case results have an atomic, fsynced cache file and a separate index anchoring its SHA256. Resume also checks cache identity/configuration, raw response, provider/mode/model/effort, raw usage and derived label/evidence/token fields against the deterministic mock or original replay records. Rehashing a corrupted cache alone does not make fabricated usage/labels valid. Replay metadata usage must match the raw terminal event. Completed-stage integrity includes the index, budget ledger and every case-cache file.

Attempt reservation is saved before allocating a new case. A durable indexed result with an unfinished reservation recovers without a new call; an orphan/unresolved reservation stops to avoid guessing whether a prior call happened. Local crash injection covers reservation, result write and index write boundaries. General remote-provider exactly-once behavior is not proven; this recipe still has no live provider.

Revision 1 output caches lack these anchors and are rejected. They are retained, without deletion or migration. Default mock output is now `output/roast/smoke-v2`; use `output/roast/replay54-v2` for this revision.

Independent QA directly reviewed all six alternative-page citations and judged them correct additional evidence. The historical reference-page diagnostic remains16/18 vs12/18 because its scoped mappings were not expanded. This is an independent assistant review, not official scoring/human gold. Cache integrity fixes are pending fresh independent QA against the new patch hash.

### Source-ID protocol and canonical output

The current mock backend returns only label and source span IDs. `messages_for_pages` builds the same source-ID payload after selection; extraction explicitly keeps all physical pages so a full or vote-page strategy is applied once. The model's ID JSON is decoded by `restore`. Final `{id,label,label_name,evidence:[page,text],metrics}` output is checked by `validate_prediction`, not sent back through the raw model parser. Canonical checks retain exact source/page, item/character and finite metric requirements.

Replay reconstructs the original prompt in an isolated local process using its frozen engine and helper sources. Both legacy `{page,text}` histories and new source-ID histories are accepted only after prompt, input/source hashes and raw terminal usage agree. Legacy histories retain their frozen decoder; they are not relabeled as new ID inference. Source-ID histories use the current deterministic citation decoder after the historical inference prompt is verified unchanged. Missing or mismatched history never invokes a model. A source-ID run directory may use `calls/<id>` and a recovered completion metadata file; its prompt hash must still agree with both the manifest binding and the actual saved prompt.

Source IDs remain unchanged source-offset anchors. Citation context closure returns the full original reference for B, and full physical pages for A. A standalone committee/government heading may attach its contiguous two-page source block; blank/unprovided pages and different standalone speaker headings stop expansion. Body mentions do not define speakers. No claim, label, gold, reference_string or case ID controls expansion. All returned words are original source substrings; over5000 characters on an A page or more than five resulting items is a hard failure. This bounded source-context rule improves attribution/antecedent coverage, but does not prove semantic relevance or official scoring. It can lengthen citations. Histories and measured original outputs remain preserved; changed citation outputs are offline decoder replay, not new generation or stability trials.

Replay source manifests now also pin current engine helper sources and frozen engine/helper files. Engine cache identity includes all source Python modules, so changing a helper cannot silently reuse a completed stage. Choose a fresh output directory for this revised protocol. No live API provider was added.
