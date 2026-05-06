"""
jarvis/profile/loader.py
Loads resume.json and user_profile.json from the data directory.
"""

from __future__ import annotations
import json
from pathlib import Path
from rich.console import Console
from jarvis.config import RESUME_PATH, PROFILE_PATH

console = Console()


def load_resume() -> dict:
    """Load the structured base resume from JSON."""
    return _load(RESUME_PATH, label="resume")


def load_profile() -> dict:
    """Load the user profile (skills, preferences, etc.)."""
    return _load(PROFILE_PATH, label="user profile")


def _load(path: Path, label: str) -> dict:
    if not path.exists():
        console.print(
            f"[bold red]❌ {label.capitalize()} file not found:[/bold red] {path}\n"
            f"[dim]Run [bold]python main.py setup[/bold] to create the template.[/dim]"
        )
        raise SystemExit(1)
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def resume_as_text(resume: dict) -> str:
    """Flatten resume JSON into a readable text block for LLM prompts."""
    lines = []
    lines.append(f"Name: {resume.get('name', '')}")
    lines.append(f"Summary: {resume.get('summary', '')}")

    skills = resume.get("skills", [])
    if skills:
        lines.append(f"Skills: {', '.join(skills)}")

    for exp in resume.get("experience", []):
        lines.append(
            f"\nExperience — {exp.get('role')} at {exp.get('company')} "
            f"({exp.get('duration', '')})"
        )
        for bullet in exp.get("bullets", []):
            lines.append(f"  • {bullet}")

    for proj in resume.get("projects", []):
        lines.append(f"\nProject — {proj.get('name')}: {proj.get('description')}")
        tech = proj.get("tech", [])
        if tech:
            lines.append(f"  Tech: {', '.join(tech)}")

    for edu in resume.get("education", []):
        lines.append(
            f"\nEducation — {edu.get('degree')} from {edu.get('institution')} "
            f"({edu.get('year', '')})"
        )

    return "\n".join(lines)
