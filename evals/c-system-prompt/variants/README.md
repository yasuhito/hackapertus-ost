# Evidence-only child (explicit experiment, not production)

Approved surface: the fixed C 8B child selects only up to five unique exact candidate IDs. Python restores original source with existing `candidates`/`citation_pages` closure helpers, without internal classification or synthesized quotation. The fixed 70B parent receives original source/claim and label-free restored evidence, and supplies its own label. Tool names/count, package runAgent, repair/completion caps, ledger/fences, fixtures/splits and official scoring are unchanged. No examples added.

`run_batch.py --variant evidence-only-child` applies the archived patch only inside tracked source-only temporary workspaces. Production and default C stay v0. It rejects prompt/metadata additions. The specification pins patch SHA256, four role-file before/after hashes, full mapped source hashes, fixed policy and normalized frozen source/parent-schema hashes. The child HTTP compatibility projection only removes label: **no uniqueItems on the wire**. TypeBox/Python retain strict local uniqueness.

Configure existing installations (no installation/authentication required): set `REPO`, `RUN_PYTHON`, `EVAL_PYTHON`, `OFFICIAL_REPO`, `PI_PACKAGE_ROOT`, and `PI_SUBAGENTS_ROOT` to your repository, runtime/evaluator Python executables, pinned official evaluator checkout, Pi 1.1.0 package root and pi-subagents 0.19.0 package root respectively. Export the two package-root variables.

Offline preparation (no credentials or network):

```sh
"$RUN_PYTHON" -B "$REPO/evals/c-system-prompt/run_batch.py" \
  --repo "$REPO" --python "$RUN_PYTHON" --count 5 \
  --prefix "$REPO/output/cscs/evidence-child-reviewed" \
  --variant evidence-only-child --prepare-only
```

Only parent/user after patch review may replace `--prepare-only` with `--user-run --approval '<explicit approval reference>'` for approved 54 cases x 5 repeats. Jobs/sidecars must be fresh; never retry/reuse uncertain fences. Preparation leaves private temporary source copies, not completed jobs.

Saved-run analysis uses existing scorer/split. Set `VARIANT_R1` through `VARIANT_R5` to the five exact completed candidate job paths:

```sh
"$EVAL_PYTHON" "$REPO/evals/c-system-prompt/analyze_runs.py" compare \
  --repo "$REPO" --official-repo "$OFFICIAL_REPO" --python "$EVAL_PYTHON" \
  --jobs "$REPO/output/cscs/format-C-r1" "$REPO/output/cscs/format-C-r2" \
         "$REPO/output/cscs/format-C-r3" "$REPO/output/cscs/format-C-r4." \
         "$REPO/output/cscs/format-C-r5" \
  --candidate-jobs "$VARIANT_R1" "$VARIANT_R2" "$VARIANT_R3" "$VARIANT_R4" "$VARIANT_R5" \
  --destination "$REPO/output/evidence-child-analysis-reviewed" --part split \
  --variant evidence-only-child --allow-cli-only-hash-changes
```

Default analysis rejects variant manifests. Explicit analysis verifies exact source hashes and unchanged frozen source/parent schemas. The five approved original v0 manifests have identical normalized source maps, pinned in the specification. Differences from current base are only the old CLI hash (positive repeats/new write-path normalization/prepare metadata) and absent new CLI test, reviewed against HEAD^ → c47de4a. Historical maps require **both explicit flags**, and every difference is reported. No other baseline source changes are admitted.

Existing Q/noise/paired intervals, safety, validity/fallback, Hit, tokens/time and C→E metrics remain. Child counters inspect untouched saved responses including rejected repairs, before parsing/masking. Label fields, textual label keywords and class-name values under alternate fields count as emissions; candidate_ids values are excluded. Any nonempty emitted content/reasoning/reasoning_content (visible saved response fields only), unauthorized fields and malformed arguments are separate contract violations. Ledger counters are independently rechecked by analysis. Detection is finite lexical, not a semantic classifier of every implicit recommendation; no model judge. Expected legitimate output is candidate_ids only with empty content and all counters zero. With the variant only, both adoption gates additionally require candidate `child_label_free_all` on **both train and test**. Default adoption gates are unchanged.

Offline tests (existing environments must supply pytest/numpy/pypdf):

```sh
PYTHONDONTWRITEBYTECODE=1 "$EVAL_PYTHON" -B -m pytest -q \
  "$REPO/evals/c-system-prompt/test_evidence_variant.py" \
  "$REPO/evals/c-system-prompt/test_runbook_cli.py"
PYTHONDONTWRITEBYTECODE=1 "$RUN_PYTHON" -B -m pytest -q "$REPO/track_2a/dev/format"
```

If pytest lives in a separate existing environment, expose its pure-Python site-packages via `PYTHONPATH`; do not install dependencies. Tests are synthetic fake-provider SDK/strict-contract checks, not Apertus accuracy or official scoring. Live 54x5 and saved-run official scoring have not been executed by implementation agent.
