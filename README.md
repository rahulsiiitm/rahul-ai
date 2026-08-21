<div align="center">
  <img src="assets/banner.png" alt="Rahul AI Banner" width="100%" />
  
  <br />
  <h1>Rahul AI Hub</h1>
  <p><strong>The backend code and terminal interface for my personal AI chatbots and agents projects.</strong></p>
  
  <p>
    <img src="https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python" />
    <img src="https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white" alt="FastAPI" />
    <img src="https://img.shields.io/badge/Groq-F55036?style=for-the-badge" alt="Groq" />
    <img src="https://img.shields.io/badge/OpenRouter-6467F2?style=for-the-badge" alt="OpenRouter" />
    <img src="https://img.shields.io/badge/License-Proprietary-red?style=for-the-badge" alt="License" />
  </p>
  <br />
</div>

## Overview

This repository holds the code for my personal AI tools. I built this to keep my AI backend logic in one place instead of scattering it across different repos. Right now, it powers **Zero** (the chatbot you can talk to on my portfolio) and includes a local terminal UI I use for testing.

---

## What's Inside

### `1. zero-backend/`
This is a FastAPI backend that runs the **Zero** chatbot on my portfolio website. 
- It uses Groq first, OpenRouter second, and a deterministic portfolio-data fallback if both hosted providers are unavailable.
- Streams responses in real-time.
- Uses authenticated chat sessions, distributed rate limiting, bounded provider timing, and optional Supabase telemetry.

### `2. ZERO_Core/`
A local terminal UI (TUI) I use for testing models and scripts without needing a web browser.
- Built with Python and Textual.
- Connects directly to local models running via Ollama.

---

## Running the Backend Locally

If you want to spin up the backend API on your own machine:

```bash
# Move into the backend folder
cd zero-backend

# Setup a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install the required packages
pip install -r requirements-dev.txt

# Start the API server
uvicorn main:app --host 0.0.0.0 --port 8000
```

The API will be live at `http://localhost:8000/api/chat`.

---

## Environment Variables
To run the backend, create a `.env` file in the `zero-backend/` folder with your API keys:
```env
GROQ_API_KEY=your_groq_key
OPENROUTER_API_KEY=your_openrouter_key
CHAT_SESSION_SECRET=a_random_secret_with_at_least_32_characters
UPSTASH_REDIS_REST_URL=your_upstash_url
UPSTASH_REDIS_REST_TOKEN=your_upstash_token
```

---

## License

This project is proprietary. All rights reserved. See the [LICENSE](LICENSE) file for more information.
