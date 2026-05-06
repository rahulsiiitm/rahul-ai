"""
jarvis/tools/job_scraper.py
Scrapes job listings from Internshala, Y Combinator, and Wellfound.
Uses requests + BeautifulSoup. No login required.
"""
from __future__ import annotations
import time
import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}
TIMEOUT = 10


def _get(url: str) -> BeautifulSoup | None:
    try:
        r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        r.raise_for_status()
        return BeautifulSoup(r.text, "lxml")
    except Exception as e:
        print(f"[scraper] GET failed: {url} — {e}")
        return None


# ── Internshala ────────────────────────────────────────────────────────────────

def scrape_internshala(query: str, count: int = 10) -> list[dict]:
    slug = query.lower().strip().replace(" ", "-")
    url = f"https://internshala.com/internships/{slug}-internship/"
    soup = _get(url)
    if not soup:
        # fallback: general search
        url = f"https://internshala.com/internships/keywords-{slug}/"
        soup = _get(url)
    if not soup:
        return [{"error": "Could not reach Internshala. Try again later."}]

    results = []
    cards = soup.select(".individual_internship")[:count]
    for card in cards:
        title_el  = card.select_one(".job-internship-name")
        company_el = card.select_one(".company-name")
        loc_el    = card.select_one(".location_link, .locations-strip")
        stip_el   = card.select_one(".stipend")
        dur_el    = card.select_one(".ic-16-calendar + span, .other-detail-item .item_body")
        link_el   = card.select_one("a.view_detail_button, a[href*='/internship/detail/']")

        title   = title_el.get_text(strip=True)   if title_el   else "N/A"
        company = company_el.get_text(strip=True)  if company_el else "N/A"
        loc     = loc_el.get_text(strip=True)      if loc_el     else "N/A"
        stip    = stip_el.get_text(strip=True)     if stip_el    else "N/A"
        link    = "https://internshala.com" + link_el["href"] if link_el else url

        results.append({
            "title": title, "company": company,
            "location": loc, "stipend": stip,
            "source": "Internshala", "link": link,
        })

    return results if results else [{"error": "No listings found on Internshala for that query."}]


# ── Y Combinator Jobs ──────────────────────────────────────────────────────────

def scrape_ycombinator(query: str, count: int = 10) -> list[dict]:
    soup = _get("https://news.ycombinator.com/jobs")
    if not soup:
        return [{"error": "Could not reach YC Jobs."}]

    results = []
    q = query.lower().strip()
    for row in soup.select("tr.athing"):
        title_el = row.select_one("td.title a")
        if not title_el:
            continue
        title = title_el.get_text(strip=True)
        # Only filter when a query was given
        if q and q not in title.lower():
            continue
        link = title_el.get("href", "")
        sub  = row.find_next_sibling("tr")
        meta = sub.get_text(" ", strip=True) if sub else ""
        results.append({
            "title": title, "company": "YC Company",
            "location": "Remote/Various", "stipend": "N/A",
            "source": "YCombinator", "link": link,
            "meta": meta[:120],
        })
        if len(results) >= count:
            break

    return results if results else [{"error": "No YC jobs matched that query."}]


# ── Wellfound (AngelList) ──────────────────────────────────────────────────────

def scrape_wellfound(query: str, count: int = 10) -> list[dict]:
    slug = query.lower().strip().replace(" ", "-")
    url = f"https://wellfound.com/role/l/{slug}"
    soup = _get(url)
    if not soup:
        return [{"error": "Could not reach Wellfound. It may require login for full results."}]

    results = []
    cards = soup.select("[class*='JobListing'], [data-test='JobListing']")[:count]
    for card in cards:
        title_el   = card.select_one("a[class*='title'], h2")
        company_el = card.select_one("[class*='company'], [class*='startup']")
        loc_el     = card.select_one("[class*='location']")
        link_el    = card.select_one("a[href*='/jobs/']")

        title   = title_el.get_text(strip=True)   if title_el   else "N/A"
        company = company_el.get_text(strip=True)  if company_el else "N/A"
        loc     = loc_el.get_text(strip=True)      if loc_el     else "Remote"
        link    = "https://wellfound.com" + link_el["href"] if link_el and link_el.get("href","").startswith("/") else (link_el["href"] if link_el else url)

        results.append({
            "title": title, "company": company,
            "location": loc, "stipend": "N/A",
            "source": "Wellfound", "link": link,
        })

    return results if results else [{"error": "No Wellfound listings found. Site may need login."}]


# ── Dispatcher ─────────────────────────────────────────────────────────────────

def scrape_jobs(query: str, site: str = "internshala", count: int = 10) -> list[dict]:
    site = site.lower().strip()
    time.sleep(0.5)  # polite delay
    if site == "internshala":
        return scrape_internshala(query, count)
    elif site in ("ycombinator", "yc"):
        return scrape_ycombinator(query, count)
    elif site in ("wellfound", "angellist"):
        return scrape_wellfound(query, count)
    else:
        # Try all three, merge
        results = []
        results += scrape_internshala(query, count // 2 or 5)
        results += scrape_ycombinator(query, count // 2 or 5)
        return results
