# Measurement coverage

| Requirement | Implemented and locally verified | External/live boundary |
|---|---|---|
| Roast SDK/dependencies | Standard six cmd stages, frozen lock, project vendor, version smoke | Ruby environment required |
| IDs/provenance | run/case/attempt, engine/recipe/data/split/config hashes, commit, tracked diff and worktree file hash | Historical commit/dirty diff absent in old logs, retained unknown |
| Usage | raw events, 81 real historical model usages, all82 attempts, cache/reasoning inclusion, dedup, missing/error fields null | Organizer token proxy absent |
| Timing | fake Apertus HTTP observer delay/failure, local PDF/context/replay spans, timeout process spans | Historical exact HTTP wait unknown; live Apertus/Pi streaming untested |
| Contract | ID/cardinality, integer labels/names, exact quotes/physical pages/selected context, first5/5000 limit | Actual endpoint/context limits untested |
| Classification | A/B macro-F1, confusion/class P/R/F1, date-group bootstrap95%, paired comparison | Two date groups; no new repeated-inference variance |
| Evidence | 18 assistant mappings with PDF/page hashes, partial coverage/exclusions, hit5 diagnostic | Human/official gold and semantic sufficiency unverified |
| Budgets/resume | maxcases/calls, zero live tokens/calls, command/run timeout, transient-only bounded retry, source/input/PDF snapshots, upstream hashes, anchored per-case cache/raw consistency, reserved-attempt recovery/fail-closed, flock | No remote transport retry observed in runtime |
| Holdout | approved replay data hash+date check before cases; noholdoutread field; gold-free inference | No final-holdout score produced |
| Decision/report | historical full/selected actualusage, regressions, keep candidate pending Apertus | Official composite always null; no production promotion |
| Skill | project install, source commit, unchanged upstream and explicit adaptation | Fresh-thread autodiscovery unverified |
| Container/submission | Python contract kept; runtime Apertus guard | Docker socket inaccessible, no permissions changed; actual Apertus and report/submission pending |

Verification commands and local evidence paths are in README. No new model generation is necessary for these local checks.


Revision 2 adds the two independent-QA reproductions and cache-index rehash/raw-source consistency tests. Normal resume and changed gold remain covered without duplicate inference. Prior version1 caches are retained and rejected. Independent QA judged all six alternative-page citations correct; official score remains null. A new exact-patch QA pass is required after this fix.
