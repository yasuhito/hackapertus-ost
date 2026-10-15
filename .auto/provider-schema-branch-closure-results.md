# Complete-branch fictional probe

Run31 retained this diagnostic result, not an application change. The exact same12 fictional requests, messages, models and tool descriptions were used. Only the conditional schema representation changed: both branches now repeat all common required fields, types, enums and bounds. Independent TypeBox tests verified equivalence to the previous accepted argument set, including neutral nonempty IDs.

| Model | Simple violations | Previous conditional violations | Complete-branch violations |
|---|---:|---:|---:|
| 8B | 0/3 | 0/3 | 0/3 |
| 70B | 0/3 | 3/3 | 0/3 |

Primary improved from the actual measured3/12 to0/12. There were no missing fields, truncations or exact-copy mismatches. This supports a branch-scope representation explanation, but does not identify the provider implementation or prove broad JSON Schema compliance. The diagnostic floor is reached; do not rerun this completed probe for noise.

All12 new calls completed with known usage:1520 input tokens,208 output tokens,1728 total. Inference phase15.77575320797041 seconds; summed HTTP wall14.233519890811294 seconds. No retries or recovery calls.85 offline fictional tests and live backpressure checks passed. Prospective protocol SHA256:83d58a54863ece0c758cbe11b0de4cc071db8c2864658d3127fcf3a49f871398.

Model/completion/input usage/POST/total-token caps were unchanged. The per-request reservation rose conservatively from1256 to1800 to cover larger schema bytes without raising allowed actual input usage1000 or output256. Total budget remained32768.

The dashboard's original0 baseline came from run29's unavailable crash sentinel. It is not a valid reference. Run30's fully revalidated original captures establish3, against which this actual measured0 is compared. No unavailable observation was imported as a baseline.

PUBLIC60, NLI scoring, v5 SYSTEM and application source were untouched. Neither retention nor this small copy-task result authorizes adoption or establishes production reliability. A future generality investigation needs separately frozen fictional edge cases, such as neutral nonempty evidence and longer/multiple identifiers, before any separate production evaluation proposal.
