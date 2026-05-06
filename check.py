import sys
results = []

def chk(name, fn):
    try:
        detail = fn()
        results.append((name, "OK", detail or ""))
    except Exception as e:
        results.append((name, "FAIL", str(e)[:80]))

# Config
chk("jarvis.config", lambda: (
    __import__("jarvis.config", fromlist=["OLLAMA_MODEL"]),
    f"model={__import__('jarvis.config',fromlist=['OLLAMA_MODEL']).OLLAMA_MODEL}"
)[1])

# DB
chk("jarvis.db", lambda: (
    __import__("jarvis.db", fromlist=["init_db"]).init_db(), "DB OK"
)[1])

# LLM / Ollama
def chk_llm():
    from jarvis.llm import ping
    ok = ping()
    if not ok:
        results.append(("jarvis.llm (Ollama)", "WARN", "Mistral not reachable — run: ollama serve"))
        return None
    return "Mistral reachable"
chk("jarvis.llm (Ollama)", chk_llm)

# Profile
def chk_profile():
    from jarvis.profile.loader import load_resume, load_profile
    r = load_resume(); p = load_profile()
    return "name=" + r["name"]
chk("jarvis.profile", chk_profile)

# Agent
chk("jarvis.agent.planner",      lambda: (__import__("jarvis.agent.planner", fromlist=["AGENT_SYSTEM"]), "OK")[1])
chk("jarvis.agent.tools",        lambda: ("tools=" + str(list(__import__("jarvis.agent.tools", fromlist=["TOOLS"]).TOOLS.keys()))))
chk("jarvis.agent.server_agent", lambda: (__import__("jarvis.agent.server_agent", fromlist=["run_agent"]), "OK")[1])

# Tools
chk("jarvis.tools.job_scraper",    lambda: (__import__("jarvis.tools.job_scraper",    fromlist=["scrape_jobs"]),   "OK")[1])
chk("jarvis.tools.contact_finder", lambda: (__import__("jarvis.tools.contact_finder", fromlist=["find_contact"]), "OK")[1])
chk("jarvis.tools.email_reader",   lambda: (__import__("jarvis.tools.email_reader",   fromlist=["read_emails"]),  "OK")[1])
chk("jarvis.tools.email_sender",   lambda: (__import__("jarvis.tools.email_sender",   fromlist=["queue_draft"]),  "OK")[1])

# Modules
chk("jarvis.modules.scorer",  lambda: (__import__("jarvis.modules.scorer",  fromlist=["score_job"]),        "OK")[1])
chk("jarvis.modules.emailer", lambda: (__import__("jarvis.modules.emailer", fromlist=["generate_email"]),   "OK")[1])
chk("jarvis.modules.resume",  lambda: (__import__("jarvis.modules.resume",  fromlist=["customize_resume"]), "OK")[1])

# Voice
chk("jarvis.voice.stt", lambda: (__import__("jarvis.voice.stt", fromlist=["start_recording"]), "imports OK")[1])
chk("jarvis.voice.tts", lambda: (__import__("jarvis.voice.tts", fromlist=["speak"]), "imports OK")[1])

# UI
chk("jarvis.ui.hud", lambda: (__import__("jarvis.ui.hud", fromlist=["HudCanvas"]), "OK")[1])
chk("gui.py",        lambda: (__import__("gui"), "OK")[1])

# Report
print()
print("=" * 62)
print("  JARVIS SYSTEM CHECK")
print("=" * 62)
for name, status, detail in results:
    if status is None: continue
    icon = "[OK]  " if status == "OK" else "[WARN]" if status == "WARN" else "[FAIL]"
    print(f"  {icon}  {name:<33} {detail}")
print("=" * 62)
ok   = sum(1 for _,s,_ in results if s == "OK")
warn = sum(1 for _,s,_ in results if s == "WARN")
fail = sum(1 for _,s,_ in results if s == "FAIL")
print(f"  {ok} OK  |  {warn} WARN  |  {fail} FAIL")
print("=" * 62)
