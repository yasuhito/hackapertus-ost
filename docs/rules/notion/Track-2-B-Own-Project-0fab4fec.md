Source URL: https://hackapertus.notion.site/0fab4fec112a8308a8cb0170b95d38e5
Fetch date: 2026-10-12

# Track 2 B: Own Project

;lPz: 🟡🔴 Intermediate–Advanced

DBFd: Path A — Red-Teaming Apertus

E_=Z: University of Zurich - Department of Computational Linguistics

GSrM: **Apify**

NJQ:: [https://github.com/HackApertus](https://github.com/HackApertus)

^GB[: [View challenge →](https://notion.genaizurich.ch/gaz26-hackathon)

tHvE: 📆  **02 October, 12:30** CET, {{link}}
📆  **08 October, 12:00** CET, {{link}}

~|kM: [https://huggingface.co/HackApertus](https://huggingface.co/HackApertus)

Bring your own idea and build a working Apertus prototype that tackles a problem you care about — any domain, any use case. The project must be new, started within the hackathon period.

Submissions must use the Apertus model family. For Track 2 this means that submitted solutions must be built with Apertus. Other open-weights models can be used to support development, e.g. as automatic judges during evaluation. Their role must be clearly described in the submission report.

💬 In case you have questions, join the conversation on [Discord](https://discord.gg/hack-apertus) or send an email to “[hello@hackapertus.ch](mailto:hello@hackapertus.ch)”

---

### 🔧 Resources, Tools & Support

Check our resources & tools page for detailed information:
[https://hackapertus.notion.site/resources-tools](https://hackapertus.notion.site/resources-tools?source=copy_link)


---

### 💻 Technical Preferences

| Specific AI models | Apertus v1.5 — 8B or 70B |

| Model sources | [huggingface.co/swiss-ai/Apertus-v1.5-8B<br>](https://huggingface.co/swiss-ai/Apertus-v1.5-8B)[huggingface.co/swiss-ai/Apertus-v1.5-70B](https://huggingface.co/swiss-ai/Apertus-v1.5-70B) |

| Target architecture (mandatory) | Whatever you build in Track 2B must be deployable in one of these three architectures:<br><br>  a) On-premise — on the organisation's own infrastructure, under its own administration.<br>  b) Air-gapped — with no external network connection at runtime.<br>  c) Sovereign Swiss cloud — on a cloud platform operated in Switzerland, under Swiss jurisdiction, with Swiss data residency. |

---

#### 📦 Submissions & Deliverables

Submissions are not handled in Devpost.

Submit on our website only:
[http://hackapertus.ch/online-hack/submissions](http://hackapertus.ch/online-hack/submissions)


Github repo template:
[https://github.com/HackApertus/project-template](https://github.com/HackApertus/project-template/tree/main/track_2a)

The submission must:

1. follow the template repo and include all prerequisite files and definitions

1. follow the specified input/output formats

1. run in a Docker container, launched with `make run` from the root of the project

1. run end-to-end when judges try to run it

#### **Git repo (URL)**

- Create your repo from this template (**Use this template**) and work in the `track_2b/` challenge directory. Delete the other track challenge directories.

- Keep `track_2b/` as it is: don't rename it or move its files.

- Set the repo to PUBLIC (Settings --> Collaborators --> Manage Visibility)

- Submit the URL of YOUR Git repo.

#### **Technical Report (pdf)**

- Update [technical_report.md](https://github.com/HackApertus/project-template/blob/main/track_2b/technical_report.md) in this repository with all the details for your submission.

- Upload a pdf of your technical report to this directory, named as `TeamName_Report.pdf`.

- Format: pdf, max. 6 pages

- Submit the pdf of the technical report.

#### **Demo video (URL)**

- Max. 2 min demo video of your prototype

#### **
Dataset (URL), ***optional, depending on the project*

Submitted datasets must comply with our guidelines for responsibly sourced datasets.

- Create a user account on Hugging Face

- Clone our dataset template on Hugging Face:
[https://huggingface.co/datasets/HackApertus/online_hack_template](https://huggingface.co/datasets/HackApertus/online_hack_template)

- Complete the dataset card with all required information

- Upload your dataset. It should consist of the following components:

- evaluation dataset (i.e. individual test cases)

- model response dataset (i.e. the model response to each test case)

- metadata file (i.e. additional information about each test case; where relevant, this file must contain instance-level licensing information)

- Make sure your dataset access control is set to PUBLIC

- Submit the URL of *your* data set

---

### ⚖️ Judging Criteria

##### **1. Purposeful use of AI
2. Technical rigour
3. Value, cost & scalability
4. Sovereign deployability
5. Implementation feasibility**


Judges use a Scale 0–5 per dimension.


---

### **Support**

**Licensing requirements** Please check our Terms & Conditions (6. What you build is open source): [https://hackapertus.ch/terms-and-conditions](https://hackapertus.ch/terms-and-conditions)

### **FAQ**

💡 [https://hackapertus.ch/faq](https://hackapertus.ch/faq)

### **Contact**

💬 In case you have questions, join the conversation on Discord or send an email to “[hello@hackapertus.ch](mailto:hello@hackapertus.ch)”
