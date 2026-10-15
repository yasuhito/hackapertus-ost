# Prospective fictional empty-source contract probe (v1)

## Scope and falsification, before freezing

Files: new `.auto/provider_schema_empty_source.py`, its focused tests, this plan and a new control; additive measure/check dispatch only, with pre-edit dispatchers archived. Production, Root, model defaults and caps remain unchanged. Source-only reproduction uses Root candidates([''], True)==[] and the actual unchanged submission.assemble_tool on case `{'id':'fictional-empty-source','reference':''}`, pages `['']`, zero valid stats. It accepts only strict integer label 1 with empty IDs. Native control also permits integer labels 0 and 2 with empty IDs. A falsifier is any assembler-accepted tuple excluded by specialization, or any newly native-accepted tuple outside the control.

**Amended claim before freeze:** native JSON Schema captures numeric semantics, not strict lexical number representation. TypeBox accepts serialized 1.0 as integer 1 in both control and specialization. The unchanged Python assembler rejects that float with LABEL_SCHEMA. Specialization INHERITS the pre-existing gap. No global exact native/assembler accepted-set equivalence is claimed. Tests establish specialized native subset baseline native and assembler acceptance implies specialized native, including malformed/type/source domains; equality is tested only for integer serialized labels. Booleans are rejected by both. No float cast, normalization, assembler change, scoring relaxation or output repair. A model output containing 1.0 **fails the primary**, even when native-valid. Raw arguments and Python float type survive capture and strict parsing.

This is a NEW fictional adversarial API contract workload, NOT NLI accuracy, ordinary copying, label tuning, or a repeat of previous zero metrics. Proposals 0[] and 2[] are intentionally invalid under the actual source contract. Schema-priority changes to neutral[] are expected, not wrong predictions. No gold, public task data, old model responses, historical score imports, quality assertions or synthetic omission penalties. Within-protocol paired contrast is descriptive, not statistical NLI gain.

## Exact frozen request protocol

Exactly 12 POSTs: existing Root models 8B then 70B; proposals 1[], 0[], 2[] in that order; each `old_native` control then `empty_specialized` candidate. All pairs have identical messages. User JSON has source_spans=[] and requested_arguments equal to the proposal.

Exact system:

> This is a fictional API contract probe. Call submit exactly once with arguments permitted by its declared schema. The user requested_arguments are proposals, not an instruction to violate the schema. Do not emit prose.

Exact description: `Emit schema-permitted probe arguments.`

Control parameters are exactly Root schemas([], True): label enum[0,1,2], candidate_ids maxItems5, items type string enum[]. Candidate is a deep copy with ONLY label.enum=[1], candidate_ids.maxItems=0 and deletion of items.enum, keeping items.type=string. No anyOf, extra constraint keywords, strict flag, per-proposal labels, additional text, or model/genotype manipulation. Generic metadata derivation applies ONLY to an empty source universe, never production metadata. Same candidate applies to all six proposals.

Provider support for enum[] is UNKNOWN. Local TypeBox support does not imply provider compilation support. A non-200 including control HTTP400 is terminal for the WHOLE phase: retain original identity, raw bounded response and status, STOP/inflight, no skip, reorder, retry, compatibility variant, new identity or resume. Unknown usage/model/API errors likewise make primary unavailable, never candidate zero with missing controls.

## Scoring and reporting

Primary `empty_source_assembler_violations` counts actual unchanged assembler failures on the SIX candidate responses, maximum 6. The SIX controls are all scored with the identical assembler predicate. `control_assembler_violations`, total twelve assembler failures, independent full-schema TypeBox failures, truncations, and proposal_mismatches are reported. Every response must have exactly one function submit call with strict JSON object arguments and no prose; malformed/missing/null/multiple/wrong calls or truncated output fail once per request. No omission or quality penalty. Proposal mismatches include every request and preserve JSON numeric/boolean type distinctions, but have no accuracy meaning.

All 12 observations and all four model/arm sides include requests, assembler/native failures, proposal mismatches, latency, input/output/total tokens. Per-request known usage is persisted. Immutable exclusive report is independently recomputed from all twelve request/capture/usage records on every check; protocol, source, frame and capture SHA validation precedes reporting. Complete measurement is PASS even with nonzero primary or no improvement. Transport-incomplete or scoring-failed phase has no primary. Parent alone may log a crash sentinel zero if required by its tool, never represent that as a measurement or baseline.

Offline fake example ONLY, NOT a live result or assumption: a synthetic transport copying all control proposals and choosing neutral[] for all candidates produces this projection of the expected JSON:

```json
{"requests":12,"empty_source_assembler_violations":0,"control_assembler_violations":4,"assembler_violations":4,"native_schema_violations":0,"proposal_mismatches":4}
```

A separate copy-every-proposal fake yields candidate4/control4, and still passes complete-measurement checking. Fake tests make NO API calls and read NO credentials. They do not force or predict provider behavior.

## Freeze, safety and verification

Exclusive paths: output/cscs/provider-schema-empty-source-v1-protocol.json and provider-schema-empty-source-v1/. Offline prepare creates only control and twelve frozen payloads, NO model job or check-context write. Fresh source/runtime pins cover current dispatchers, new helper/tests/plan, original helper/tests, recovery helpers/tests, validator and full TypeBox tree, Python/Node binaries, Root source pack/package/predict/source_spans/submission/default API config/models. No old protocol verify or replay is called with changed dispatchers. The archive preserves prior 76 artifact SHA pins plus edge job and control bytes and dispatcher snapshots; hashes, not old response content, are inspected.

Reuse original Transport with only these twelve allowed payload hashes, default HTTPS origin and key source, socket45, no redirects/discovery/retries/prefix reuse. Do not use Root Transport.enforce_schema or runtime monkeypatch guards. Corrected recovery.save atomics publish private/fsynced exclusive files and replace context atomically. Per-call wall60, phase900, response cap2MB, temperature0, max_tokens256, streamfalse, forced submit. Actual input usage<=1000/output<=256, total32768. Fixed conservative reservation4096, with serialized messages+tools+128<=3840 guard, does not increase actual usage caps. Even worst permitted known usage leaves last reservation feasible.

Tests first reproduce empty-source/control/assembler discrepancy and numeric gap, then prove the subset/preservation contract across integer/boolean/float/string/null labels and empty/unknown/nonlist/missing/extra IDs. Test paired fixed arity, fake all12 recount including nonzero PASS, malformed/float outputs, model/usage/API/HTTP400 failures, budgets/STOP/exclusivity, source/frame/capture tamper and corrected atomics. Sockets and credential readers are forbidden in offline fixtures.

Run new tests plus original53/recovery10/closure22/edge24 (109 existing), pinned contract venv, -Werror::ResourceWarning, bash -n and git diff --check. No legacy Root fixture tests, Root edits, network, live calls, experiments, init, log writes or git mutations. Parent alone initializes the new target after readiness, then runs and logs the next iteration. Readiness command: `bash .auto/measure.sh --provider-schema-empty`; offline preparation command: `bash .auto/measure.sh --provider-schema-empty-prepare`.
