"""
NaukriGulf Scraper
-------------------
naukrigulf.com — primary source for GCC (UAE, Qatar, Saudi, Kuwait) roles.
Uses their search API (JSON response, no auth).
"""

import requests
import logging
from typing import List, Dict
from datetime import date
import time

logger = logging.getLogger(__name__)

SEARCH_URL = "https://www.naukrigulf.com/njsearch/v2/nj_jobs"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Accept": "application/json",
    "Referer": "https://www.naukrigulf.com/",
    "clientid":   "d3app",
    "systemid":   "ng",
}

GCC_COUNTRIES = ["UAE", "Qatar", "Saudi Arabia", "Kuwait", "Bahrain", "Oman"]


def build_payload(profile: Dict, page: int = 1) -> Dict:
    roles = " ".join(profile.get("target_roles", ["research manager"]))
    locations = profile.get("locations", [])

    # Determine GCC locations from profile
    gcc_locs = [loc for loc in locations if any(c.lower() in loc.lower() for c in GCC_COUNTRIES)]
    if not gcc_locs:
        gcc_locs = ["UAE"]  # default to UAE if no GCC location specified

    return {
        "searchType":  "Jobs",
        "keyword":     roles,
        "location":    ",".join(gcc_locs),
        "pageNo":      page,
        "noOfResults": 20,
        "experienceFrom": max(0, profile.get("experience_years", 0) - 2),
        "experienceTo":   profile.get("experience_years", 0) + 3,
        "sortBy":      "Relevance",
    }


def _parse_job(raw: Dict) -> Dict:
    locations = raw.get("locations", [])
    location = ", ".join(
        loc.get("city", "") or loc.get("country", "")
        for loc in locations if isinstance(loc, dict)
    )

    salary_from = raw.get("salaryFrom")
    salary_to   = raw.get("salaryTo")
    currency    = raw.get("currency", "AED")
    salary = f"{currency} {salary_from}–{salary_to}/month" if salary_from and salary_to else None

    return {
        "job_title":          raw.get("jobTitle", "").strip(),
        "company":            raw.get("companyName", "").strip(),
        "location":           location,
        "salary_range":       salary,
        "job_url":            raw.get("jobUrl") or f"https://www.naukrigulf.com/job/{raw.get('jobId', '')}",
        "description_snippet": (raw.get("jobDescription") or "")[:500],
        "posted_date":        date.today().isoformat(),
        "source":             "naukrigulf",
        "source_job_id":      str(raw.get("jobId", "")),
        "job_type":           "full_time",
        "seniority":          None,
    }


def scrape(profile: Dict) -> List[Dict]:
    # Only run if user has GCC locations in their profile
    locations = profile.get("locations", [])
    has_gcc = any(
        any(c.lower() in loc.lower() for c in GCC_COUNTRIES + ["gulf", "gcc", "dubai", "abu dhabi", "riyadh", "doha"])
        for loc in locations
    )
    if not has_gcc:
        logger.info("[NaukriGulf] No GCC locations in profile, skipping")
        return []

    all_jobs: List[Dict] = []

    for page in range(1, 4):
        try:
            resp = requests.get(
                SEARCH_URL, headers=HEADERS, params=build_payload(profile, page), timeout=20
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            logger.warning(f"[NaukriGulf] Page {page} failed: {e}")
            break

        raw_jobs = data.get("jobDetails", []) or data.get("jobs", []) or []
        if not raw_jobs:
            break

        for raw in raw_jobs:
            all_jobs.append(_parse_job(raw))

        time.sleep(1)

    logger.info(f"[NaukriGulf] {len(all_jobs)} jobs found")
    return all_jobs
