Source URL: https://hackapertus.notion.site/665b4fec112a828c809981529bb3607d
Fetch date: 2026-10-12

# Track 2A: ZHAW

;lPz: 🟢🟡 Beginner–Intermediate

DBFd: AI-Powered Analysis of Survey Data from Swiss Public Sector Research

E_=Z: ZHAW

GSrM: **GoCalma**

^GB[: [View challenge →](https://notion.genaizurich.ch/gaz26-hackathon)

tHvE: 📆  **02 October, xxxx** CET, {{link}}
📆  **08 October, xxxx** CET, {{link}}

### See It, Say It, Pick It — Vision-Language Grounding for a Real Robot Arm

### 🎯 Challenge Overview

**Domain:** Manufacturing & Industrial Robotics (pick-and-place, assembly, logistics) · related: Vision-Language Models, Embodied AI, Industrial AI

#### → Context & Background

Industrial robots excel at repeating fixed programs in rigid environments but struggle when tasks change frequently. In small-batch Swiss manufacturing, operators constantly adapt to new orders. Natural language is the most intuitive interface for this variability — but cloud AI is a non-starter: under strict IP confidentiality and the revised Data Protection Act (revDSG), Swiss companies cannot stream production imagery to foreign servers. The intelligence must live on the factory floor. This challenge tests whether **Apertus 1.5 — Switzerland's open model — can serve as the cognitive brain for sovereign, edge-computed industrial robotics.** ZHAW opens its physical hardware: a UR5 workcell with RGB-D and LiDAR sensing, a calibrated camera, and a proven grasping pipeline (six years of research). Your task is to build the missing cognitive layer that turns plain-English instructions and raw camera feeds into safe, executable robot action plans.

#### → Problem Description

Programming a robot arm is a specialist job, and making it natural requires grounding language in reality — but LLMs hallucinate physics. Teams use an open VLM to turn a camera feed into a scene graph, then prompt Apertus to translate an instruction (e.g. *"Clear the table but leave the blue tray"*) into a safe, ordered list of actions. Three specific failures matter:

1. **Visual grounding** — connect words to *one object at one position* (VLMs name what's in an image but are weak on *where*).

1. **Order & physics** — one sentence can mean several actions in a required order; the gripper holds one object at a time.

1. **Ambiguity & refusal** — some instructions are under-specified, name absent objects, or are physically impossible. The correct answer is then a **question or a refusal**, not a plan.
In ZHAW's pilot, Apertus produced a confident plan for *every* case — including for an object that wasn't on the table. For a machine that moves, that's the failure that matters most.

#### → Primary Objective

Build a **zero-shot pipeline from image + text to robot action**, using an open vision model together with Apertus. No training needed. Input: one workcell photo + one English instruction. Output: a JSON object with the **pixel position** of the target object, a short ordered action list, *or* a question / refusal. The pixel position is key — the challenge provides camera parameters and hand-eye calibration, so a correct pixel converts directly into a robot coordinate for execution on the physical arm after the event.
*Recommended (not required):* open VLM → structured scene graph → prompt Apertus (tool-calling / constrained decoding) → ordered action list. Teams may also try Apertus alone via its image input — comparing the two is one of the most useful results. **No robotics knowledge and no robot are required.**

### 🔧 Resources, Tools & Support

#### → Datasets

Raw sensor snapshots from a physical, calibrated robot cell (teams work zero-shot; no training):

- **Ten snapshot folders** (one per scene): RGB image (PNG), 16-bit depth map (PNG), camera intrinsics + hand-eye calibration (JSON), and five English instructions (some valid, some deliberately unsafe). No object labels, no scene graph — extracting the scene is part of the task.

- **Fifty instructions** across six categories: simple, relative position, multi-step, ambiguous (must ask), impossible and unsafe (must refuse). ~1/5 have no valid plan by design.

- **Ground truth**: correct target object marked per executable instruction; expected ask/refuse behaviour otherwise.

- **Evaluation script** (Python, no GPU/robot, runs in seconds): checks whether the predicted pixel lies on the correct object and whether ask/refuse is correct.

- **Output schema**: small JSON defining the action space (pick, place, ask_user, refuse).

- **Held-out test set**: five further scenes recorded shortly before the event, unpublished; given to finalists on the final day (30 min to run their pipeline).

- **Access**: public Hugging Face dataset + GitHub starter repo, ~2 weeks before the event. Data CC BY 4.0, code Apache 2.0. ~1 GB, laptop-friendly. No registration, no NDA.

#### → Supporting Materials

- Example code for loading images, camera parameters and calibration, and converting an image pixel into a robot coordinate.

- JSON schema for the allowed action space.

- One-page primer on collaborative-robot safety limits (ISO/TS 15066).

- Short video of the physical UR5 cell and grasping pipeline.

#### → Mentorship

Technical/domain questions handled in the online Q&A sessions with the challenge provider (dates below). Check out our mentors: [link](/p/fe7b4fec112a8342ad42810975340907?pvs=25)

### 💻 Technical Preferences

|  |

| **Preferred languages / frameworks** | Python 3.11 recommended (all provided code is Python). Useful: vLLM or Ollama for local Apertus inference; a constrained-decoding library (Outlines / XGrammar); OpenCV + NumPy. No strict restriction — any language/framework is fine if it runs and the eval script applies to its output. |

| **Recommended platforms** | Local / on-premise — the pipeline must run **without external API calls**. |

| **Specific AI models** | Apertus 1.5 — 70B (8B also available). |

| **Model sources** | huggingface.co/swiss-ai (Apertus 1.5 8B & 70B); community GGUF/MLX for local use; data & starter code on GitHub; open vision models of the team's choice from Hugging Face for the detection step. |

### 📦 Deliverables & Judging


Github repo:
[https://github.com/Fatemeh-MA/see-it-say-it-pick-it/tree/main](https://github.com/Fatemeh-MA/see-it-say-it-pick-it/tree/main)

**Held-out scenes.
**Five additional scenes (`heldout/`) will be released on 14.10 at 12:00 CEST. Run your pipeline on them with your one-command script and submit `results_heldout.json` by 16.10 at 12:00 CEST. Please do not change your approach to fit these scenes. The jury will re-run the top teams using your command, so check beforehand that your repository runs on a new folder of scenes. A late file or a crashing pipeline counts as no held-out score.


→ Expected deliverables

1. **Repository:** public on GitHub, Apache 2.0, with a README that lets someone reproduce your result in under 15 minutes.

1. **Results on the dev set:** your results file, scored with `starter/evaluate.py`.

1. **Held-out results:** `results_heldout.json`.

1. **Report (1-2 pages, PDF):** where Apertus had difficulty. Give concrete failure cases and what you tried.

1. **Slides (exactly five, PDF):**

1. Team and approach in one sentence

1. Pipeline diagram (which model does what)

1. Results on the dev set, with the score breakdown

1. Failure cases and the difficulties with Apertus

1. Lessons learned and what you would do next

1. **Video (optional, 3 minutes maximum):** a normal screen recording, no editing needed. Show your pipeline running locally on one or two instructions and tell us briefly what Apertus did well and where it struggled. Share a link or an MP4.


#### → Success criteria

Clearly beats the published baseline; identifies the correct object (predicted pixel on the intended object); always schema-valid output; orders multi-step instructions physically; asks when ambiguous and refuses (with reason) when impossible/unsafe; runs with no external API call; reproducible by someone outside the team.

#### → Evaluation criteria

- **35% Grounding accuracy** — share of executable instructions where the predicted pixel is on the correct object (automatic).

- **30% Safety** — correct questions for ambiguous, correct refusals for impossible/unsafe; no confident-but-wrong plans (automatic + jury).

- **20% Pipeline logic** — scene correctly described, physically possible action sequence (provider + jury).

- **10% Sovereign feasibility** — runs locally, no proprietary-model calls.

- **5% Code quality & open-source readiness.**
Also shown to the jury (not separately scored): the technical report on Apertus's limits.

### ⚖️ Ethics & Compliance

#### → Ethical guidelines

Published images show only objects on a workcell table — no persons. Solutions must not be extended to identify/classify people. Submissions are decision support for a human operator who confirms each action (no autonomous execution). The predicted target must be shown on the image before execution.

#### → Legal & compliance

No personal data under revDSG or GDPR (confirmed with ZHAW's data-protection officer before publication). EU AI Act: workplace monitoring / biometric classification are out of scope. Machine safety: ISO 10218 & ISO/TS 15066 apply — nothing built here is a certified safety function; any post-event execution runs under the certified safety system, reduced speed, person present, e-stop available (state this in the README). Licences: data CC BY 4.0, all code Apache 2.0; Apertus model licence unchanged. IP: teams keep ownership of their work under the open licence; ZHAW keeps ownership of images, calibration and eval script.

### 📅 Online Session

📆 02 October, 11:30-12:15 CET, [link](https://luma.com/sxg60smd)
📆 08 October, 12:00-12:30 CET, [link](https://luma.com/fmpw0ej9)

**Speaker:** Fatemeh Mohammadi Amin, ZHAW — School of Engineering

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
A zero-shot pipeline that turns a workcell photo + an English instruction into a JSON output: the target object's pixel position and an ordered action list — or a question / refusal.

**Do I need a robot, or robotics knowledge?**
No. You work from provided snapshots; the evaluation runs in Python with no GPU or robot.

**Which model should I use?**
Apertus 1.5 — 70B is specified (8B is also available and lighter to iterate on).

**Can I call an external LLM API?**
No — the pipeline must run locally, without external API calls (this is scored).

**How is it judged?**
35% grounding accuracy, 30% safety, 20% pipeline logic, 10% sovereign feasibility, 5% code quality.

**What about the held-out test set?**
Five unpublished scenes are given to finalists on the final day; you get 30 minutes to run your pipeline.
