"""
Lever ATS Scraper
-----------------
Lever has a public JSON API:
  GET https://api.lever.co/v0/postings/{company}?mode=json
No auth required. Returns all postings.
"""

import requests
import logging
from typing import List, Dict

logger = logging.getLogger(__name__)

LEVER_COMPANIES = [
    # Finance / Research
    {"name": "Andreessen Horowitz", "slug": "a16z"},
    {"name": "Sequoia Capital",     "slug": "sequoia"},
    {"name": "Accel",               "slug": "accel"},
    {"name": "Tiger Global",        "slug": "tigerglobal"},
    # KPO / Analytics
    {"name": "ZS Associates",       "slug": "zs"},
    {"name": "Decision Point",      "slug": "decisionpoint"},
    # Tech / AI
    {"name": "Scale AI",            "slug": "scaleai"},
    {"name": "Weights & Biases",    "slug": "wandb"},
    {"name": "Hugging Face",        "slug": "huggingface"},
    {"name": "Cohere",              "slug": "cohere"},
    {"name": "Perplexity",          "slug": "perplexityai"},
    {"name": "Mistral AI",          "slug": "mistral"},
    {"name": "Anthropic",           "slug": "anthropic"},
    {"name": "OpenAI",              "slug": "openai"},
    {"name": "Pika Labs",           "slug": "pikalabs"},
    {"name": "Canva",               "slug": "canva"},
    {"name": "Atlassian",           "slug": "atlassian"},
    {"name": "Twilio",              "slug": "twilio"},
]

BASE_URL = "https://api.lever.co/v0/postings/{slug}"
HEADERS = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}


def parse_job(raw: Dict, company_name: str) -> Dict:
    """Normalise a Lever posting."""
    categories = raw.get("categories", {})
    location = categories.get("location") or categories.get("city") or categories.get("country") or ""

    # Salary from text (not always present)
    salary_range = None
    for item in raw.get("lists", []):
        if "compensation" in item.get("text", "").lower() or "salary" in item.get("text", "").lower():
            salary_range = item.get("content", "")[:100]
            break

    return {
        "job_title":          raw.get("text", "").strip(),
        "company":            company_name,
        "location":           location,
        "salary_range":       salary_range,
        "job_url":            raw.get("hostedUrl") or raw.get("applyUrl", ""),
        "description_snippet": (raw.get("descriptionPlain") or "")[:500],
        "posted_date":        None,  # Lever doesn't expose postDate reliably
        "source":             "lever",
        "source_job_id":      raw.get("id", ""),
        "job_type":           "full_time",
        "seniority":          categories.get("commitment"),
    }


def is_relevant(job: Dict, profile: Dict) -> bool:
    title_lower = job["job_title"].lower()
    roles = [r.lower() for r in profile.get("target_roles", [])]
    if not roles:
        return True
    return any(keyword in title_lower for role in roles for keyword in role.split())


def scrape_company(company: Dict, profile: Dict) -> List[Dict]:
    url = BASE_URL.format(slug=company["slug"])
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15, params={"mode": "json"})
        resp.raise_for_status()
        raw_jobs = resp.json()
    except requests.RequestException as e:
        logger.warning(f"[Lever] {company['name']} ({company['slug']}) failed: {e}")
        return []

    if not isinstance(raw_jobs, list):
        raw_jobs = []

    jobs = [parse_job(j, company["name"]) for j in raw_jobs]
    relevant = [j for j in jobs if is_relevant(j, profile)]

    logger.info(f"[Lever] {company['name']}: {len(relevant)}/{len(jobs)} relevant jobs")
    return relevant


def scrape(profile: Dict) -> List[Dict]:
    all_jobs: List[Dict] = []
    target_companies = profile.get("target_companies", [])
    exclude = profile.get("exclude_companies", [])

    for company in LEVER_COMPANIES:
        if target_companies and company["name"] not in target_companies:
            continue
        if company["name"] in exclude:
            continue
        try:
            jobs = scrape_company(company, profile)
            all_jobs.extend(jobs)
        except Exception as e:
            logger.error(f"[Lever] Unexpected error for {company['name']}: {e}")

    return all_jobs
