# Fragment selector v1 implementation

This records implementation and offline verification; operational preparation/run status is in overnight-state. At coder handback no API calls, real-input preparation/freeze, baseline inference/regrading, initialization, experiment logging, commits, package changes or production changes had occurred. Parent review and subsequent offline corrections are recorded below.

## Change scope and behavior

- `fragment_review_contract.py`: deterministic complete input-only partitions,
  claim width80/source width120 Unicode codepoints, last whitespace in latter
  half preferred, otherwise hardcut. Whitespace and offsets survive exactly;
  whitespace-only pieces stay visible but cannot be selected. Global ordered
  base36 c/s IDs map to original span IDs and span-relative offsets.
- Reviewer projection retains full claim, complete ordered source partition and
  all original factual metadata. Only top-level `final_verification` is removed;
  strings occurring within claim/source are never removed or normalized.
- Case-specific native schema accepts exactly `checks:[]` or one three-string
  enum-ID/axis object. No empty enum, anyOf or uniqueItems. Python's unchanged
  strict JSON parser rejects duplicate keys before SDK coercion; private host
  validation rejects extra/type/unknown/surrogate/duplicate selections. Restored
  reports carry original quotes, candidate ID, offsets and span metadata.
- Honest statuses are `fact_pair_selected`, `no_fact_pair_selected`, or explicit
  `review_unavailable` after two unusable completions. Reports explicitly mark
  host-rendered ID selections, unproven relevance and no-pair's truth limits.
  Selection includes matching facts; it is not forced disagreement or an NLI vote.
- `fragment_review_worker.py` and `fragment-review-templates/*`: independent
  pinned8B Pi1.1.0/runAgent0.19.0 session, private settings/hooks cleanup, only
  review_source. Parent/ordinary helper retain original USER and SYSTEM, ordinary
  NLI schemas/assembler unchanged. Observed parent requests audit report delivery.
- `fragment_review_research.py`: exclusive five candidate jobs in namespace
  `fragment-review-v1`. Reuses unchanged frozen `role_review_transport.py`.
  All original resource/retry/deadline/ledger and quality gates remain intact.
  All five60-case canonical outputs must finish before first official grading.
  Per-repeat analysis separates selected-pair/no-pair/unavailable counts; existing
  metric keys remain available, including unknown-cost handling.
- Saved reference verification requires original protocol SHA
  `5aad8b8db06e725613f661275d596c61ff6f74930b5406dcce2ebd4ff0bb6b1d`,
  all old source/test/runtime/workspace/control hashes and saved baseline canonical,
  ledger, official-report and analysis integrity. No baseline inference or regrading.
  Previous300 control SDK paths are verified from hash-bound saved packet artifacts.
  Original old dispatch hashes must match archived bytes; removing the single marked
  new dispatch block must reproduce the archive exactly. Ended old candidate records
  and fences are also bound read-only. New protocol binds reference and five exclusive
  candidate identities before inference.
- Only additive marked branches in `measure.sh`/`checks.sh`; context mode
  `fragment_review`. Old files, archives, workspaces and STOP records are not edited.

## Verification actually run

Environment for pytest commands:

```sh
export PI_PACKAGE_ROOT=/home/yasuhito/.pi/agent/install/releases/1.1.0/node_modules/@earendil-works/pi-coding-agent
export PI_SUBAGENTS_ROOT=/home/yasuhito/.pi/agent/npm/node_modules/@tintinweb/pi-subagents
export PYTHONDONTWRITEBYTECODE=1
# PY below denotes:
# /tmp/hackapertus-ost-contract/.venv/bin/python -B -Werror::ResourceWarning -m pytest -q -p no:cacheprovider
```

- `PY .auto/test_fragment_review*.py`: **111 passed in282.56s**. Includes all five
  fictional workspaces/300 distinct actual-SDK input paths, each run in populated
  maximal-rendered-pair and no-pair mode (600 SDK executions), native complete
  packets including enums/tools/later parent reports, malformed-then-valid and
  unavailable paths, canonical/physical60-case verification, strict restoration,
  Unicode/whitespace/pages/empty cases, model/storage/deadline/budget/retry guards,
  quality backpressure, and actual unchanged official scorer on five synthetic60
  sets. The initial full run had a mock-reference fixture missing `analysis`;
  the fixture was corrected, then full runs passed. No acceptance check was weakened.
- `PY .auto/test_role_review*.py`: **127 passed in294.47s** (unchanged old tests).
- `PY .auto/test_fullbranch_transport.py .auto/test_prepare_role_review_data.py track_2a/dev/format --deselect=track_2a/dev/format/test_submission.py::test_saved_33_reproduce_then_normalize_27_reject_6 --deselect=track_2a/dev/format/test_strategy_c.py::test_c_freeze_same_source_and_only_parent_model`:
  **166 passed,1 skipped,2 deselected in16.83s**. This comprises remaining39 old
  experimental tests plus127 Root format tests. Together old experimental166 pass.
- An earlier combined quick run used the wrong second deselection: it ran the
  source-only historical `test_c_freeze_same_source_and_only_parent_model` and
  deselected fictional `test_full_a_summary_resume_no_duplicates` instead. It passed;
  the corrected command above was subsequently run. No historical gold was opened.
- `bash -n .auto/measure.sh .auto/checks.sh`: passed. Python byte assertions confirm
  removing only marked new branches reproduces both parent-created archives.
  Archive SHAs: measure69cf7f15a2303710a457d3adc1f33a5cdc786ba8b696be9910b7888530e69695;
  checks0d1089a1c088a5163c11afd88b329417354d9d8cb1266d039df037c93afeb65d.
- Production runner/SDK hashes remain
  `01dff6b930a546dbe1b0f8651cebe0cec5f4d3987eeecf2bb9309b4ecea799b6` /
  `d666a679c4ea291285f9cd416260e394d5aba8216fade1bf7e963dc225e422ec`.

## Limits and next command (parent only, after review)

No real data preflight was run. Actual DEVELOPMENT packet sizes, saved reference
integrity and feasibility under physical300 remain unverified here; oversized packets
or exhaustion fence without truncation, cap expansion or prefix grading. Fictional
saved-control300 fixture verifies traversal/hash/additive-dispatch/mutation fencing;
its old canonical/official verifier is stubbed, not a new300-path SDK replay. Real
preparation instead invokes the unchanged saved baseline verifier read-only.

Next authorized parent command after patch review:
`bash .auto/measure.sh --fragment-review-prepare` (zero API). It validates the old
reference and prepares/freezes all five new workspaces; each candidate path exercises
both populated maximum-rendered report and no-pair through actual SDK. It does not
initialize the already-initialized mean_Q target. Only later, with >=5700s remaining,
`bash .auto/measure.sh --fragment-review-candidate` through run_experiment, followed
immediately by log_experiment. No baseline entrypoint exists. No production adoption.

## Parent review before freeze

Independent review found no demonstrable restoration/input/integrity/gating/deadline defect. Two low observations were addressed prospectively: the accurate parent subagent-description change is now explicit in the plan; selected/no-pair/unavailable counts and fragment-selection rejection counts now emit METRIC lines. The inherited meaningless free-text quote-failure counter was removed.

Parent reproduced a real-input native240000byte failure through the actual pinned SDK in an ephemeral source/input-only workspace with external access forbidden. A fictional ASCII300-span SDK regression independently failed at263460bytes. Cause was exposing redundant host-only offsets and original NLI anchors in a flat fragment table. The compact projection keeps offsets/original span anchors only in the inventory/restored parent report. A grouped JSON prototype still exceeded the real packet bound, so the final deterministic plain-text view displays factual metadata JSON blocks and [id] exact-text entries in original group order, avoiding a redundant layer of per-fragment JSON escaping. All source/claim characters and factual page/language/vote context remain present. No input filtering/truncation/reselection or bound increase. The original actual-SDK real-input repro now PASSES,4packets/max231792bytes/zeroAPI, and the ASCII300-span regression passes. Full-text restoration and metadata-collision tests cover the view. Parent final full suite:113passed in284.37s, including the600fictional SDK executions, actual official scorer on synthetic sets and complete real canonical/physical-stat reporting. A zero-state counter publication issue was reproduced through the60-case SDK/ledger fixture and fixed by explicitly initializing all report-state counts; final full suite includes the regression. All300new real-input paths and saved reference integrity still require canonical preparation before inference. Shellsyntax passed and production runner/SDK hashes remain unchanged.
