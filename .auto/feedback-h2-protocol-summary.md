# H2 offline freeze

Only native `schemas()` / `nativeTools()` gain `anyOf`. Neutral IDs remain unrestricted. Local TypeBox, assembler, H1 feedback, SYSTEM, roles and caps are unchanged. Provider support: **UNCONFIRMED**; transport rejection stops without retry.

Old declaration accepts fictional nonneutral empty IDs; assembly rejects them. Test-first RED: missing `anyOf`. GREEN: 280 tuples checked against an independent installed TypeBox compiler. Only two tuples newly excluded; seven assembler-accepted tuples retained. Duplicate-ID constraints remain assembler-only.

Checks: pinned-runtime `python -B -Werror::ResourceWarning -m pytest -q -p no:cacheprovider` on H2 controller/tests, format regressions, source-spans and failure reproduction: **196 passed, 8 deselected**. Two forbidden historical fixtures and six frozen no-anyOf tests excluded; new H2 counterparts preserve their rejection checks. `bash -n` and H2 `verify()` / `check_reference()` passed.

`bash .auto/measure.sh --feedback-h2-prepare` completed five exclusive workspaces/300 contexts. Actual SDK mock: 60 cases/180 outbound frames, maximum191922 bytes, cap240000; zero remote calls/credential reads. Initial equivalence stop omitted the intentional SDK hash allowance; same offline workspace retained and source-verified before completion. No model jobs exist. SHA proof preserved1562 H1 files.

SHA256:
- control: `ab6af38c36adc1cbf23ce48f5b88c0ad35b8ad2503ad2628a31a1171379b888a`
- Python: `376b4196bded0bc1fd22ff63e8b12931494cd501666d155cd6741bbd20080b3d`
- SDK: `498aeb9851760330a9c0d8c949e4be42e5f1715019b9fe54ecbc5c33a5f85a96`

Parent-ready: `bash .auto/measure.sh --feedback-execute h2` via run_experiment, then log all metrics. Historical reference7 and quality gates unchanged. No inference, grading, init, log or commit performed.
