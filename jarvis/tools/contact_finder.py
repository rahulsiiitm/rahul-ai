"""
jarvis/tools/contact_finder.py
Finds founder/CEO contact info for a company via web search.
Returns name, role, LinkedIn, and guessed email patterns.
"""
from __future__ import annotations
import re
import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}
TIMEOUT = 8


def _ddg_search(query: str) -> str:
    """DuckDuckGo HTML search — returns page text."""
    try:
        r = requests.get(
            "https://html.duckduckgo.com/html/",
            params={"q": query},
            headers=HEADERS,
            timeout=TIMEOUT,
        )
        soup = BeautifulSoup(r.text, "lxml")
        results = []
        for a in soup.select(".result__title a")[:5]:
            results.append(a.get_text(strip=True))
        for snippet in soup.select(".result__snippet")[:5]:
            results.append(snippet.get_text(strip=True))
        return " | ".join(results)
    except Exception:
        return ""


def _guess_emails(domain: str, name: str) -> list[str]:
    """Generate common email patterns from a person's name + domain."""
    parts = name.lower().split()
    if len(parts) < 2:
        return [f"{parts[0]}@{domain}"] if parts else []
    first, last = parts[0], parts[-1]
    return [
        f"{first}@{domain}",
        f"{first}.{last}@{domain}",
        f"{first[0]}{last}@{domain}",
        f"hello@{domain}",
        f"contact@{domain}",
    ]


def _extract_domain(company: str) -> str:
    """Guess company domain from name."""
    slug = re.sub(r"[^a-z0-9]", "", company.lower())
    return f"{slug}.com"


def find_contact(company: str, role: str = "CEO") -> dict:
    """
    Search for a company's founder/CEO contact.
    Returns: name, role, linkedin, email_guesses, domain
    """
    query = f"{company} {role} founder site:linkedin.com"
    text  = _ddg_search(query)

    # Also search for email directly
    query2 = f"{company} {role} email contact"
    text2  = _ddg_search(query2)
    combined = text + " " + text2

    # Try extracting emails from search results
    found_emails = re.findall(r"[\w.+-]+@[\w-]+\.[a-zA-Z]{2,}", combined)
    found_emails = [e for e in found_emails if "example" not in e][:3]

    # Try to extract a person name from results
    name_match = re.search(
        r"([A-Z][a-z]+ [A-Z][a-z]+)(?:,?\s*(?:CEO|Founder|CTO|Co-Founder))",
        combined,
    )
    name = name_match.group(1) if name_match else "Unknown"

    # LinkedIn URL
    li_match = re.search(r"linkedin\.com/in/([\w-]+)", combined)
    linkedin = f"https://linkedin.com/in/{li_match.group(1)}" if li_match else "Not found"

    domain = _extract_domain(company)
    guessed = _guess_emails(domain, name) if name != "Unknown" else [f"hello@{domain}", f"contact@{domain}"]

    return {
        "company": company,
        "role": role,
        "name": name,
        "linkedin": linkedin,
        "domain": domain,
        "found_emails": found_emails,
        "guessed_emails": guessed,
        "note": "Verify before sending — these are best guesses based on web search.",
    }
