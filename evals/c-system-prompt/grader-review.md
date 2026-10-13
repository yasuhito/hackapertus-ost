# Official grader review (approved; supersedes local review)

Owner authorized unmodified official evaluator scoring, then confirmed Q_label_norm
and baseline repeat 3. The earlier local-grader review's INVALID fallback judgments
are superseded, not used to override the official evaluator.

Source: `https://gitlab.com/ifsoftware/hackapertus-starter/-/blob/5e6957729b77a126006049305ad1ef241211a5b4/evaluate.py`.
`label_of` checks label type/range and label_name only. Missing/duplicate responses
are INVALID; evidence/metrics/internal error metadata do not override a valid
label. Task A evidence is independently scored with official fuzzy Hit@5.

| case | saved configuration | gold | canonical label | official label verdict |
|---|---|---:|---:|---|
| ost-dev54-0117-B | C r1 | 0 | 0 | correct |
| ost-dev54-0557-B | C r1 | 1 | 1 | correct |
| ost-dev54-0557-A | C r1 | 1 | 1 | correct |
| ost-dev54-0117-A | C r1 | 0 | 2 | wrong |
| ost-dev54-1117-B | C r1 | 2 | 0 | wrong |
| ost-dev54-1117-A | C r1 | 2 | 0 | wrong |
| ost-dev54-0835-B | B70 r1 fallback | 1 | 1 | correct label; fallback counted separately |
| ost-dev54-0924-B | B70 r1 fallback | 1 | 1 | correct label; fallback counted separately |

No model/judge calls for validation. These outputs are programmatically checked
twice against official label_of. B rows validate fallback semantics only, not C
baseline performance. Full raw outputs stay ignored. Do not mistake a correct
fallback label for a successful model inference or correct semantic evidence.
