# Future empty-source retry policy v1

User approval: bounded HTTP500 retries, subsequently amended to at most five total attempts (試行は 5 回までにしない？). No protocol or job had been prepared when the limit changed.

This is a new exclusive protocol and job, not permission to resume job #33 or
any historical H1, H2, probe, prefix, STOP or inflight job. Historical artifacts
and the old no-retry dispatch branches remain unchanged. Production Root,
SYSTEM, models, sources and assembler acceptance are unchanged.

Only HTTP 500 is retryable, at most four retries (five total attempts), with fixed
2, 4, 8 then 16 second waits. No jitter, reset, or retry for other status codes,
timeouts, sockets, malformed JSON, model mismatch, API errors or unknown usage
on HTTP 200. The explicitly approved exception is unknown usage on HTTP 500.
Every attempt uses a fresh original strict allowlisted HTTPS Transport.
Credentials are opaque and read only during execution by the default client.

Twelve logical cases, six control and six candidate, retain identical fictional
empty-source frames and grading. The primary remains
empty_source_assembler_violations on the six candidate answers. Control results
are separately reported. Requested arguments are adversarial proposals, never
permission to violate the schema. Native numeric 1.0 acceptance does not change
the strict assembler integer guard. Errors are not synthesized as answers.

The new physical POST cap is 60 (12 logical requests times at most five attempts). Each POST first persists an exclusive attempt
identity, payload hash, reservation and counter, and atomically replaces budget
state. Each raw HTTP status/body capture is immutable, without headers. Even
failed captures preceding success survive. Disk failures stop, never retry.
Terminal failures preserve STOP and inflight; no job can resume.

A logical call has 60 seconds total including all attempts and waits. Socket
limit is 45 seconds; the global monotonic phase limit is 900 seconds. Deadlines,
POST count and reservation are checked before each POST and before each wait.
No sleep or POST occurs when the scheduled wait cannot fit. Output remains
256 tokens, known input at most 1000. Total charged budget remains 32768.
Before every attempt reserve 4096. Known valid 200 usage replaces that attempt's
reservation with actual tokens. Unknown failures retain 4096 permanently as
budget accounting only, not actual usage or cost. The budget can prevent a
retry even with attempts remaining. Report known token subtotal, unknown count
and reserved charge separately. With unknown attempts, full_usage_known is
false, full_total_tokens is null and financial cost is unavailable.

Preparation and checking are offline. Fresh metadata pins policy, helper, tests,
plan, dispatchers, current model/source and runtimes. Checking verifies every
attempt checksum and reconstructs counters, waits, usage, budget and all twelve
logical answers without POSTs. Complete answer grading may be measured under
this new policy despite honest unknown failed-attempt cost. It does not bless
old no-retry measurements or weaken their guards.

After offline tests, future commands are:

    .auto/measure.sh --provider-schema-empty-retry-prepare
    .auto/measure.sh --provider-schema-empty-retry

Execution is not automatic. This implementation task performs no live calls,
experiments, init, log, or automatic prepare/freeze.
