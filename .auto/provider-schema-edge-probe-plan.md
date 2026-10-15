# Prospective fictional edge probe v1

This is a NEW workload and the first valid baseline for the NEW target
`edge_schema_contract_violations` (integer 0..12), not an improvement from the
previous toy workload's measured zero. Parent initializes that target after
preparation. No production, PUBLIC60, gold, historical responses, official grader,
NLI quality, significance or deployment claim. At zero, stop, do not repeat.

Six fixed pages are exactly `Fictional marker A.` through `Fictional marker F.`.
Full span objects come only from unchanged Root runner `candidates(pages, False)`.
IDs in physical page order, all 36 characters (actual unchanged generator output,
not the initial 37-character estimate):

1. p0001-o0000000-e0000019-6ac35b55a6f1
2. p0002-o0000000-e0000019-0515f21e5a7d
3. p0003-o0000000-e0000019-32f26716bd8f
4. p0004-o0000000-e0000019-9dc253aee5da
5. p0005-o0000000-e0000019-f4fc46267119
6. p0006-o0000000-e0000019-580f92255da8

Fixed order: Apertus-v1.5-8B then Apertus-v1.5-70B. For each model, cases
(label 1, first two IDs), (label 0, first five), (label 2, last five), each
simple then complete_branch. Exactly 12 prospective POSTs. No variants, tuning,
retries, resume, replay prefix or provider discovery. The task is only copying
requested_arguments, not deciding labels. User JSON contains source_spans and
requested_arguments. System and submit descriptions are identical to the original
probe. Both arms have identical messages and payload fields except schema.
Simple is unchanged Root schemas(ids, child=True)[0] parameters. Complete branch
retains every root field and adds two full self-contained copies: neutral label
[1], nonneutral label [0,2] with candidate_ids minItems 1. All copies retain the
six-ID enum, maxItems 5, types, required fields and additionalProperties false.

Independent Pi 1.1.0 TypeBox full native validation uses original score semantics.
Schema violations are nonfatal outcomes: collect all 12. Report original compliant
exact-copy mismatch counts AND unmasked all_exact_copy_mismatches, per model/arm,
with missing fields, truncations, usage and latency. No masking of malformed output.
The five-ID typed output validates offline; 256 is a prospective output clamp,
not proof the provider will fit it.

Unchanged actual usage caps: input 1000, output 256, total 32768; request 60s,
socket 45s, phase 900s. New per-request reservation 4096 conservatively bounds
messages+tools serialized bytes+128 at <=3840. Actual measured maximum is 2824.
If exceeded, stop OFFLINE before freeze, never drop span fields or raise guards.
12*1256=15072<32768 and 11*1256+4096=17912<32768, so every reservation fits even
at worst allowed preceding actual usage. 12*4096 need not fit: actual input/output
caps remain lower. No cap increase or monkeypatch of Root transport guards.

Fresh protocol pins current entrypoints, new helper/tests/plan, original helper
and recovery safeSave dependencies, Root sourcepack including source_spans.py and
predict.py, model/default API configuration, package files, validator tree and
runtime binaries. No historical reference-pin chain. Transport is original probe
Transport with frozen payload hash allowlist, fixed default HTTPS origin and
credential source, read only during explicit execution. Root application native
transport guard is intentionally not used by this fictional diagnostic client.

Private fsynced captures retain request/payload hashes and raw response, model
identity and usage. Unknown/inconsistent usage, API errors, wrong identity,
transport or storage failures are fatal: preserve inflight, STOP, no resume.
Immutable exclusive control and job identities; checking recomputes captures and
validation without API. Current source mutation is fatal before any transport.
Current dispatchers archived before additive edits; immutable proof hashes cover
production sources, old helpers, archives, controls and historical job files.

Run new offline tests plus unchanged original53/recovery10/closure22 in pinned
contract venv with ResourceWarning errors and no network/credential access.
Only after green tests, `.auto/measure.sh --provider-schema-edge-prepare` freezes
12 payload hashes offline without creating a job. Parent alone initializes the
new target and decides any execution. Ready execution command, not run here:
`.auto/measure.sh --provider-schema-edge`.
