"""
Greenhouse ATS Scraper
-----------------------
Greenhouse has a public JSON API: no auth required.
Endpoint: https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true

Finding a company's slug: go to company's careers page powered by Greenhouse,
the URL contains the slug (e.g. jobs.lever.co/stripe → "stripe").
"""

import requests
import logging
from datetime import datetime
from typing import List, Dict

logger = logging.getLogger(__name__)

GREENHOUSE_COMPANIES = [
    # Finance & Research
    {"name": "Kroll",          "slug": "kroll"},
    {"name": "Lazard",         "slug": "lazard"},
    {"name": "Jefferies",      "slug": "jefferies"},
    {"name": "Macquarie",      "slug": "macquarie"},
    {"name": "Nomura",         "slug": "nomura"},
    # KPO / Research
    {"name": "Morningstar",    "slug": "morningstar"},
    {"name": "FactSet",        "slug": "factset"},
    {"name": "MSCI",           "slug": "msci"},
    {"name": "Dun & Bradstreet","slug": "dnb"},
    {"name": "Wood Mackenzie", "slug": "woodmac"},
    {"name": "IHS Markit",     "slug": "ihsmarkit"},
    # Tech
    {"name": "Stripe",         "slug": "stripe"},
    {"name": "Coinbase",       "slug": "coinbase"},
    {"name": "Notion",         "slug": "notion"},
    {"name": "Airtable",       "slug": "airtable"},
    {"name": "Figma",          "slug": "figma"},
    {"name": "Dropbox",        "slug": "dropbox"},
    {"name": "Robinhood",      "slug": "robinhood"},
    {"name": "Plaid",          "slug": "plaid"},
    {"name": "Brex",           "slug": "brex"},
]

BASE_URL = "https://boards-api.greenhouse.io/v1/boards/{slug}/jobs"
HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json",
}


def parse_job(raw: Dict, company_name: str) -> Dict:
    """Normalise a Greenhouse job object."""
    # Location
    location_obj = raw.get("location", {})
    location = location_obj.get("name", "") if isinstance(location_obj, dict) else str(location_obj)

    # Posted date
    updated_at = raw.get("updated_at", "")
    try:
        posted_date = datetime.fromisoformat(updated_at.replace("Z", "+00:00")).date().isoformat()
    except (ValueError, TypeError):
        posted_date = None

    # Description snippet (strip HTML)
    description = raw.get("content", "") or ""
    import re
    description = re.sub(r"<[^>]+>", " ", description)[:500].strip()

    return {
        "job_title":          raw.get("title", "").strip(),
        "company":            company_name,
        "location":           location,
        "salary_range":       None,
        "job_url":            raw.get("absolute_url", ""),
        "description_snippet": description,
        "posted_date":        posted_date,
        "source":             "greenhouse",
        "source_job_id":      str(raw.get("id", "")),
        "job_type":           "full_time",
        "seniority":          None,
    }


def is_relevant(job: Dict, profile: Dict) -> bool:
    """Quick keyword match before full filtering."""
    title_lower = job["job_title"].lower()
    roles = [r.lower() for r in profile.get("target_roles", [])]
    if not roles:
        return True
    return any(keyword in title_lower for role in roles for keyword in role.split())


def scrape_company(company: Dict, profile: Dict) -> List[Dict]:
    url = BASE_URL.format(slug=company["slug"])
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15, params={"content": "true"})
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException as e:
        logger.warning(f"[Greenhouse] {company['name']} ({company['slug']}) failed: {e}")
        return []

    raw_jobs = data.get("jobs", [])
    jobs = [parse_job(j, company["name"]) for j in raw_jobs]
    relevant = [j for j in jobs if is_relevant(j, profile)]

    logger.info(f"[Greenhouse] {company['name']}: {len(relevant)}/{len(jobs)} relevant jobs")
    return relevant


def scrape(profile: Dict) -> List[Dict]:
    all_jobs: List[Dict] = []
    target_companies = profile.get("target_companies", [])
    exclude = profile.get("exclude_companies", [])

    for company in GREENHOUSE_COMPANIES:
        if target_companies and company["name"] not in target_companies:
            continue
        if company["name"] in exclude:
            continue
        try:
            jobs = scrape_company(company, profile)
            all_jobs.extend(jobs)
        except Exception as e:
            logger.error(f"[Greenhouse] Unexpected error for {company['name']}: {e}")

    return all_jobs
