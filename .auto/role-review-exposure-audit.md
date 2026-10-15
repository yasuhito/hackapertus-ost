# Exposure audit — working-tree metadata evidence

**Conditional local envelope supported; universal freshness NOT certified.**

- Preparation is not inference: original source-index IDs originate in `track_2a/scripts/prepare_data.py:25-38`. Historical evaluation documents **331 beginner + 331 advanced mock cases**, not 1,488 real-model cases (`STATUS.md:24-29`; `track_2a/technical_report.md:69-80`). The 1,157-row mock-training assertion is not substantiated by these records.
- `Makefile:34-39` explicitly selects mock. Current `track_2a/src/predict.py:100-109` implements deterministic substring entailment/otherwise-neutral and returns before HTTP (`:110-136`). This is not an LLM; current code alone cannot authenticate historical runtime bytes.
- ID-only inspection of all 105 `output/cscs/*/manifest.json` and corresponding `state.json`: 65 freezes54, 15 freezes36, 25 freezes60; unique114 IDs = dev54 plus public60. All declare Apertus70B parent/8B child. State case counts: 63×54, 1×48, 1×27, 15×36, 25×60. No individual outputs read. Execution/save binding: `track_2a/dev/format/run_comparison.py:485-508`.
- Thus observed local real-model scope fits the existing conservative **62-source-row exclusion union** (`.auto/role-review-data-plan.md:11-25`), not all prepared1,488.

**Limit:** unrecorded/deleted/external executions and historical human/agent individual inspection remain unverified. File absence proves nothing. Reasonable scoped statement: “outside documented local LLM prompt-development exposure”; NOT “never viewed.” Owner must accept that boundary before selection; otherwise gate remains STOP. No exhaustive exposure JSON certified. No inference/tests/grading/network or forbidden-content inspection performed.
