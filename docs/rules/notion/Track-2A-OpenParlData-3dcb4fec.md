Source URL: https://hackapertus.notion.site/3dcb4fec112a80b58579cf3168827f8e
Fetch date: 2026-10-12

# Track 2A: OpenParlData

;lPz: 🟡🔴 Intermediate–Advanced

DBFd: SwissGov-RSD: Detecting Cross-Lingual Semantic Differences in Swiss Government Websites

E_=Z: University of Zurich - Department of Computational Linguistics

GSrM: **Apify**

^GB[: [View challenge →](https://notion.genaizurich.ch/gaz26-hackathon)

tHvE: 📆  **02 October, 12:30** CET, {{link}}
📆  **08 October, 12:00** CET, {{link}}

## Extracting Parliamentary Affairs from PDFs into One Common Structure

### 🎯 Challenge Overview

**Domains:** Public Sector / GovTech / Democracy / Politics

#### → Context & Background

Switzerland has parliaments at three levels — the Federal Assembly, 26 cantonal parliaments, and several hundred municipal/city parliaments — operating across different languages. Most proceedings involve a common object: a **parliamentary affair** (motion, postulate, interpellation, written question or initiative), submitted by members, answered by the executive, and usually closed by a decision. **OpenParlData** (openparldata.ch) scrapes 90 Swiss parliaments daily and publishes ~300,000 parliamentary affairs as open data, via API (`api.openparldata.ch`) and bulk exports (`files.openparldata.ch/exports/`).
Much valuable information is buried in parliamentary **PDFs** and can't be reliably extracted into structured form — the question asked, the government's answer and reasoning, the decision, the people involved. Documents vary hugely: born-digital, scanned, some with handwritten stamps/signatures, tables and annexes. Generic document AI (e.g. Docling) gives a clean but domain-agnostic page representation; ad-hoc LLM prompting produces a different JSON shape for every body. OpenParlData already runs the surrounding infrastructure (a prompt-driven extraction workbench with side-by-side PDF / Text / JSON / Docling views and a manual review step), so **what this challenge produces can go into real operation, not just a demo.**

#### → Problem Description

There is no shared, machine-readable format in which a parliamentary affair can be expressed so two parliaments become comparable — and no reliable way to produce one from existing PDFs. Three gaps:

1. **Format gap.** Docling/plain text are too generic (document structure, not affair semantics); Akoma Ntoso is rich but heavyweight and rooted in legislative drafting; TEI/Parla-CLARIN targets speech/debate transcripts. What's missing is a **middle layer** (like JATS for scientific papers) that preserves document structure *and* captures affair semantics (type, submitter & co-signatories, addressed body, question/answer pairings, dates, procedural history, decisions, links to related affairs).

1. **Extraction gap.** Turning heterogeneous, multilingual, partly-scanned PDFs into that format at 300,000-document scale needs an LLM — and an unconstrained, untraceable LLM invents values.

1. **Verification gap.** No gold standard and no metric, so nobody can say whether a pipeline is good enough to run unattended.

#### → Primary Objective

Design and prototype a **structured representation model for parliamentary affairs**, plus a working **Apertus-driven pipeline** that produces it from real PDFs. Three deliverables:

- **The representation model** — a versioned, documented schema + controlled vocabularies (affair types, actor roles, procedural states, decision outcomes). Small enough for a municipality, expressive enough for national parliaments; handles embedded images, tables (e.g. budgets), annexes. Ideally maps concepts to existing standards (Akoma Ntoso, Parla-CLARIN, Popolo, Docling).

- **The converter** — prompts + code turning real PDFs into valid structured data using Apertus, **with provenance**: each value keeps a reference to page and, where possible, the text span, so a reviewer can verify quickly.

- **The evidence** — evaluate on a multilingual, multi-level sample against a manually-checked gold set, and demonstrate value by answering at least one cross-parliamentary question that can't currently be answered reliably.

### 🔧 Resources, Tools & Support

#### → Datasets

Provided by OpenParlData:

- **Full corpus** — ~300,000 parliamentary affairs (federal/cantonal/municipal) with structured metadata (title, type, contributors, dates, status, events) + linked source documents. Public REST API: `api.openparldata.ch/v1/` (docs at `api.openparldata.ch/documentation`).

- **Source documents** — original PDFs (born-digital and scanned), plus already-extracted plain text (Apache PDFBox/Tika) for a large subset.

- **Data protection** — the corpus contains only material already published by the parliaments themselves.

#### → Supporting Materials

PDFs as binary files: `files.openparldata.ch/doc/`

#### → Mentorship

Technical/domain questions handled in the online Q&A sessions with the challenge provider (dates below). Check out our mentors: [link](/p/fe7b4fec112a8342ad42810975340907?pvs=25)

### 💻 Technical Preferences

|  |

| **Preferred languages / frameworks** | No restriction. For reference, the production stack is Python (FastAPI, Pydantic) with PostgreSQL and an Angular/React front end; ETL pipelines use Apache Hop. |

| **Recommended platforms** | Develop locally to start. OpenParlData runs on a self-managed VPS with a GitLab deploy process; ~20 GB RAM available for self-hosted LLMs on prod, though a specific LLM provider (e.g. Infomaniak) is intended. A dedicated container can later be added to OpenParlData's docker-compose landscape. |

| **Specific AI models** | Apertus v1.5 — 8B or 70B |

| **Model sources** | [huggingface.co/swiss-ai/Apertus-v1.5-8B<br>](https://huggingface.co/swiss-ai/Apertus-v1.5-8B)[huggingface.co/swiss-ai/Apertus-v1.5-70B](https://huggingface.co/swiss-ai/Apertus-v1.5-70B) |

### 📦 Deliverables & Judging

Github repo template:
[https://github.com/HackApertus/project-template](https://github.com/HackApertus/project-template/tree/main/track_2a)

#### → Expected outputs

A **reference implementation**: a public repository containing the PDF-to-schema converter, the Apertus prompts, possibly a validator, and a README with context and samples.

Technical report template (can be adjusted):
[https://github.com/HackApertus/project-template/blob/main/track_2a/technical_report.md](https://github.com/HackApertus/project-template/blob/main/track_2a/technical_report.md)

#### → Success criteria

The main criterion is **insight**: does the team reach a well-founded conclusion on whether a common schema for parliamentary affairs is feasible, which parts can be represented consistently across parliaments, and where fundamental differences remain? A convincing negative or partial answer counts as success. If a workable schema emerges, demonstrate it on a broad, diverse set of real documents — showing an LLM can reliably transform heterogeneous PDFs into the schema across document types, languages and levels of government.

#### → Evaluation criteria

- **Insight** — how well the submission answers whether a common schema is feasible.

- **Breadth & applicability** — how well the approach works across different parliaments, document types and languages.

### ⚖️ Ethics & Compliance

#### → Ethical guidelines

Minimise hallucinations and keep extracted content traceable to the original source. Favour **conservative extraction** — do not introduce, omit or substantively alter information present in the source; stay faithful to the original wording and meaning (the original PDF always remains the authoritative reference). Significant *formatting* changes are encouraged where they improve usability (removing page numbers/headers/footers, restructuring, improving readability, preserving/adding links). Clearly distinguish extracted content from generated/inferred content; where information can't be reliably extracted, make that transparent rather than guess.

#### → Legal & compliance

All outputs should be openly accessible and reusable. Parliamentary affairs and related documents are assumed to be generally publicly accessible, and not necessarily protected by copyright.

### 📅 Online Session

📆 02 October, 14:30-15:15 CET, [link](https://luma.com/mne4e0m5)
📆 08 October, 12:00-12:30 CET, [link](https://luma.com/3avq28dg)

**Speaker:** Christian Gutknecht, OpenParlData / Glue AG

### Recordings & Slides

[08.10.26 «Hack Apertus» - Challenge Q&A: OpenParlData](08-10-26-Hack-Apertus---Challenge-Q-A-OpenParlData-3f3b4fec.md)

[08.10.26 «Hack Apertus» - Challenge Q&A: OST](08-10-26-Hack-Apertus---Challenge-Q-A-OST-3f3b4fec.md)

[2.10.26 «Hack Apertus» - Challenge info session: OpenParlData](2-10-26-Hack-Apertus---Challenge-info-session-OpenParlData-3f0b4fec.md)

[2.10.26 «Hack Apertus» - Challenge info session: OST](2-10-26-Hack-Apertus---Challenge-info-session-OST-3f0b4fec.md)

[2.10.26 «Hack Apertus» - Challenge info session: UZH](2-10-26-Hack-Apertus---Challenge-info-session-UZH-3f0b4fec.md)

[2.10.26 «Hack Apertus» - Challenge info session: ZHAW](2-10-26-Hack-Apertus---Challenge-info-session-ZHAW-3f0b4fec.md)

[2.10.26 «Hack Apertus» - Challenge info session: FHGR](2-10-26-Hack-Apertus---Challenge-info-session-FHGR-3f0b4fec.md)

[2.10.26 «Hack Apertus» - Apertus 1.5 under test: academic and real business tasks](2-10-26-Hack-Apertus---Apertus-1-5-under-test-academic-and-real-business-tasks-3f0b4fec.md)

[2.10.26 «Hack Apertus» - Apertus Introduction](2-10-26-Hack-Apertus---Apertus-Introduction-3f0b4fec.md)

[1.10.26 «Hack Apertus» - Kick-off Online Hackathon](1-10-26-Hack-Apertus---Kick-off-Online-Hackathon-3f0b4fec.md)

### FAQ

**What am I building, in one sentence?**
A structured representation (schema) for parliamentary affairs plus an Apertus-driven pipeline that extracts it from real parliamentary PDFs, with provenance back to the source.

**What data do I get?**
~300,000 affairs with metadata via the OpenParlData API, plus original PDFs (born-digital and scanned) and pre-extracted plain text for a large subset.

**Which model should I use?**
Apertus. Language/framework are otherwise unrestricted.

**Is a "negative" result acceptable?**
Yes — the main criterion is insight. A well-founded conclusion that a common schema is only partly feasible (and where it breaks) counts as success.

**What matters most in the extraction?**
Traceability and faithfulness — conservative extraction, no invented values, each value linked to its page/text span; unreliable cases flagged rather than guessed.

**Can this go into production?**
Potentially yes — OpenParlData already runs the surrounding extraction workbench and import workflow, so a good result can be put into real operation.
