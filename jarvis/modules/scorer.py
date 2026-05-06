"""
jarvis/modules/scorer.py
Module 2: Job Scoring Engine

Evaluates a job description against the user's resume/skills and returns:
  - score (0–100)
  - matched_skills
  - missing_skills
  - verdict (Strong Match / Moderate Match / Weak Match)
  - tip (brief advice)
"""

from __future__ import annotations
from jarvis import llm
from jarvis.config import SCORE_THRESHOLD_HIGH, SCORE_THRESHOLD_MED
from jarvis.profile.loader import load_resume, load_profile, resume_as_text

SYSTEM_PROMPT = """You are a precise job relevance evaluator.
When given a job description and a candidate's resume, you MUST respond with ONLY valid JSON.
No explanation. No markdown. Just raw JSON."""

PROMPT_TEMPLATE = """\
Evaluate how well the candidate's profile matches this job.

=== CANDIDATE PROFILE ===
{resume_text}

=== JOB DESCRIPTION ===
Title: {job_title}
Company: {company}
Description:
{job_description}

Return ONLY this JSON (no extra text):
{{
  "score": <integer 0-100>,
  "matched_skills": [<list of matching skills>],
  "missing_skills": [<list of important skills the candidate lacks>],
  "verdict": "<one of: Strong Match | Moderate Match | Weak Match>",
  "tip": "<one actionable sentence to improve chances>"
}}
"""


def score_job(
    job_title: str,
    company: str,
    job_description: str,
) -> dict:
    """
    Score a job description against the loaded user profile.
    Returns a dict with score, verdict, skills analysis, and tip.
    """
    resume = load_resume()
    resume_text = resume_as_text(resume)

    prompt = PROMPT_TEMPLATE.format(
        resume_text=resume_text,
        job_title=job_title,
        company=company,
        job_description=job_description,
    )

    result = llm.generate_json(prompt=prompt, system=SYSTEM_PROMPT)

    # Normalize verdict based on score if LLM didn't set it correctly
    score = result.get("score", 0)
    if isinstance(score, int):
        if score >= SCORE_THRESHOLD_HIGH:
            result["verdict"] = "Strong Match"
        elif score >= SCORE_THRESHOLD_MED:
            result["verdict"] = "Moderate Match"
        else:
            result["verdict"] = "Weak Match"

    return result
