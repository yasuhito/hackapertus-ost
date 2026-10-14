# PUBLIC60 protocol readiness

Frozen protocol SHA256: `719f36396fb3807862dd8403425462a47e0a1cb7de1bfa794404e405ce22e2e0`.

Offline preparation and verification passed: 10 manifests, 600 prepared cases, unchanged 60-case public selection, inputs, pages, candidate IDs, reminder and variant SYSTEM routes. No remote calls or credential reads. Pinned SDK mocks covered all 60 cases for both variants, including parent/child and parent continuation payloads: 360 mocked bridge requests.

Encoded UTF8 byte guard: 240,000 bytes for context and actual serialized API payload, checked before the base transport or credential access. Maximum contexts: v5 183,485 bytes, v16 183,489 bytes. Maximum actual SDK payloads: v5 191,817 bytes, v16 191,821 bytes. This is not exact native token measurement. Native provider context 262,144 tokens and returned usage validation remain unchanged. Legacy 66K fixture guard remains unchanged.

Each new exclusive job permits at most 300 POSTs and declares a 78,720,000-token reservation budget. Each separate five-job phase permits at most 1,500 POSTs. Actual monotonic batch cap is 5,400 seconds, checked before each job and each POST. Original case cap remains 300 seconds; an already running case may extend the soft batch bound by up to 300 seconds. No retry, resume, replay, partial-prefix grading or automatic candidate execution.

Checks: pinned-runtime pytest `.auto/test_public_validation.py track_2a/dev/format -q -W error::ResourceWarning`: 129 passed, 2 skipped. Shell syntax, Python AST syntax, `git diff --check`, real `--prepare-only`, and frozen `verify()` passed. Live HTTP and live official grading have not run. Initial SDK tests without runtime environment paths failed; pinned-path rerun passed. The first offline preparation exceeded a 240-second shell timeout, leaving no protocol or model jobs; the complete 600-second invocation passed with fresh workspaces and preserved earlier files.

Ready baseline command: `bash .auto/measure.sh --public-baseline`.

Only after the parent records the actual completed baseline: `bash .auto/measure.sh --public-candidate v16`.

Primary `public_Q_gain_v5` is unavailable until five complete inference jobs pass canonical/source/known-usage checks and official grading. Only then baseline emits measured-reference gain 0. Candidate gain uses the newly measured baseline and unchanged quality/noise gates; checks bind the current phase and protocol. Failures preserve fences and report unknown quality and unknown failed-request usage, not fabricated METRIC 0.

This is a public benchmark comparison, not a secret benchmark or private holdout. No adoption, scoring change, selection change, hypothesis, prompt or data change is introduced.
