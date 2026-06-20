"""
Foundit (formerly Monster India) Scraper
-----------------------------------------
foundit.in — significant volume for mid-senior roles in India.
Uses their public search endpoint.
"""

import requests
import logging
from typing import List, Dict
from datetime import date
import time

logger = logging.getLogger(__name__)

SEARCH_URL = "https://www.foundit.in/srp/results"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Accept": "application/json, text/plain, */*",
    "Referer": "https://www.foundit.in/",
}


def build_params(profile: Dict, page: int = 1) -> Dict:
    roles     = " OR ".join(profile.get("target_roles", ["research manager"]))
    locations = ",".join(profile.get("locations", ["India"]))
    exp_min   = max(0, profile.get("experience_years", 0) - 2)
    exp_max   = profile.get("experience_years", 0) + 3

    return {
        "query":    roles,
        "location": locations,
        "experienceFrom": exp_min,
        "experienceTo":   exp_max,
        "sort":     "1",   # 1 = most recent
        "limit":    25,
        "start":    (page - 1) * 25,
    }


def _parse_job(raw: Dict) -> Dict:
    location = ""
    if isinstance(raw.get("locations"), list):
        location = ", ".join(loc.get("label", "") for loc in raw["locations"] if isinstance(loc, dict))
    elif isinstance(raw.get("location"), str):
        location = raw["location"]

    salary = None
    if raw.get("minSalary") and raw.get("maxSalary"):
        salary = f"{raw['minSalary']} - {raw['maxSalary']} LPA"

    return {
        "job_title":          raw.get("title", "").strip(),
        "company":            raw.get("companyName", "").strip(),
        "location":           location,
        "salary_range":       salary,
        "job_url":            raw.get("applyUrl") or raw.get("jobDetailUrl") or "https://www.foundit.in",
        "description_snippet": (raw.get("jobDescription") or "")[:500],
        "posted_date":        date.today().isoformat(),
        "source":             "foundit",
        "source_job_id":      str(raw.get("jobId") or raw.get("id", "")),
        "job_type":           "full_time",
        "seniority":          None,
    }


def scrape(profile: Dict) -> List[Dict]:
    all_jobs: List[Dict] = []

    for page in range(1, 4):  # max 3 pages
        try:
            resp = requests.get(
                SEARCH_URL, headers=HEADERS, params=build_params(profile, page), timeout=20
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            logger.warning(f"[Foundit] Page {page} failed: {e}")
            break

        raw_jobs = data.get("data", {}).get("jobList", []) or data.get("jobs", []) or []
        if not raw_jobs:
            break

        for raw in raw_jobs:
            all_jobs.append(_parse_job(raw))

        time.sleep(1)

    logger.info(f"[Foundit] {len(all_jobs)} jobs found")
    return all_jobs
