"""
Instahyre Scraper
------------------
instahyre.com — fast-growing in India for mid-senior tech and analytics roles.
Has a JSON API endpoint.
"""

import requests
import logging
from typing import List, Dict
from datetime import date
import time

logger = logging.getLogger(__name__)

SEARCH_URL = "https://www.instahyre.com/api/v1/opportunity/"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Accept": "application/json",
    "Referer": "https://www.instahyre.com/",
    "X-Requested-With": "XMLHttpRequest",
}


def build_params(profile: Dict, page: int = 1) -> Dict:
    roles = " ".join(profile.get("target_roles", ["research manager"]))
    return {
        "q":        roles,
        "limit":    20,
        "offset":   (page - 1) * 20,
        "ordering": "-posted",
    }


def _parse_job(raw: Dict) -> Dict:
    company = raw.get("company", {})
    company_name = company.get("name", "") if isinstance(company, dict) else str(company)

    locations = raw.get("locations", [])
    location = ", ".join(
        loc.get("name", "") if isinstance(loc, dict) else str(loc)
        for loc in locations
    )

    salary_min = raw.get("ctc_min")
    salary_max = raw.get("ctc_max")
    salary = f"₹{salary_min}–{salary_max} LPA" if salary_min and salary_max else None

    slug = raw.get("slug") or raw.get("id", "")
    job_url = f"https://www.instahyre.com/jobs/{slug}/" if slug else "https://www.instahyre.com"

    return {
        "job_title":          raw.get("designation", "").strip(),
        "company":            company_name,
        "location":           location,
        "salary_range":       salary,
        "job_url":            job_url,
        "description_snippet": (raw.get("description") or "")[:500],
        "posted_date":        date.today().isoformat(),
        "source":             "instahyre",
        "source_job_id":      str(raw.get("id", "")),
        "job_type":           "full_time",
        "seniority":          raw.get("seniority_level"),
    }


def scrape(profile: Dict) -> List[Dict]:
    all_jobs: List[Dict] = []

    for page in range(1, 4):
        try:
            resp = requests.get(SEARCH_URL, headers=HEADERS, params=build_params(profile, page), timeout=20)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            logger.warning(f"[Instahyre] Page {page} failed: {e}")
            break

        raw_jobs = data.get("results", []) or data.get("opportunities", []) or []
        if not raw_jobs:
            break

        for raw in raw_jobs:
            all_jobs.append(_parse_job(raw))

        if not data.get("next"):
            break

        time.sleep(1)

    logger.info(f"[Instahyre] {len(all_jobs)} jobs found")
    return all_jobs
