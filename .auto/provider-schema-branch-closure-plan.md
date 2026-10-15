# Prospective fictional provider probe: branch closure v1

The owner explicitly requested this next iteration. Hypothesis: making each conditional
branch self-contained may improve provider schema handling while preserving logical
acceptance. Provider implementation/role remains unknown. This small diagnostic cannot
establish causal significance, production reliability, NLI accuracy, or PUBLIC60 performance.
No application, SYSTEM text, tool name, tuples, control/simple schema, or task changes.
No encoding search, retries, selection using source/gold, or production H2 retry.

## Frozen comparison

Reference: original completed 12 fictional copy requests, independently recounted after
all original and recovery source/artifact pins validate. Actual reference violations = 3:
8B simple 0/3, conditional 0/3; 70B simple 0/3, conditional 3/3.
Run29's crash/unavailable zero is NOT a baseline; run30's read-only recount measured 3.
Original protocol, completion, all captured requests/responses, full source and runtime
pins remain checked. Only dispatcher source pins relocate to exact archived bytes:
original archives for original pins, fresh pre-change archives for recovery pins.
No blanket model-source or data exemption. Current helper/test/plan/dispatchers, original
sources, validators, Python/Node/TypeBox 1.1.0 runtime, archived dispatchers and reference
frame/request/artifact hashes are pinned in the new immutable control.

Exactly the original ordered 12 frames: for 8B then 70B, labels 0,1,2, each simple then
conditional. All messages and simple payloads byte-identical. Only conditional parameters
change: retain common object schema c, replace partial anyOf with two deep copies of c.
Neutral branch label enum [1]; nonneutral branch label enum [0,2] and candidate_ids
minItems 1. Both include full required fields/properties/types/enums/maxItems and
additionalProperties false. No uniqueItems. Neutral empty and nonempty remain legal.
Independent TypeBox proof exhausts finite domains including missing/extra fields,
bools/floats/strings/null, labels, all binary known-ID arrays lengths 0..6, duplicates,
multi-IDs, invalid arrays/IDs, Unicode lookalike expected enum mismatch. No accepted tuple
excluded and no constraint relaxed versus original common-plus-partial-anyOf.

## Safety and reporting

One exclusive new job, 12 calls once, no resume/retry. Same default origin/credentials,
45s socket, 60s request, 900s phase, temperature 0, max_tokens 256 and 32768 total budget.
Known actual input usage <=1000 and output <=256 remain mandatory, NOT loosened.
Only conservative per-request SAFETY reservation increases from1256 to1800:
12*1800=21600<32768. Serialized messages+tools+128 must be <=1544 (1800-256);
maximum new estimate1358 bytes. This is a reservation/preflight allowance, not a provider
context cap or permission to consume >1000 input tokens. Separate driver uses1800,
never the original run loop's1256. Unknown usage/HTTP/error/identity/storage uncertainty
permanently STOP; inflight is nonresumable. Wrong schema outcomes collect all12.
Checks pass complete measurements even with nonzero violations; backpressure does not
gate the primary improvement. Primary schema_contract_violations is compared to actual3,
not crash0. Stable run30 secondary metric keys retained; recovery_wall_seconds=0 explicitly
means this is NOT a recovery run, not zero inference time. Candidate phase and request
wall times measured normally. No new primary initialization.

Offline tests must pass before offline --prepare. Preparation creates only the new
control, no credentials/API/job/context. Final control SHA is reported separately,
not embedded recursively here. Parent alone may execute the 12-request experiment and
log results. No production/root edits, historical helper edits, log/prompt edits, or
historical artifact writes. Global check context changes atomically only after completion,
using recovery.save's corrected replacement, never original frozen save(replace=True).
