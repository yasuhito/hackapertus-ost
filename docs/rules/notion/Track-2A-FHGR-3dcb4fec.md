Source URL: https://hackapertus.notion.site/3dcb4fec112a80e58117ed7e551387ea
Fetch date: 2026-10-12

# Track 2A: FHGR

;lPz: 🟡🔴 Intermediate–Advanced

DBFd: SwissGov-RSD: Detecting Cross-Lingual Semantic Differences in Swiss Government Websites

E_=Z: University of Zurich - Department of Computational Linguistics

GSrM: **Apify**

^GB[: [View challenge →](https://notion.genaizurich.ch/gaz26-hackathon)

tHvE: 📆  **02 October, 12:30** CET, {{link}}
📆  **08 October, 12:00** CET, {{link}}

## AI-Powered Job Interview Coach

### 🎯 Challenge Overview

**Domain:** Education

#### → Context & Background

FHGR is extending its established **Profolio** career-orientation platform with AI-supported, personalised guidance for young people entering the world of work. A key component is **simulated job-interview training** — letting students practise realistic interviews and receive individualised feedback in a safe environment. As Switzerland is multilingual, the solution should support **German, French and Italian**, including Swiss dialects where appropriate. Apertus is the underlying LLM, chosen for its support of all three Swiss national languages and dialects and for enabling privacy-preserving, locally deployable AI.

#### → Problem Description

Young people have limited opportunities to practise job interviews and get individualised feedback before applying for an apprenticeship or first job, and teachers cannot provide repeated one-to-one training at scale. The challenge is to create a natural, realistic conversational interview experience that adapts to the student, evaluates their answers, and gives constructive, development-oriented feedback.

#### → Primary Objective

Develop an **Apertus-based AI job-interview coach** that conducts realistic, adaptive interviews and provides meaningful, personalised feedback — an engaging, scalable training experience that helps students improve their interview skills, confidence, and ability to present their strengths. Should support German, French and Italian (Swiss dialects a plus). Support for future integration of real-time text-to-speech (to simulate a spoken interview) is beneficial.

### 🔧 Resources, Tools & Support

#### [https://github.com/fhgr/Hackapertus](https://github.com/fhgr/Hackapertus)

#### → Datasets

- Example apprenticeship/job interview questions (common and role-specific).

- Example candidate answers at different quality levels.

- Expert/didactic annotations on what makes an answer strong, weak, incomplete or problematic.

- Evaluation criteria: clarity, relevance, motivation, self-awareness, communication, ability to give concrete examples.

- Examples in German, ideally including selected Swiss-German dialect examples.

- A small set of synthetic candidate profiles and job/apprenticeship descriptions for personalised interviews.

#### → Supporting Materials

- Technical starter material: a Docker container with LangChain/LangGraph + Aegra for deployment.

- Guidelines on developmentally appropriate, constructive feedback for adolescents.

- A description of the Swiss apprenticeship application/interview process.

- Sample job/apprenticeship profiles and interview scenarios.

- A suggested interview flow (introduction → motivation → strengths/weaknesses → situational questions → candidate questions → feedback).

- Examples of good vs. poor AI feedback.

- Description of the Swiss education & vocational training system for apprenticeships (EBA/EFZ), including the Federal Vocational Baccalaureate (BM1/BM2).

#### → Mentorship

Technical/domain questions handled in the online Q&A sessions with the challenge provider (dates below).
Book a session with our mentors: 
[https://hackapertus.notion.site/mentors](https://hackapertus.notion.site/mentors)


### 💻 Technical Preferences

|  |

| **Preferred languages / frameworks** | Python; LangChain or LangGraph; Aegra (for deployment). |

| **Recommended platforms** | Docker image, local or cloud (local preferred). |

| **Specific AI models** | Apertus 1.5 — 8B. |

### 📦 Deliverables & Judging

Github repo template:
[https://github.com/HackApertus/project-template](https://github.com/HackApertus/project-template/tree/main/track_2a)

#### → Expected outputs

A runnable Docker container + deployment instructions; source code; documentation of the chosen approach and underlying idea & strategy; a visual overview of the application's functionality.

Technical report template (can be adjusted):
[https://github.com/HackApertus/project-template/blob/main/track_2a/technical_report.md](https://github.com/HackApertus/project-template/blob/main/track_2a/technical_report.md)

#### → Success criteria

Interview quality is measured qualitatively and quantitatively using an **LLM-as-judge** approach; the underlying metrics and prompts will be published before the challenge.

#### → Evaluation criteria

- **Practicality & runtime (REQUIRED):** must run on consumer-grade hardware with **< 32 GB VRAM**, averaging **< 5 LLM calls per candidate answer**.

- **Performance — 50%:** score on the provided LLM-as-a-Judge benchmark (quality, relevance, appropriateness of interactions and feedback).

- **Consistency — 25%:** reliable performance across scenarios, candidate profiles, questions and languages.

- **Innovation — 25%:** novel methods, architectures or creative combinations of techniques.

### ⚖️ Ethics & Compliance

#### → Ethical guidelines

Data privacy and protection: the final solution must run on consumer-level GPU hardware to allow on-premise deployment.

#### → Legal & compliance

Privacy & data security: Swiss data-protection laws; GDPR. IP: use of open-source frameworks is preferred.

### 📅 Online Session

📆 02 October, 12:00-12:45 CET, [link](https://luma.com/g7mccjtk)
📆 08 October, 12:00-12:30 CET, [link](https://luma.com/dxtzhae0)

**Speakers:** Norman Süsstrunk, FHGR

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
An Apertus-based AI interview coach that runs realistic, adaptive job interviews with young people and gives them personalised, constructive feedback.

**Which languages must it support?**
German, French and Italian; Swiss dialects are a plus.

**Which model should I use?**
Apertus 1.5 — 8B.

**Are there hard runtime limits?**
Yes — it must run on consumer-grade hardware (< 32 GB VRAM) and average fewer than 5 LLM calls per candidate answer.

**How is it scored?**
50% performance (LLM-as-judge benchmark), 25% consistency, 25% innovation — with the practicality/runtime limits as a required gate.

**What do I hand in?**
A runnable Docker container + deployment instructions, source code, documentation of the approach, and a visual overview of the app.
