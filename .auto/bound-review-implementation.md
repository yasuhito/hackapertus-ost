# Bound review implementation

Prospective source-binding hypothesis, not run40 resumption, transient capacity replay or favorable-answer retry. No canonical prepare/freeze, real data inspection/grading, inference, adoption or git writes performed. Baseline38 remains the saved reference; unavailable run40 is not a measured zero.

## Files and behavior

- New `.auto/bound_review_{contract,worker,research}.py`, five private `.auto/bound-review-templates/*`, five `.auto/test_bound_review*.py` modules.
- Only one additive bound block each in `.auto/measure.sh` and `.auto/checks.sh`.
- Complete unchanged 80/120-codepoint partitions, claim aliases `c_` plus base36, source aliases bare base36. All factual metadata/text/whitespace/order retained. Top-level NLI final_verification alone removed from factual view. Compact JSON exactly source_spans/all original IDs in order plus evidence_view. Short labels and unbracketed IDs, no regex rewriting or truncation.
- Reviewer guard additionally compares recovered source IDs with complete original host inventory in order. Exact model/schema/tool choice and strict pre-SDK validation retained. Original parent/ordinary input, schemas and final assembler unchanged.
- Offline export post traverses pinned SDK/runAgent, Python bridge, actual unchanged Root Transport.request, then fake HTTP for EVERY native packet, including later parent reports. Dummy submitted credentials scoped/restored only in Python, never Node; read_key/network forbidden. Fake wire bytes compared with original native payload encoding. Export audit records 480 Root-tested packets per workspace, both populated/no-pair paths and zero network/credential reads.
- Five exclusive bound-review-v1-candidate-r1..5 jobs, unchanged bounds/gates/deadlines/accounting/retry transport. No baseline execution CLI. Saved baseline checked with original role checked_analysis, without inference or regrading. Both ended protocol hashes, all old controls/runtime/workspaces and historical reference hashes verified; failed records/fences bound read-only. Dispatch exception requires both exact archive hashes and exactly one marked block at each layer.
- Optional operational hardening: new worker catches core.Stop and writes only allowlisted fixed code or unavailable plus fixed type Stop to new-job guard-stop.json, then rethrows the same error. Never writes exception text/stderr/headers/credentials or modifies Root STOP/unknown reservations. New completed-result verifier treats this diagnostic as a fence.

## Checks actually run

Environment for pytest:

```
PI_PACKAGE_ROOT=/home/yasuhito/.pi/agent/install/releases/1.1.0/node_modules/@earendil-works/pi-coding-agent
PI_SUBAGENTS_ROOT=/home/yasuhito/.pi/agent/npm/node_modules/@tintinweb/pi-subagents
PYTHONDONTWRITEBYTECODE=1
```

Command: `/tmp/hackapertus-ost-contract/.venv/bin/python -B -Werror::ResourceWarning -m pytest -q -p no:cacheprovider .auto/test_bound_review*.py`

Final full suite: 135 passed in 290.99s, including operational hardening and the independent guard-diagnostic completed-result fence test. No deselections.

Coverage: all five fictional workspaces, 300 distinct fictional inputs each in populated/no-pair modes = 600 actual SDK executions and 2400 actual Root-guard/fake-HTTP packets. Actual plaintext-v1 projection rejected UNDECLARED_TOOLS_REFUSED before HTTP construction; missing/subset/reordered/tampered/duplicate identities and schema/model/tool-choice changes rejected before HTTP. Selected/no-pair/repair/unavailable, strict malformed/duplicate/surrogate arguments, later-parent packet limits, large entirely fictional ASCII source completeness, immutable ordinary feedback, accounting/retry/deadline/unknown usage, availability delivery, fixed quality gates, and unchanged official scorer on five synthetic complete60 sets covered. Guard-stop allowlist/unavailable sanitization and original fence/reservation byte preservation covered.

`bash -n .auto/measure.sh .auto/checks.sh`: PASS. Read-only hash script: both ended protocol hashes, all original role and fragment control source/test/doc hashes, both additive archive chains and production runner/SDK hashes PASS. Original Root runner SHA01dff6b930a546dbe1b0f8651cebe0cec5f4d3987eeecf2bb9309b4ecea799b6; SDK SHAd666a679c4ea291285f9cd416260e394d5aba8216fade1bf7e963dc225e422ec. No old files changed. Old suites not rerun; their frozen code/test hashes verified.

## Remaining parent-only steps

Actual canonical input byte fit and full real historical runtime/workspace/artifact reference verification remain unexecuted here by explicit prohibition. Synthetic SDK proof is not proof that the largest canonical native packet fits. Parent must inspect this patch, then run `bash .auto/measure.sh --bound-review-prepare` offline to establish all actual-input native byte bounds and freeze before any candidate calls. An oversize packet must fence, never truncate/reselect or raise caps. No quality, cost improvement or model-capacity conclusion is claimed. After successful reviewed preparation only, parent may use the authorized experiment/log workflow; no target reinitialization.
