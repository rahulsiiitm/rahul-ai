from models.schemas import Message
from services.knowledge import experience_data, projects_data


def _latest_user_text(messages: list[Message]) -> str:
    for message in reversed(messages):
        if message.role != "user":
            continue
        if message.content:
            return message.content.strip().lower()
        if message.parts:
            return "".join(
                str(part.get("text", ""))
                for part in message.parts
                if isinstance(part, dict)
            ).strip().lower()
    return ""


def build_local_fallback(messages: list[Message]) -> str:
    """Return a useful, factual response when every hosted model is unavailable."""
    text = _latest_user_text(messages)

    if any(phrase in text for phrase in ("who are you", "what are you", "your name")):
        return (
            "I'm Zero — the Chief's AI co-pilot inside this portfolio. "
            "I know his projects, experience, and technical stack. The external brain is "
            "temporarily rate-limited, but the local one still works."
        )

    if any(word in text for word in ("who is rahul", "who is the chief", "about rahul", "about the chief")):
        return (
            "▸ The Chief is a B.Tech CSE student at IIIT Manipur, graduating in 2027.\n"
            "▸ He's a full-stack and AI engineer focused on RAG, applied ML, and clean interfaces.\n"
            "▸ His flagship work includes SUTRA, VidChain, and Vyoma."
        )

    if any(word in text for word in ("project", "built", "work")):
        featured = projects_data[:3]
        if featured:
            lines = [
                f"▸ {project.get('title')} — {project.get('tagline')}"
                for project in featured
            ]
            return "A few of the Chief's builds:\n" + "\n".join(lines) + "\nSee the full set in `/archive`."

    if any(word in text for word in ("experience", "intern", "job")):
        if experience_data:
            entries = [
                f"▸ {item.get('role')} @ {item.get('company')} ({item.get('period')})"
                for item in experience_data[:3]
            ]
            return "The Chief's recent experience:\n" + "\n".join(entries)

    if any(word in text for word in ("skill", "stack", "technology", "technologies")):
        return (
            "The Chief works mainly with Python, JavaScript, React/Next.js, FastAPI, "
            "PyTorch, TensorFlow, Docker, Firebase, and vector-search/RAG systems."
        )

    if any(word in text for word in ("hi", "hello", "hey")):
        return "Hey. Zero here — the Chief's digital co-pilot. Systems are a little busy, but I'm still online."

    return (
        "The hosted AI providers are temporarily rate-limited, but I can still cover the "
        "Chief's projects, experience, skills, resume, and contact details. Try one of those topics."
    )
