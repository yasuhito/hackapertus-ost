# Approved full-branch PUBLIC60 round: rejected

Run36 imported the immutable original-v5 five-repeat reference, without inference or regrading. Run37 collected all300 new answers once and officially graded every canonical output, including the5 legal neutral decoder fallbacks, only after all5 jobs completed. The backpressure check rejected the candidate with `CANDIDATE_Q_FAILED`. This is a completed quality rejection, not an interrupted transport run. Do not retry it for favorable noise or change thresholds, schema ordering/spelling, cases or output treatment.

The owner explicitly approved this separate round after being asked about PUBLIC60x5, unchanged quality/evidence safeguards and no production changes. The changed compatibility assumption came from fictional provider probes31/32, not from mining PUBLIC60 gold. The original failed H2 identities and no-retry decision remain intact. PUBLIC60 is exposed DEVELOPMENT, not unseen validation, generalization evidence or a competition holdout.

## Fixed decision

| Measurement | Saved original v5 | Full-branch candidate |
| --- | ---: | ---: |
| Final format fallbacks | 7/300 | 5/300 |
| Accepted answers | 293/300 | 295/300 |
| Mean Q | .8051187036988255 | .767211377759045 |
| Mean TaskA macro-F1 | .7009478538890304 | .7203123673711909 |
| Mean TaskB macro-F1 | .9167303284950343 | .8174603174603173 |
| Mean HitA | .30 | .30 |
| API requests | 941 historical | 910 new physical/logical |
| Known prompt tokens | 8917635 historical | 9084489 |
| Known completion tokens | 32531 historical | 30226 |
| Known total tokens | 8950166 historical | 9114715 |
| Parent calls | 616 historical | 605 |
| Child calls | 325 historical | 305 |
| API wait, seconds | 1908.6031044714618 historical | 1604.4014757815748 |
| Total case wall, seconds | 2238.1406852069777 historical | 1770.0356041353662 |

Both per-repeat F1 safeguards passed (A>=.60, B>=.75), as did mean HitA>=.30 and all source/usage/canonical integrity checks. Mean Q failed the exact preregistered floor `.8029455012419827`, original Q minus original measured noise `.0021732024568427814`. The Q delta was `-.03790732593978052`; TaskB macro-F1 fell despite TaskA improving. The primary improvement7to5 cannot override this fixed guard. No statistical-significance claim is made from2 fewer fallbacks.

Calls decreased31, while measured tokens increased164549. Timing values above compare historical observed case/API durations with new observed durations, not a controlled latency experiment. The8.035340698901564-second reference command only imported archived observations; it was not baseline inference. New candidate command wall was1813.9600752210245 seconds, excluding8.6-second backpressure checks. Monetary cost is unavailable because no billing rate was supplied.

## Every new repeat

| Repeat | Accepted | Fallbacks | TaskA F1 | TaskB F1 | Q | HitA | Physical calls | Tokens | Case wall seconds |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 59 | 1 | .753076988371106 | .8174603174603173 | .7841585955176219 | .30 | 182 | 1822956 | 393.9570421827957 |
| 2 | 59 | 1 | .712121212121212 | .8174603174603173 | .7629745733194008 | .30 | 182 | 1822958 | 347.85281291767024 |
| 3 | 59 | 1 | .712121212121212 | .8174603174603173 | .7629745733194008 | .30 | 182 | 1822885 | 343.5387590462342 |
| 4 | 59 | 1 | .712121212121212 | .8174603174603173 | .7629745733194008 | .30 | 182 | 1822958 | 342.4711051376071 |
| 5 | 59 | 1 | .712121212121212 | .8174603174603173 | .7629745733194008 | .30 | 182 | 1822958 | 342.21588485105895 |

Each repeat had121 parent and61 child logical calls, exactly182 physical POSTs, below the unchanged300 POST/job cap. Every physical attempt returned HTTP200 on its first attempt; zero HTTP500 retries, failed-usage reservations or backoff waits occurred. All9114715 measured tokens and response model identities are known and validated. Actual live500 recovery remains unexercised. The separate immutable physical ledger preserves every attempt and its bijection to the original SDK logical ledger. Future unknown500 usage would remain unknown with262400-token conservative budget charges, not measured tokens or full known cost.

## Controls and artifacts

- Protocol: `output/cscs/public60-fullbranch-v1-protocol.json`, SHA256 `cad5397e82c154ce803be8e0f9450b8950024ce6eb16b2367a7c04b86dfcb81b`.
- Original reference binding: `output/cscs/public60-fullbranch-v1-reference.json`; source actual repeats are `public60-v5-r1` and `public60b-v5-r2..5`, not H1/H2.
- All new jobs: `output/cscs/public60-fullbranch-v1-r1..5`, with `physical/` attempt records and original canonical outputs.
- Official reports: `output/cscs/public60-fullbranch-v1-r1..5-official.json`.
- Completed collection/grade fingerprint: `output/cscs/public60-fullbranch-v1-analysis.json` and matching phase JSON. Their `completed` status describes collection, not adoption or passing quality safeguards.
- Original v5 SYSTEM, source extraction, IDs, prose, role structure, local assembler, official scorer and caps unchanged. The candidate changed only isolated Python schemas()/SDK nativeTools() declarations to self-contained equivalent branches. No uniqueItems or empty-source specialization was bundled.
- Production runner SHA256 remains `01dff6b930a546dbe1b0f8651cebe0cec5f4d3987eeecf2bb9309b4ecea799b6`; SDK SHA256 remains `d666a679c4ea291285f9cd416260e394d5aba8216fade1bf7e963dc225e422ec`. Production/app diffs are empty; no deployment, push or adoption occurred.

Offline preparation exercised900 actual pinned-SDK fake-backend packets for all300 contexts; max payload204886/240000 bytes. Implementation reported238 passed/1 skipped/2 prohibited historical fixtures deselected. Parent independently ran43 new tests successfully and213 format/controller/fictional tests successfully with2 skipped under explicit pinned Pi1.1.0/subagent0.19.0 environment variables. An initial parent invocation omitted those required runtime variables and produced36 SDK bootstrap failures; rerunning with the required pinned environment resolved all of them without source changes. Independent non-mutating review found no demonstrable HIGH/CRITICAL defect in the retry/accounting/evaluation safeguards.

## Boundary

This approved300-answer comparison is complete and rejected. Preserve all data, captures, source snapshots, prior STOPs and failed protocol identities. Do not replay this round, select favorable repeats, interpret the dashboard's primary decrease as a passing quality decision, or tune another declaration against exposed answers. Fictional schema compatibility did not establish NLI quality preservation. Further live work needs a genuinely distinct, independently reproduced source-contract defect and separately approved prospective scope, rather than cosmetic schema variants or fabricated zero-floor diagnostics.
