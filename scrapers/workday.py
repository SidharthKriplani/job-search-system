"""
Workday ATS Scraper
-------------------
Calls the Workday JSON API (no HTML scraping — stable endpoint).
Each company has a unique subdomain and job family ID.

Adding a new company:
    1. Go to their careers page (company.wd5.myworkdayjobs.com)
    2. Open DevTools → Network → filter "jobs"
    3. Find the API call and copy the subdomain + job family path
"""

import requests
import logging
from datetime import datetime, date
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

# -------------------------------------------------------------------
# Company registry — extend this list freely
# Format: (display_name, workday_subdomain, api_path, job_family_ids)
# job_family_ids: None = all families, else filter by these IDs
# -------------------------------------------------------------------
WORKDAY_COMPANIES = [
    # Finance / IB / KPO
    {"name": "HSBC",              "subdomain": "hsbc",              "path": "HSBC",              "families": None},
    {"name": "Goldman Sachs",     "subdomain": "goldmansachs",      "path": "gs",                "families": None},
    {"name": "JP Morgan",         "subdomain": "jpmc",              "path": "jpmc",              "families": None},
    {"name": "Morgan Stanley",    "subdomain": "morganstanley",     "path": "External",          "families": None},
    {"name": "Citi",              "subdomain": "citi",              "path": "Citi",              "families": None},
    {"name": "Deutsche Bank",     "subdomain": "db",                "path": "deutschebank",      "families": None},
    {"name": "Standard Chartered","subdomain": "standardchartered", "path": "scb",               "families": None},
    {"name": "BNP Paribas",       "subdomain": "bnpparibasgroup",   "path": "bnpparibas",        "families": None},
    {"name": "Barclays",          "subdomain": "barclays",          "path": "barclays",          "families": None},
    {"name": "UBS",               "subdomain": "ubs",               "path": "ubs",               "families": None},
    # Consulting / Big 4
    {"name": "Deloitte",          "subdomain": "deloitte",          "path": "Deloitte",          "families": None},
    {"name": "EY",                "subdomain": "ey",                "path": "ey",                "families": None},
    {"name": "KPMG",              "subdomain": "kpmg",              "path": "kpmg",              "families": None},
    {"name": "PwC",               "subdomain": "pwc",               "path": "pwc",               "families": None},
    # Research / Rating agencies
    {"name": "S&P Global",        "subdomain": "spgi",              "path": "Global",            "families": None},
    {"name": "Moody's",           "subdomain": "moodys",            "path": "External",          "families": None},
    {"name": "Fitch",             "subdomain": "fitchgroup",        "path": "FitchGroup",        "families": None},
    # KPOs
    {"name": "Genpact",           "subdomain": "genpact",           "path": "genpact",           "families": None},
    {"name": "WNS",               "subdomain": "wns",               "path": "wns",               "families": None},
    {"name": "EXL",               "subdomain": "exlservice",        "path": "exl",               "families": None},
    {"name": "Evalueserve",       "subdomain": "evalueserve",       "path": "evalueserve",       "families": None},
    {"name": "Accenture",         "subdomain": "accenture",         "path": "AccentureCareers",  "families": None},
    # Tech (for GenAI/ML roles)
    {"name": "Microsoft",         "subdomain": "microsoft",         "path": "External",          "families": None},
    {"name": "Amazon",            "subdomain": "amazon",            "path": "External",          "families": None},
]

BASE_URL = "https://{subdomain}.wd5.myworkdayjobs.com/wday/cxs/{subdomain}/{path}/jobs"

HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json",
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
}


def build_payload(search_terms: List[str], locations: List[str], offset: int = 0) -> Dict:
    """Build Workday API request payload."""
    location_filters = []
    for loc in locations:
        if loc.lower() not in ("remote", "wfh"):
            location_filters.append({
                "descriptor": loc,
                "id": "",
                "type": "location"
            })

    return {
        "appliedFacets": {
            "locationCountry": [],
            "locationCity": location_filters,
        },
        "limit": 20,
        "offset": offset,
        "searchText": " OR ".join(search_terms),
    }


def parse_job(raw: Dict, company: str, source_url: str) -> Dict:
    """Normalise a Workday job object to our schema."""
    posted_raw = raw.get("postedOn", "")
    try:
        posted_date = datetime.strptime(posted_raw, "%B %d, %Y").date().isoformat()
    except (ValueError, TypeError):
        posted_date = date.today().isoformat()

    location_parts = [
        loc.get("descriptor", "") for loc in raw.get("locationsText", [])
    ]
    location = ", ".join(filter(None, location_parts)) or "Unknown"

    return {
        "job_title":          raw.get("title", "").strip(),
        "company":            company,
        "location":           location,
        "salary_range":       None,
        "job_url":            f"{source_url}/{raw.get('externalPath', '')}",
        "description_snippet": raw.get("jobDescription", {}).get("descriptor", "")[:500],
        "posted_date":        posted_date,
        "source":             "workday",
        "source_job_id":      raw.get("bulletFields", [None])[0] or raw.get("externalPath", ""),
        "job_type":           "full_time",
        "seniority":          None,
    }


def scrape_company(company: Dict, profile: Dict) -> List[Dict]:
    """Scrape all matching jobs for one Workday company."""
    subdomain = company["subdomain"]
    path      = company["path"]
    url       = BASE_URL.format(subdomain=subdomain, path=path)
    base_site = f"https://{subdomain}.wd5.myworkdayjobs.com/en-US/{path}"

    jobs: List[Dict] = []
    offset = 0
    max_pages = 5  # safety cap

    search_terms = profile.get("target_roles", ["research manager"])
    locations    = profile.get("locations", ["India"])

    for _ in range(max_pages):
        try:
            resp = requests.post(
                url,
                json=build_payload(search_terms, locations, offset),
                headers=HEADERS,
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()
        except requests.RequestException as e:
            logger.warning(f"[Workday] {company['name']} failed: {e}")
            break

        raw_jobs = data.get("jobPostings", [])
        if not raw_jobs:
            break

        for raw in raw_jobs:
            jobs.append(parse_job(raw, company["name"], base_site))

        total = data.get("total", 0)
        offset += len(raw_jobs)
        if offset >= total:
            break

    logger.info(f"[Workday] {company['name']}: {len(jobs)} jobs found")
    return jobs


def scrape(profile: Dict) -> List[Dict]:
    """
    Main entry point. profile is a user_profiles row.
    Returns list of normalised job dicts.
    """
    all_jobs: List[Dict] = []
    target_companies = profile.get("target_companies", [])  # [] = scrape all

    for company in WORKDAY_COMPANIES:
        if target_companies and company["name"] not in target_companies:
            continue
        if company["name"] in profile.get("exclude_companies", []):
            continue
        try:
            jobs = scrape_company(company, profile)
            all_jobs.extend(jobs)
        except Exception as e:
            logger.error(f"[Workday] Unexpected error for {company['name']}: {e}")

    return all_jobs
