# Empty-source diagnostic completed under the approved retry policy

Run34 used a new frozen protocol and identity after explicit user approval for HTTP500 retries, at most five total attempts with2/4/8/16-second backoff. Run33's stopped identity, partial prefix and failure records remain unchanged.

All12 requests completed, HTTP200 on the first attempt. Therefore retry_count=0: this live run does not demonstrate recovery from an actual500. Five-attempt behavior is covered by offline mocked HTTPS tests;217 tests and live backpressure checks passed.

| Model | Old native assembler violations | Specialized assembler violations |
|---|---:|---:|
| 8B | 2/3 | 0/3 |
| 70B | 2/3 | 0/3 |

All responses conformed to their declared native schemas. The four specialized-arm proposal mismatches were expected substitutions of legal neutral output for intentionally invalid nonneutral empty-ID proposals. They are neither NLI accuracy errors nor evidence of NLI accuracy gains. The unchanged assembler graded every response; no float normalization or failure omission occurred.

This is the first COMPLETE valid observation for this workload. Run33's logged0 remains an unavailable crash sentinel, not a measured baseline. The measured paired comparison is control4/6 versus candidate0/6; zero is the primary floor. Do not rerun this completed diagnostic to seek favorable noise.

Known usage1500 tokens,12 physical POSTs,12 logical requests, no unknown usage, no reserved unknown-failure charges. Phase15.46875801216811 seconds. Financial cost is unspecified, not zero. Production and PUBLIC60 were untouched.

Protocol SHA256:06e67c8e2914e32466c94f9b747eece396778d6e7255c0582ceb274db87d6e94.

The earlier HTTP500 did not recur; this observation does not identify its cause. A provider support draft remains unsent. No further provider-log access is required merely to use the newly approved bounded500 retry policy in future prospective experiments.
