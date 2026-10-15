# Fictional provider diagnostic result

The owner requested the next iteration. We selected the deferred provider-compatibility investigation, not another PUBLIC60 evaluation. Before inference,12 fixed fictional argument-copy requests were frozen: two existing models, three requested argument tuples, two schema arms. Paired messages were identical. The conditional arm copied the exact H2 root conditional, not a newly tuned encoding. There was no NLI task or production change.

| Model | Simple schema violations | Conditional schema violations |
|---|---:|---:|
| 8B | 0/3 | 0/3 |
| 70B | 0/3 | 3/3 |

The70B conditional failures comprised two missing-field responses and one truncated response. All schema-valid responses exactly copied the requested arguments. Each response was validated against its actual complete schema using installed TypeBox Compile. Twelve HTTP200 responses had known usage and matching model identities:1520 input tokens,450 output tokens,1970 total. Original inference phase17.943960991920903 seconds; summed HTTP wall16.553048715926707 seconds.

This reproduces conditional incompatibility on fictional tasks. It does not identify whether the cause is model behavior, template handling or constrained decoding, and does not establish NLI performance or generalization. Retain the application's simple native schema. PUBLIC60 was not rerun.

## Publication failure and read-only recovery

Run29 collected all12 responses and published completed.json, but failed before printing metrics. The original atomic save(replace=True) called unlink after os.replace had already removed the temporary name. The original53 tests lacked replacement-path coverage. Its logged primary0 is an unavailable crash sentinel, not a measured baseline.

A recovery-only helper fixes replacement and adds regression tests;63 tests pass. Original helper, control and all26 original job files remain unchanged. Archived original dispatcher bytes match their original source pins; new dispatcher/recovery sources have separate pins. Run30 revalidated the same saved responses and passed checks without any API calls. Its primary3 is the FIRST valid diagnostic observation, not a worsening from zero or a production improvement. Dashboard0/+Infinity comparisons are invalid because zero was unavailable. Keep retains diagnostic evidence only.

Original protocol SHA256:654ae624fe7a007a3a2308c31a751caf3c90915b1a5936a2d58aaf0a8ae0bde3.
Recovery protocol SHA256:0780604028a8d0d28c607f8252864fd14ebab2d0a9425ab9ef26dad867836709.

## Exposure incident

During setup a subagent's broad search displayed existing gold excerpts. The hypothesis, exact schema pair and all12 fictional request definitions had already been specified before that search. None were changed using those excerpts. This incident was disclosed before inference. No claim of unseen NLI validation is made. Further searches were restricted to explicit diagnostic/source paths.
