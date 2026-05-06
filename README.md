# 🤖 Jarvis v1 — Private AI Job Assistant

> **"A local AI-powered job assistant that helps you apply smarter, faster, and privately — without relying on external APIs."**

![Python](https://img.shields.io/badge/Python-3.10+-blue)
![Ollama](https://img.shields.io/badge/LLM-Ollama%20%2B%20Mistral-orange)
![Privacy](https://img.shields.io/badge/Privacy-100%25%20Local-green)
![License](https://img.shields.io/badge/License-MIT-lightgrey)

---

## 🧠 What is Jarvis?

Jarvis is a **fully local, privacy-first AI assistant** for job applications. It runs entirely on your machine using **Ollama + Mistral** — no external APIs, no cloud, no data leaks.

**It helps you:**
- 📊 Score job descriptions against your profile (0–100 with skill analysis)
- 📧 Generate tailored application emails in seconds
- 📄 Customize resume content with ATS-optimized keywords
- 🗃️ Track all your past applications in a local SQLite database

---

## ⚡ Quick Start

### 1. Prerequisites

```bash
# Install Ollama from https://ollama.com
ollama pull mistral
ollama serve
```

### 2. Install Dependencies

```bash
cd rahul-ai
pip install -r requirements.txt
```

### 3. Fill in Your Data

Edit `data/resume.json` with your actual resume.
Edit `data/user_profile.json` with your skills, target roles, and preferences.

### 4. Setup & Verify

```bash
python main.py setup
```

---

## 🖥️ CLI Commands

| Command | Description |
|---|---|
| `python main.py setup` | First-time setup, verify Ollama, init DB |
| `python main.py score_job` | Score a job + optionally generate email/resume |
| `python main.py generate_email` | Generate a tailored application email |
| `python main.py customize_resume` | Generate tailored resume content |
| `python main.py show_history` | View all past jobs and generated outputs |

---

## 🔄 Workflow

```
1. python main.py score_job
2. Paste job title, company, and description
3. Jarvis scores it → shows matched/missing skills + verdict
4. If score ≥ 45 → prompts to generate email and/or resume
5. Outputs saved locally to outputs/ and jarvis.db
6. You review, edit, and manually apply
```

---

## 📁 Project Structure

```
rahul-ai/
├── jarvis/
│   ├── config.py          # Paths, model settings, constants
│   ├── db.py              # SQLite persistence layer
│   ├── llm.py             # Ollama/Mistral wrapper
│   ├── modules/
│   │   ├── scorer.py      # Job scoring engine
│   │   ├── emailer.py     # Email generator
│   │   └── resume.py      # Resume customizer
│   └── profile/
│       └── loader.py      # Resume + profile JSON loaders
├── data/
│   ├── resume.json        # Your structured resume (edit this!)
│   ├── user_profile.json  # Your profile & preferences (edit this!)
│   └── jarvis.db          # Auto-created SQLite database
├── outputs/               # Auto-generated emails and resume snippets
├── main.py                # CLI entry point
└── requirements.txt
```

---

## ⚙️ Configuration

| Env Var | Default | Description |
|---|---|---|
| `JARVIS_MODEL` | `mistral` | Ollama model to use |
| `OLLAMA_HOST` | `http://localhost:11434` | Ollama server URL |

Override in a `.env` file or set in your shell.

---

## 🔒 Privacy Design

- ✅ Zero network calls after initial model download
- ✅ All data stored in `data/` and `outputs/` — local only
- ✅ `.gitignore` excludes all personal data and DB from Git
- ✅ No telemetry, analytics, or cloud sync of any kind

---

## 🖥️ Hardware Requirements

| Component | Minimum | Recommended |
|---|---|---|
| GPU VRAM | 4GB (RTX 3050) | 8GB+ |
| RAM | 8GB | 16GB |
| Storage | 5GB (for Mistral Q4) | 10GB |

Mistral 7B Q4_K_M runs comfortably on a 4GB VRAM GPU.

---

## 📈 Roadmap

- [x] Job scoring engine
- [x] Email generator
- [x] Resume customizer
- [x] SQLite history tracking
- [ ] Web dashboard (Flask/Streamlit)
- [ ] Job scraping (LinkedIn, Internshala)
- [ ] Application tracking system (status, follow-ups)
- [ ] Follow-up email generator
- [ ] Multi-model support (Llama 3, Phi-3)

---

## 🧠 Philosophy

> AI assists the user, not replaces them.

Human stays in control. AI handles repetitive cognitive work. Focus on quality over quantity — no mass-apply spam.

---

*Built with ❤️ by Rahul Sharma · Runs 100% locally*
