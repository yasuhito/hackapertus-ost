# role_review_transport audit (read-only, no tests run)

Scope: `.auto/role_review_transport.py`, the worker/execute/subprocess_group deadline paths in `role_review_research.py`, Root `Transport`/`Ledger.post`, and `test_role_review_transport.py`.

## Findings

- **[medium] `role_review_transport.py:28` classify: a known HTTP 200 whose body read hits a timeout or reset gets retried**
  - Trigger: status 200 arrives, then `ResponseProxy.read` raises TimeoutError, ConnectionResetError or ECONNRESET. classify returns `transient_network`, the code sleeps 2s and sends a second POST. verify() accepts the record because it uses the same classify.
  - Impact: breaks rule (a). A known 200 with unknown or invalid usage must fence, but here the server may already have generated and billed a response, and it is regenerated. Reservation accounting stays conservative. `test_role_review_transport.py:140` locks this behavior in.
  - Fix: delete line 28, so status 200 falls through to `permanent`. Then rewrite the test to expect 1 POST and both inflight fences.

- **[low] `role_review_transport.py:69-75`: redaction runs after the 64KiB cut**
  - Trigger: a non-200 body echoes the key so that the key straddles byte 65536.
  - Impact: the start of the key is written to `error_excerpt` unredacted.
  - Fix: `read(BODY_CAP + len(secret))`, redact, then truncate to BODY_CAP.

- **[low] Test gap: deadlines during an in-flight request**
  - Missing: no test checks that the itimer or socket timeout gets clamped to `ABSOLUTE_STOP` while a request is in progress. The `absolute` case only patches `time.time` before the guard runs.
  - Also missing: no test of the worker clamp (`side` deadline, `bounded`).
  - Fix: add a fake test with `time.time` set to ABSOLUTE_STOP-3. Assert the Connection timeout is ≤3 and `getitimer` is ≤3 during `request`.

## Checked, no defect

Reserve is taken before each POST. Physical cap 300, budget 78720000, at most 5 attempts, waits 2/4/8/16 inside 60s. Unknown usage is never measured. Permanent results, invalid 200s, storage failures and the fifth failure keep both inflights. The 5xx-plus-schema/auth regex wins and is not retried. Tampering with the classification is reclassified by verify. The process-group SIGKILL is clamped to the stop time.

**Not verified:** no tests run. Behavior of real HTTPS sockets and signals. Whether a detached grandchild of Node survives killpg.
