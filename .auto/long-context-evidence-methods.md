# Long-context evidence reading: qualified methods

Accessed 2026-10-15 UTC. Primary-paper research only, within the supplied authorization ending Unix 1792098000. No adoption, production, push, implementation, model calls or experiments are authorized by this note.

## Decision

**The papers support distinguishing evidence availability, successful retrieval, and semantic support. They do not establish a winning Apertus design.** Full-source exposure avoids deliberate fact deletion but does not guarantee attention to relevant facts. Targeted excerpts can improve effective visibility while hiding unselected facts if they replace the source. Preserve this distinction when assessing the finite-ID selector.

Supplied status, not independently audited: baseline mean Q **.729** on exposed DEVELOPMENT60; first quote-writing reviewer failed structurally; finite-ID selection with full original source and host-restored exact **80/120 code-point** fragments is being integrated. No new selector quality result exists. Host restoration establishes literal provenance, not relevance, governing scope, entailment or contradiction. Paper facts cannot rescue failed quality gates.

## Three directly inspected primary sources

**1. Liu et al., Lost in the Middle**, [v3, revised 2023-11-20](https://arxiv.org/abs/2307.03172v3), [full text](https://arxiv.org/html/2307.03172v3), §§2.1-2.3, 3, 4.2, 5. Tasks: multi-document question answering and synthetic key-value retrieval. Models include MPT-30B-Instruct, LongChat-13B (16K), GPT-3.5-Turbo/16K (0613), Claude-1.3/100K; GPT-4 receives a subset evaluation. In §2.3: “Model performance is highest when relevant information occurs at the beginning or end of its input context.” The controlled QA setting contains one answer-bearing document among distractors, rather than distributed governing conditions. §4.2 finds query-aware contextualization helps synthetic retrieval far more than multi-document QA. §5 separates retriever recall from reader performance: more available answer-bearing documents do not guarantee better use.

**Transfer:** context capacity and evidence position are separate risks. Full-source exposure is not effective coverage. **Does not transfer:** these older models and QA/key lookup tasks establish neither Apertus multilingual NLI performance nor a remedy through prompt reordering. This is not a reason to retry completed v4..v16 prompt/order failures.

**2. Hsieh et al., RULER**, [v3, revised 2024-08-06](https://arxiv.org/abs/2404.06654v3), [full text](https://arxiv.org/html/2404.06654v3), §§3-5, 8, Table 3. It evaluates **17 models on 13 tasks**: retrieval variants, variable tracking, aggregation and QA. Models include GPT-4, Gemini-1.5-Pro, Llama-3.1 8B/70B, Qwen2 and long-context open models. §4 tests lengths **4K through 128K tokens**; “effective length” is thresholded against Llama2-7B at 4K, not a universal semantic capacity. §5 distinguishes distractor susceptibility, incomplete retrieval, tracking failure and aggregation failure. §8 explicitly labels “Lack of position controlling” and “Lack of correlation with realistic long-context tasks,” calling RULER “convenient behavioral checks.”

**Transfer:** finding one exact fragment is weaker than retrieving all relevant conditions or combining facts. **Does not transfer:** its synthetic checks are not multilingual source-NLI validation, and its threshold cannot certify Apertus. Length-averaged scores do not settle position effects. Supplied packets near **240,000 bytes**, including about **193,000 source-text bytes**, cannot be mapped to paper token lengths without the actual tokenizer; preserved facts can still be overlooked.

**3. Gao et al., Enabling Large Language Models to Generate Text with Citations (ALCE)**, [v2, revised 2023-10-31](https://arxiv.org/abs/2305.14627v2), [full text](https://arxiv.org/html/2305.14627v2), §§2, 3.3, 4.2, 5.1 and Limitations. Tasks: ASQA, QAMPARI and ELI5 retrieval-grounded answers; models include ChatGPT, GPT-4 and open LLaMA-family systems. Citation recall requires statements to be entailed by their cited passages, not merely attached to existing text. Citation precision tests irrelevant citations; the paper acknowledges limitations for partial support.

§4.2 calls summaries/snippets “lossy compressions.” §5.1 reports improved correctness with summaries/snippets but citation-quality costs on ASQA/ELI5; interactive full-passage checks did not improve results. **Transfer:** provenance and semantic support need separate treatment, and compact evidence can trade coverage for focus. **Does not transfer:** generated answer citation is not multilingual NLI; ALCE's learned NLI evaluator is not an oracle, nor does ALCE validate exact 80/120-code-point fragments or an additive retrieval/checking stack.

## At most two deferred decompositions

These are inferences, not tested prescriptions. Each needs a distinct prospective freeze and fresh authorization; heldout reserve remains sealed. Never select using individual gold.

1. **Replace ordinary NLI voting with answer-blind nomination, then a bounded governing-scope check.** Nomination sees the original source; checking must expose surrounding conditions, attribution, negation and exceptions, not only the selected fragment. The second stage depends on the first nomination: it is not independent corroboration and cannot recover every unselected fact. Exact short fragments can omit a remote governing clause.
2. **Two complementary full-source fact channels**, isolated from each other's outputs and candidate labels. Retaining the source avoids selection-only visibility, but both channels can miss the same facts. Role diversity and answer blindness do not establish statistical independence.

Neither is additive. Two guaranteed review calls + ordinary NLI + two parent calls already use **5 × 60 = 300 physical requests**, before repairs. Logical ceilings are parent ≤3, helper1 ≤2, helper2 ≤2 per case, not permission for seven physical calls. Retain all supplied limits: 300 seconds, output ≤256, temperature 0, whole payload ≤240,000 bytes, ≤300 POST/job and ≤78,720,000 tokens. Any later method must freeze repair accounting within these limits; no new live assessment is authorized here.

Inspected: the three pinned papers and existing independent-review note, without repeating its research. No local benchmark data, coder-owned bound_review files, protected source bodies, credentials or hidden reasoning were inspected; no local quality claim was verified.
