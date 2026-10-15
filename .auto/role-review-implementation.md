# Role-review v1 implementation (not yet measured)

Files: `role_review_research.py`, `role_review_transport.py`, existing contract/worker/templates, fictional role-review tests, and **additive only** `measure.sh`/`checks.sh` dispatch. Production Root, historical transports/tests/jobs, data builder, research history and papers are unchanged.

## Controller

`--prepare-only` validates the parent adapter's completed manifest, canonical compact-JSON freeze, input/PDF/artifact/code hashes, precise documented-exposure scope, false universal-unseen claim, selection-file hash and hashed exclusion evidence. It never selects/replaces data or reads full source rows. Expected data are hashed, never copied to model workspaces. Missing/mismatched bindings fail closed.

Preparation creates ten exclusive **source-only** workspaces from current Root code plus local input cases/PDFs and new worker helpers. No old workspace copier/patcher/controller is imported. Baseline is unchanged simple v5; templates install once for candidate only. Dedicated credential-free subprocesses use the real pinned SDK/package fake backend on all60 cases in EACH workspace (600 cases); every native packet, including later parent report packets, is byte-checked and frozen. The actual original prepared context, selected page text, candidate IDs and unchanged v5 SYSTEM are audited. Runtime dependency closures/binaries, sources, helper/tests/dispatcher/protocol, native packets/schemas/prompts and all job manifests are bound before either arm can start. No ledgers are initialized by preparation.

`--baseline` / `--candidate` run five exclusive fresh jobs, never resume. Canonical Root Ledger/assembler remain authoritative. Candidate requires a complete, bound fresh baseline. No arm is graded before all five complete. The unchanged official grading API supplies all per-repeat metrics at its fixed commit. Research gates use unrounded mean Q, fixed .02 gain and strictly greater five-repeat noise, all F1 floors, mean Hit, total fallback and95% reviewer availability. Complete records include actual review states/reasons, literal-validation failures, actual parent-tool report coverage and report contents, three-role successful usage/call counts and separate physical attempts/unknown reservations. Unknown failed usage never becomes measured tokens or a known full cost.

Each arm has5400s plus at most300s for an ongoing case; no new case starts after5400s. No arm starts below5700s remaining. SDK case time and physical API timers/sockets clamp to Unix1792098000. Parent subprocesses use a new process group and kill the group on timeout at the earlier phase allowance/absolute stop, leaving exclusive job/phase fences. Cleanup and grading are permitted after the model deadline. Storage uncertainty/permanent errors/exhaustion fence the phase without retry/resume.

## New transport only

Root's unchanged Transport still performs request/native-tool validation and credential handling. A connection proxy captures at most65536 bytes of non200 error body, redacts the exact Bearer credential (and bare credential) before persistence, and records exception **types**, never exception messages/headers/keys. HTTP408/425/429/5xx retry; other statuses need explicit captured capacity/overload/rate-limit/temporary-unavailable evidence. Known grammar/schema/unsupported/auth/permission/invalid-input failures stop. Network timeout/reset/retryable errno is classified as transient network, not confirmed capacity; unknown transport is uncertainty and stops. Five total attempts, waits2/4/8/16, logical60s including waits, physical300/job and charged78720000 with262400 before each send remain fixed. Every before/result/wait is exclusive; an independent verifier reconstructs physical/logical bijection, all three roles, successful usage and unknown failed reserves. Successful model/usage validation failure and storage uncertainty never retry.

## Parent operational entrypoints

After final audit and all source files are final:

1. `.auto/measure.sh --role-review-prepare` (offline real-input export/freeze; parent only).
2. Parent initializes the changed mean_Q/higher target once, then uses run_experiment with `.auto/measure.sh --role-review-baseline`, followed immediately by log_experiment.
3. Same tool/log sequence for `--role-review-candidate` after baseline completes. No adoption follows a research keep.
4. `.auto/checks.sh` recognizes `mode=role_review` and runs `role_review_research.py --check-context`, reconstructing integrity and the saved comparison without inference or regrading.

The shared check context is written only after successful complete-arm grading. Original dispatcher archives already exist under `protocol-archive/role-review-before-*`. Do not edit controls or this document after freeze.

## Offline verification

- New controller/transport focused suite: **42 passed, 1 expensive test deselected** before final integration rerun. Includes real SDK third-role native packets, later packet guard, sixty fictional canonical records with physical accounting/report integrity, group timeout, complete-arm gating, all transient/permanent/network/budget/storage/deadline guards.
- Full ten-workspace preparation against a **temporary fictional bundle**, actual pinned Pi1.1.0/pi-subagents0.19.0, **600 actual SDK case paths**: **1 passed in293.86s**. No owner data, live transport, initialization or grading. Final adapter alignment is rechecked below in final handback.
- Existing role-review worker/contract/physical and new focused suites: **112 passed** before final adapter alignment.

No real-input preparation/freeze, live inference, experiment initialization/logging, official grading, git operation, network retrieval, dependency installation or production mutation was performed. Real bundle offline export and official live/grading paths remain parent actions; quality/cost/generalization claims are not established by these fictional tests.

### Final verification commands

Use `PI_PACKAGE_ROOT=/home/yasuhito/.pi/agent/install/releases/1.1.0/node_modules/@earendil-works/pi-coding-agent PI_SUBAGENTS_ROOT=/home/yasuhito/.pi/agent/npm/node_modules/@tintinweb/pi-subagents PYTHONDONTWRITEBYTECODE=1` with `/tmp/hackapertus-ost-contract/.venv/bin/python -Werror::ResourceWarning -m pytest -q`:

- `.auto/test_role_review.py .auto/test_role_review_physical.py .auto/test_role_review_research.py .auto/test_role_review_controller.py .auto/test_role_review_transport.py .auto/test_fullbranch_transport.py`: full fictional integration suite includes600 actual SDK case paths; final result in handback. Historical transport tests remain unchanged.
- `track_2a/dev/format --deselect=track_2a/dev/format/test_submission.py::test_saved_33_reproduce_then_normalize_27_reject_6 --deselect=track_2a/dev/format/test_strategy_c.py::test_c_freeze_same_source_and_only_parent_model`: **127 passed,1 skipped,2 historical fixtures deselected**.
- `bash -n .auto/measure.sh .auto/checks.sh`: passed. Removing only the new dispatch branches reproduces both archived dispatcher byte sequences exactly (checked with Python assertions).
- Production runner/SDK SHA256 remain `01dff6b930a546dbe1b0f8651cebe0cec5f4d3987eeecf2bb9309b4ecea799b6` / `d666a679c4ea291285f9cd416260e394d5aba8216fade1bf7e963dc225e422ec`.

Adapter alignment inspected only manifest keys/hashes and builder source, never owner expected/gold records; the fictional integration now uses the actual top-level provenance/selection-file/pin-freeze field conventions. Successful measurement emits canonical `METRIC key=value` lines, including mean_Q, all per-repeat F1/Hit/fallback/availability, successful three-role usage, physical retries and unknown reserves. Check-context reconstructs source/ledger/official metrics and baseline/candidate comparisons without regrading.

Final coder fictional suite result: **150 passed in279.59s**, including the complete ten-workspace/600-case actual pinned-SDK export/freeze fixture. No real bundle preparation or inference was run by the coder.

## Parent pre-inference review and fixes

The transport reviewer identified HTTP200 body-read retry ambiguity and a credential prefix leaking when the error-body read cut a key at64KiB. Parent reproduced both with credential-free Root transport/ledger tests. New policy conservatively fences any known200 response, even a body-read timeout, while pre-200 timeouts/resets and other declared transient statuses remain retryable. Error capture reads a key-sized bounded lookahead, redacts before UTF8 clipping, and removes a truncated final secret prefix; repeated-key compression at the read boundary is covered. In-progress socket and alarm deadlines are explicitly tested at3seconds before the absolute stop.

Parent controller review also reproduced missing quality enforcement in check-context for a small positive gain below.02, then made those preregistered gates fail backpressure. Reviewer availability now requires a validated report actually present in the parent's observed input, not merely generated by a helper. The frozen runtime now includes the official evaluator commit/clean-file check and scoring dependency closure before model spending.

Parent independently ran the unchanged official scorer on five complete SYNTHETIC60 prediction/expected sets through the actual new grade_arm path; F1A/F1B/HitA all1 and grading-replay refusal passed. No selected public gold was displayed or real model results graded. Combined credential-free suite, including data preparation tests and the600 actual-SDK fictional inputs: **166 passed in283.96s**. All fixes precede real ten-job preparation and any inference. Original production runner/SDK and historical transport/controls remain unchanged.
