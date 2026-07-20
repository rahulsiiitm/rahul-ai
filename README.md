<div align="center">
  <img src="assets/banner.png" alt="Rahul AI Hub Banner" width="100%" />
  
  <br />
  <h1>Rahul AI Hub</h1>
  <p><strong>A centralized monorepo for my autonomous AI agents, backends, and terminal interfaces.</strong></p>
  <br />
</div>

## 🌌 Overview

**Rahul AI Hub** is the central nervous system for all my AI-related projects. Instead of scattered repositories, this hub houses the core intelligence, specialized backends, and local testing environments for my AI agents (like **Zero**).

This architecture allows for seamless integration with external frontends (like my portfolio) while keeping the complex machine-learning, prompt engineering, and API integrations isolated and easily testable.

---

## 📂 Repository Structure

### `1. zero-backend/` (FastAPI)
The standalone production backend for **Zero**, my AI alter-ego deployed on my portfolio.
- **Tech Stack:** Python, FastAPI, Google Generative AI (Gemini), OpenAI SDK (xAI/Grok fallback).
- **Features:** 
  - Streams dynamic AI responses matching my exact personality and resume data.
  - Implements an IP-based rate limiter.
  - Auto-pings its own `keep-alive` endpoint to prevent Render free-tier spin-downs.

### `2. ZERO_Core/` (Terminal TUI)
A highly advanced terminal-based user interface (TUI) for local interactions and testing.
- **Tech Stack:** Python, Textual, Ollama.
- **Features:**
  - Three-panel UI layout.
  - Connects to local LLMs via Ollama for zero-latency, private inference.
  - Built-in dispatcher and job tracker.

---

## 🚀 Quick Start (Zero Backend)

To run the portfolio AI backend locally:

```bash
# 1. Navigate to the backend directory
cd zero-backend

# 2. Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run the FastAPI server
uvicorn main:app --host 0.0.0.0 --port 8000
```
*The API will be available at `http://localhost:8000/api/chat`*

---

## 🔐 Environment Variables
You will need an `.env` file in the `zero-backend/` directory with the following keys:
```env
GOOGLE_GENERATIVE_AI_API_KEY=your_gemini_key
GROQ_API_KEY=your_grok_key
```

---

<div align="center">
  <i>Built at the intersection of ML and clean Architecture by Rahul Sharma.</i>
</div>
