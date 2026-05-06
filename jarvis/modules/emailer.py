"""
jarvis/modules/emailer.py
Module 4: Email Generator

Generates a professional job application email tailored to:
  - The specific job description
  - The user's profile and strongest relevant skills
  - The requested tone (formal / semi-formal / friendly)
"""

from __future__ import annotations
from jarvis import llm
from jarvis.config import DEFAULT_TONE
from jarvis.profile.loader import load_resume, load_profile, resume_as_text

SYSTEM_PROMPT = """You are an expert career coach who writes outstanding job application emails.
Write emails that are concise, specific, and compelling — never generic.
Do NOT use placeholder text like [Your Name]. Use actual data from the profile provided."""

PROMPT_TEMPLATE = """\
Write a {tone} job application email for the role below.

=== MY PROFILE ===
{resume_text}

Additional context:
- Target roles: {target_roles}
- About me: {about_me}

=== JOB I'M APPLYING FOR ===
Role: {job_title}
Company: {company}
Job Description:
{job_description}

Instructions:
- Subject line first (prefix with "Subject: ")
- 3–4 short paragraphs maximum
- Open with a strong hook (not "I am writing to apply")
- Highlight 2–3 specific skills/projects relevant to THIS job
- Close with a clear call to action
- Tone: {tone}
- Do NOT use bullet points in the email body
"""


def generate_email(
    job_title: str,
    company: str,
    job_description: str,
    tone: str = DEFAULT_TONE,
) -> str:
    """
    Generate a tailored job application email.
    Returns the full email as a string (subject + body).
    """
    resume = load_resume()
    profile = load_profile()

    prompt = PROMPT_TEMPLATE.format(
        tone=tone,
        resume_text=resume_as_text(resume),
        target_roles=", ".join(profile.get("target_roles", [])),
        about_me=profile.get("about_me", ""),
        job_title=job_title,
        company=company,
        job_description=job_description,
    )

    return llm.generate(prompt=prompt, system=SYSTEM_PROMPT, stream=True)
