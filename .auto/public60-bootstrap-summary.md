# PUBLIC60 paired bootstrap

Baseline Q: 0.8051187036988254; candidate Q: 0.8249410791099698; ΔQ: 0.0198223754111444.

20,000 paired draws, seed 20261016 reset per grouping; percentile 95% ΔQ intervals:
- 30 source-row/reference pairs: [−0.0433292555, 0.0859624767].
- 13 date clusters: [−0.0453865145, 0.1047495174].

Both intervals cross zero. Each draw shares group multiplicities across variants, tasks, and all five repeats; Q is computed per repeat before averaging. Official present-class macro-F1 is used; canonical fallback labels remain unchanged.

Executed `/tmp/ost-official-evaluator-3U4yO9/env/bin/python .auto/public60-bootstrap.py` successfully once. Six synthetic cases matched the pinned official scorer, including perfect one-class F1=1. All ten full-sample Qs matched within 1e-12; 60 unique IDs, 30 pair mappings, and five repeats verified. SHA-256 checks proved all 17 inputs unchanged. Results: `output/cscs/public60b-bootstrap.json`.

Candidate remains FAILED: 12 versus 7 fallbacks and gain below 0.02. No adoption or statistical-significance claim; public-data uncertainty does not establish private-holdout performance. No grader/model reruns.
