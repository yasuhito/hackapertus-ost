# C system-prompt eval

## Approved scope

54 already-exposed development cases only, from 2020-09-27 and 2021-03-07.
This is not an unseen holdout. Never read the protected competition holdout.
C uses the authoritative nonthinking Apertus v1.5 70B parent and an actual
pi-subagents 8B child. Only the system prompt may change during hillclimb.
The existing runner, tool contracts, model roles and transport caps stay fixed.

## Official scoring

`grader.py` executes an unmodified external checkout of:

- https://gitlab.com/ifsoftware/hackapertus-starter.git
- commit `5e6957729b77a126006049305ad1ef241211a5b4`
- file `evaluate.py`

Acquire that public checkout outside this repository. Install its dev dependencies
in a separate environment. Pass the checkout and interpreter explicitly:

```sh
python3 evals/c-system-prompt/grader.py \
  --official-repo /tmp/official-starter \
  --python /tmp/official-env/bin/python \
  --predictions /path/to/canonical.jsonl \
  --expected /path/to/expected.jsonl \
  --cases /path/to/cases.jsonl \
  --output /path/to/ignored-results.json
```

`cases.jsonl` contains reviewed public inputs, expected labels and paired reference
passages for scoring only. Never expose these expectations, this directory, or
any grader to the model. Official CLI `--cases` rows are each case's `input`;
`--expected` rows are `{"id": id, **expect}`. The reviewed paired reference is
used as `expected.reference`, exactly as official `prepare_cases.py` uses the
underlying row's `reference_string`. Neutral expectations omit reference.

## Objectives and adoption rules

- Classification: `Q_label_norm = (0.30 F1_A + 0.28 F1_B) / 0.58`.
  The minimum worthwhile gain is +0.02 on this metric, beyond measured noise
  on **both train and test**. `Q_task` is logging only, not a goal.
- Evidence: Task A Hit@5 is a second primary improvement objective. Baseline
  reference is 7/18; its contribution is 20% of SA. Do not claim that improved
  labels alone establish improved overall official performance.
- Always log F1_A, F1_B, Hit@5, canonical/source validity, fallback-neutral count,
  all parent/child/repair tokens, case wall time and API wait separately.
- Require F1_A >= 0.60 and F1_B >= 0.75 on every scored evaluation.
  Upstream's B threshold remains 0.70; the safety policy is separate.
- Report any secondary metric regression before adoption.
- Canonical fallback neutral is scored by official `label_of`, not changed to
  INVALID by internal error metadata. Count fallbacks separately.
- Maximum five prompt candidates, entirely fictional prompt examples only.
- Preserve uncertain-request fences. No unknown-usage retry or auto-resume.
- Honor every eval-hillclimb STOP. A baseline noise check precedes any split or
  candidate. New runs require approved scale; baseline repeat 3 is approved.

The application runner creates fresh isolated parent and child workspaces and
in-memory credentials; scoring-only fixtures are not mounted there. Baseline
repeat 3 uses `--repeat 1 --job output/cscs/format-C-r3` because the unchanged
runner's repeat option accepts only 1/2 and controls the default path only.
Record it as the third independent repeat, not another baseline configuration.

Raw outputs, transcripts and local metrics remain under ignored `output/`.
No raw outputs are committed. `grader-review.md` records the official scoring
semantics approved by the owner, superseding the older local-grader review.
