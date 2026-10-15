# Native ID uniqueness: provider rejected the schema

Run35 stopped before completing the prospectively frozen paired12-request diagnostic. Its logged primary0 is an unavailable crash sentinel, not a baseline or measured zero. Neither the control6 result nor the unique6 result is available; the read-only candidate-report command was not invoked.

The generic defect was reproduced first on fictional pages: native parameters allow repeated supplied IDs, while the unchanged actual assembler raises DUPLICATE_ID. The prospective candidate added only uniqueItems:true to the root and both previously compatible complete branches. No instructions or output deduplication were introduced.273 offline tests passed, including independent TypeBox subset/no-lost-assembler-input checks.

## Live outcome

- Request0,8B control: HTTP200.
- Request1,8B uniqueItems candidate: HTTP400 BadRequestError.
- Provider message: `Grammar error: Unimplemented keys: ["uniqueItems"]`.
- No retries: the approved policy retries ONLY500, not400.
- Two POSTs attempted. The first has383 known tokens. Failed-request usage is unknown;4096 is a conservative budget charge only, not measured tokens. Partial charged budget4479.
- STOP/inflight records remain and completed.json is absent. No subsequent requests were sent.

This specifically establishes that the endpoint rejected the candidate schema keyword. It does not measure model-format reliability, prove backend implementation details beyond the returned message, or show that uniqueness is impossible through every possible representation. Alternate encodings were not tried. Enumerating toy-specific arrays would not be a scalable generic solution and must not be used to game this diagnostic.

Prospective protocol SHA256:078f20e5844cbe6ce97b68aeca7f8883d1ed5e4870cf81fd81b17e90d09cd0f4.

Production keeps its unchanged native declaration and local duplicate-ID rejection. PUBLIC60 and source/label acceptance were untouched. Do not retry this unsupported declaration or treat the failed control/candidate set as a usable reference.

## Research boundary

Completed branch-closure and empty-source diagnostics reached zero on their fixed fictional workloads. These are compatibility observations, not production NLI benefit. A future production-format evaluation of the compatible complete-branch representation would require a separately approved protocol because the original completed H2 comparison prohibited alternate-encoding retries. Such a proposal must explain the demonstrated provider representation mismatch, retain original quality/evidence safeguards, preserve all prior failures, and never present exposed PUBLIC60 as unseen validation.
