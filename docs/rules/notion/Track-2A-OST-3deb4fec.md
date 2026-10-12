Source URL: https://hackapertus.notion.site/3deb4fec112a80258fd2ddc61616011d
Fetch date: 2026-10-12

# Track 2A: OST

## Multilingual Natural Language Inference over Swiss Official Voting Booklets

### 🎯 Challenge Overview

**Domain:** Civic / Democracy

#### → Context & Background

Switzerland's direct democracy asks citizens to vote several times a year on complex legal, social and financial issues. For each national vote, the federal government publishes an official **voting booklet (Abstimmungsbüchlein)** explaining the proposal, its background, the arguments of supporters and opponents, and the position of the Federal Council and Parliament. These materials are a rich source of complex, structured and unstructured information — proposal descriptions, legal and financial detail, arguments, qualifications, dates, numbers and statements across different linguistic contexts — and an authoritative, relatively balanced basis for understanding what's being voted on. They therefore make a valuable **real-world document corpus for investigating how well multilingual models like Apertus understand and reason over complex documents.** During campaigns, voters meet many claims about proposals, and checking them against the official materials is difficult and time-consuming. This challenge explores how Apertus can be applied to this **document-grounded claim-verification** task, while remaining multilingual.

#### → Problem Description

Determining the relationship between a natural-language claim and information in a document is hard: relevant information may be spread across sections, expressed with qualifications or negations, or held in tables and other structures. Given an official Swiss voting booklet and a claim, the system must decide whether the document:

- **entails** the claim;

- **contradicts** the claim; or

- is **neutral** — the document doesn't provide enough information either way.

Core task: **Document + Claim → Entailment / Contradiction / Neutral.**
This is specifically about document extraction and **document-grounded natural language inference (NLI)** using Apertus. It is *not* general question-answering, and does not require deciding whether a claim is objectively true in the real world — only whether Apertus can reliably determine the relationship between a claim and the source document.

#### → Primary Objective

The objective is to build a **practical, multilingual claim-verification application** powered by Apertus that can operate over complex Swiss government documents.

The challenge should demonstrate both:

1. **How reliably Apertus can perform document-grounded NLI, and**

1. **How efficiently the relevant document context can be provided to the model.**

A straightforward baseline is to provide the complete voting booklet together with the claim directly to Apertus.

However, voting booklets can contain substantial amounts of text and complex document structure. Supplying the entire document may result in high context length and token consumption.

Participants are therefore encouraged to investigate whether the document can be processed, selected or compressed before being provided to Apertus, while maintaining reliable NLI performance.
The challenge deliberately leaves the technical approach open.

In particular, the system should be able to:

- **Parse/extract** a given voting booklet using Apertus.

- **Parse political claims** expressed in natural language (text) using Apertus.

- **Assess** the relationship between a claim and the booklet, using Apertus as an entailment model.

- **Classify** claims according to whether they are supported, contradicted, or not sufficiently addressed by the official materials.

- **Provide transparent evidence,** allowing users to see the exact passages from the voting booklet that support the system’s assessment.

The broader objective is to make **reliable, source-based political information more accessible, transparent, and scalable**, while demonstrating how Apertus can support democratic participation.

The challenge is intended to determine which approaches (RAG, Docling, OCR etc.) work best with Apertus rather than requiring participants to implement a predefined pipeline. No specific document-processing, retrieval or RAG architecture is mandatory.

A particularly interesting comparison is between:
Full document → Apertus → NLI
and approaches such as:
Document → processing/retrieval → selected context → Apertus → NLI

This allows participants to explore the trade-off between NLI performance and the amount of context supplied to the model.

**Multilingual Dimension**

The challenge covers Switzerland's principal official languages represented in the dataset: German, French, and Italian.

Claim and booklet pairs will be evaluated across these languages to assess the multilingual NLI capabilities of Apertus. This includes  cross-lingual document–claim pairs.

### 🔧 Resources, Tools & Support

#### → Datasets

The primary corpus is official Swiss **federal voting booklets (Abstimmungsbüchlein)**, provided as **PDF documents** with structured and unstructured text (proposal descriptions, arguments, Federal Council & Parliament recommendations, legal/financial information). A **benchmark dataset** consists of document–claim pairs with **human-annotated NLI labels** and the exact supporting paragraph where applicable. Document–claim pairs can be in different languages (German, French, Italian) — i.e. multilingual and cross-lingual.

#### → Supporting Materials

1. Challenge dataset: [https://huggingface.co/datasets/OSTswiss/MNLIoverSwissVotingBooklets](https://huggingface.co/datasets/OSTswiss/MNLIoverSwissVotingBooklets)

1. Relevant source document:
[https://www.bk.admin.ch/de/sammlung-der-abstimmungsbuechlein-seit-1978](https://www.bk.admin.ch/de/sammlung-der-abstimmungsbuechlein-seit-1978)

1. document–claim examples (available in the dataset)

1. NLI label definitions: in the readme of the dataset


The technical task focuses on **Natural Language Inference (NLI)** / Recognizing Textual Entailment — the inference relation between two short ordered texts (entailment, contradiction, neutral). An English reference dataset for familiarisation: `huggingface.co/datasets/stanfordnlp/snli`.

#### → Solution API Guide

[solution-api-guide](solution-api-guide-ef5b4fec.md)

#### → Mentorship

Technical/domain questions handled in the online Q&A sessions with the challenge provider (dates below). Check out our mentors: [link](/p/fe7b4fec112a8342ad42810975340907?pvs=25)

Discord channel for this challenge: [link](https://discord.gg/bfmRY36n3).

### 💻 Technical Preferences

|  |

| **Preferred languages / frameworks** | Python. |

| **Recommended platforms** | Designed to run locally using Dockerized services. |

| **Specific AI models** | Apertus v1.5 |

### 📦 Deliverables & Judging

Github repo template:
[https://github.com/HackApertus/project-template](https://github.com/HackApertus/project-template/tree/main/track_2a)

#### → Expected outputs

An application that takes a Swiss voting booklet and a natural-language claim as input and determines the claim's relationship to the booklet, supporting **all combinations of French, Italian and German** (e.g. booklet in French, claim in German). It returns a classification 0–2:

- **0 – Entailment:** the booklet supports the statement.

- **1 – Neutral:** the booklet doesn't provide enough information either way.

- **2 – Contradiction:** the booklet contradicts the statement.
Where possible, it also returns the **relevant passage(s)** used (multiple passages allowed where the classification depends on information spread across the document), making results transparent and verifiable. Participants should report **input/context token usage and inference time**. The application should provide a **CLI** for generating entailment predictions.


Technical report template (can be adjusted):
[https://github.com/HackApertus/project-template/blob/main/track_2a/technical_report.md](https://github.com/HackApertus/project-template/blob/main/track_2a/technical_report.md)

#### → Success criteria

Demonstrates that Apertus can perform reliable multilingual NLI over complex Swiss government documents. The solution should: correctly classify document–claim pairs (entailment/contradiction/neutral); provide the relevant evidence passage(s); support the benchmark languages; use Apertus as the primary model; be reproducible; and document how document context is prepared and supplied. A human-generated benchmark is provided during the challenge for development and testing.

#### → Evaluation criteria

Primary criterion: performance on a **held-out benchmark** of human-annotated document–claim pairs, measuring three-way NLI classification via **macro-F1** across Entailment, Contradiction and Neutral. Performance may also be analysed across German, French and Italian. Evidence passages are assessed for relevance and correctness (multiple passages may be valid — no single "correct" passage is assumed). Solutions are also compared on **input/context token usage** and **inference time**, so both NLI effectiveness *and* efficiency are judged, alongside whether classifications are properly grounded in the source.

### ⚖️ Ethics & Compliance

#### → Ethical guidelines

Because the documents concern political and civic topics, systems should avoid presenting model predictions as authoritative political advice. Where possible, outputs should be traceable to the source document.

#### → Legal & compliance

Participants must comply with the Hack Apertus terms and applicable licensing requirements.

### 📅 Online Session

📆 02 OCT, 13:30-14:15 CEST: **Challenge Info Session: OST **- Sign-up [link](https://luma.com/qz7x62m8)

📆 08 OCT, 12:00-12:30 CEST: **Challenge Q&A: OST**- Sign-up [link](https://luma.com/nkvf2m7y)

**Speakers:** Prof. Dr. Mitra Purandare & Abinas Kuganathan, OST


### Recordings & Slides

[1.10.26 «Hack Apertus» - Kick-off Online Hackathon](1-10-26-Hack-Apertus---Kick-off-Online-Hackathon-3f0b4fec.md)

[2.10.26 «Hack Apertus» - Apertus Introduction](2-10-26-Hack-Apertus---Apertus-Introduction-3f0b4fec.md)

[2.10.26 «Hack Apertus» - Apertus 1.5 under test: academic and real business tasks](2-10-26-Hack-Apertus---Apertus-1-5-under-test-academic-and-real-business-tasks-3f0b4fec.md)

[2.10.26 «Hack Apertus» - Challenge info session: ZHAW](2-10-26-Hack-Apertus---Challenge-info-session-ZHAW-3f0b4fec.md)

[2.10.26 «Hack Apertus» - Challenge info session: FHGR](2-10-26-Hack-Apertus---Challenge-info-session-FHGR-3f0b4fec.md)

[2.10.26 «Hack Apertus» - Challenge info session: UZH](2-10-26-Hack-Apertus---Challenge-info-session-UZH-3f0b4fec.md)

[2.10.26 «Hack Apertus» - Challenge info session: OST](2-10-26-Hack-Apertus---Challenge-info-session-OST-3f0b4fec.md)

[2.10.26 «Hack Apertus» - Challenge info session: OpenParlData](2-10-26-Hack-Apertus---Challenge-info-session-OpenParlData-3f0b4fec.md)

[08.10.26 «Hack Apertus» - Challenge Q&A: OpenParlData](08-10-26-Hack-Apertus---Challenge-Q-A-OpenParlData-3f3b4fec.md)

[08.10.26 «Hack Apertus» - Challenge Q&A: OST](08-10-26-Hack-Apertus---Challenge-Q-A-OST-3f3b4fec.md)

### FAQ

**What am I building, in one sentence?**
An Apertus-powered application that decides whether a natural-language claim is entailed, contradicted, or unaddressed by an official Swiss voting booklet — and shows the supporting passage(s).

**What exactly is the task?**
Document-grounded Natural Language Inference (NLI): Document + Claim → Entailment / Contradiction / Neutral. It's not general QA and not about real-world truth — only the claim–document relationship.

**Which languages must it handle?**
German, French and Italian, including cross-lingual pairs (booklet and claim may be in different languages).

**What data do I get?**
Official voting booklets as PDFs, plus a benchmark of human-annotated document–claim pairs with supporting paragraphs. SNLI is an English reference set for familiarisation.

**Which model should I use?**
Apertus, as the primary model. The document-processing approach (RAG, Docling, OCR, compression…) is open — a key comparison is full-document vs. retrieved/selected context.

**How is it judged?**
Macro-F1 over the three NLI classes on a held-out benchmark, plus evidence relevance, and efficiency (token usage and inference time).
