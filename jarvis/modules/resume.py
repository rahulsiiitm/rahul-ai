"""
jarvis/modules/resume.py
Module 3: Resume Customizer

Given a base resume + job description, generates:
  - A tailored professional summary (2–3 sentences)
  - 3–5 bullet points optimized for the specific role
  - A list of keywords to add to the resume
"""

from __future__ import annotations
from jarvis import llm
from jarvis.profile.loader import load_resume, resume_as_text

SYSTEM_PROMPT = """You are a professional resume writer with expertise in ATS optimization.
Your output must be in clean Markdown. Be specific, use action verbs, and quantify where possible."""

PROMPT_TEMPLATE = """\
Customize my resume content for the job below. Focus on relevance and ATS keywords.

=== MY CURRENT RESUME ===
{resume_text}

=== TARGET JOB ===
Role: {job_title}
Company: {company}
Description:
{job_description}

Provide the following in Markdown:

## Tailored Summary
<2–3 sentence professional summary targeting this specific role>

## Key Bullet Points
<5 strong, ATS-friendly achievement bullets from my background that are most relevant to this job>

## Keywords to Include
<comma-separated list of important keywords/phrases from the JD I should add to my resume>

## Skills to Highlight
<comma-separated list of my skills most relevant to this role>
"""


def customize_resume(
    job_title: str,
    company: str,
    job_description: str,
) -> str:
    """
    Generate tailored resume content for a specific job.
    Returns Markdown-formatted content.
    """
    resume = load_resume()

    prompt = PROMPT_TEMPLATE.format(
        resume_text=resume_as_text(resume),
        job_title=job_title,
        company=company,
        job_description=job_description,
    )

    return llm.generate(prompt=prompt, system=SYSTEM_PROMPT, stream=True)
