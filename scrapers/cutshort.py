"""
Cutshort Scraper
-----------------
cutshort.io — strong for tech + data roles in Indian startups and mid-size companies.
Has a public API (no auth needed for search).
"""

import requests
import logging
from typing import List, Dict
from datetime import date
import time

logger = logging.getLogger(__name__)

SEARCH_URL = "https://cutshort.io/api/web/jobs/search"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Accept": "application/json",
    "Content-Type": "application/json",
    "Referer": "https://cutshort.io/",
}


def build_payload(profile: Dict, skip: int = 0) -> Dict:
    roles = profile.get("target_roles", ["research manager"])
    locations = profile.get("locations", ["India"])
    exp = profile.get("experience_years", 5)

    # Filter out GCC locations (Cutshort is India-focused)
    india_locations = [l for l in locations if not any(
        gcc in l.lower() for gcc in ["uae", "qatar", "saudi", "kuwait", "dubai", "gcc"]
    )]
    if not india_locations:
        india_locations = ["India"]

    return {
        "query": " OR ".join(roles),
        "locations": india_locations,
        "experienceRequired": {"min": max(0, exp - 2), "max": exp + 3},
        "skip": skip,
        "limit": 20,
        "sort": "recent",
    }


def _parse_job(raw: Dict) -> Dict:
    company = raw.get("company", {})
    company_name = company.get("name", "") if isinstance(company, dict) else str(company)

    locations = raw.get("locations", [])
    location = ", ".join(
        (loc.get("name") or loc.get("city") or "") if isinstance(loc, dict) else str(loc)
        for loc in locations
    )

    salary_min = raw.get("minCtc") or raw.get("salaryMin")
    salary_max = raw.get("maxCtc") or raw.get("salaryMax")
    salary = f"₹{salary_min}–{salary_max} LPA" if salary_min and salary_max else None

    job_id = raw.get("id") or raw.get("jobId", "")
    job_url = f"https://cutshort.io/jobs/{job_id}" if job_id else "https://cutshort.io/jobs"

    return {
        "job_title":          raw.get("title", "").strip(),
        "company":            company_name,
        "location":           location,
        "salary_range":       salary,
        "job_url":            job_url,
        "description_snippet": (raw.get("description") or raw.get("jobDescription") or "")[:500],
        "posted_date":        date.today().isoformat(),
        "source":             "cutshort",
        "source_job_id":      str(job_id),
        "job_type":           "full_time",
        "seniority":          raw.get("seniority"),
    }


def scrape(profile: Dict) -> List[Dict]:
    all_jobs: List[Dict] = []
    skip = 0

    for _ in range(3):  # max 3 pages
        try:
            resp = requests.post(
                SEARCH_URL, headers=HEADERS, json=build_payload(profile, skip), timeout=20
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            logger.warning(f"[Cutshort] skip={skip} failed: {e}")
            break

        raw_jobs = data.get("data", []) or data.get("jobs", []) or []
        if not raw_jobs:
            break

        for raw in raw_jobs:
            all_jobs.append(_parse_job(raw))

        skip += len(raw_jobs)
        if len(raw_jobs) < 20:
            break

        time.sleep(1)

    logger.info(f"[Cutshort] {len(all_jobs)} jobs found")
    return all_jobs
