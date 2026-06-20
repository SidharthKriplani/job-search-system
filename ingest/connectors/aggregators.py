"""
Official aggregator APIs — breadth beyond ATS-using companies (covers the long
tail and non-tech / India roles).

  Remotive   — free, no key. Remote jobs across categories.
  Arbeitnow  — free, no key. Broad board (Europe-heavy but global).
  Adzuna     — free key required (app_id + app_key). THE breadth/India engine:
               query by keyword + country + location + salary. Skips cleanly if
               ADZUNA_APP_ID / ADZUNA_APP_KEY are not set.

Configure Adzuna via env:
  ADZUNA_APP_ID, ADZUNA_APP_KEY
  ADZUNA_COUNTRIES  (default "in,gb,us")
  ADZUNA_QUERIES    (default "manager,analyst,engineer,research,finance")
"""
import logging
import os
from typing import Dict, List

from ..base import http_json, make_job

logger = logging.getLogger(__name__)


def fetch_remotive() -> List[Dict]:
    data = http_json("https://remotive.com/api/remote-jobs", params={"limit": 100})
    if not data or "jobs" not in data:
        return []
    out = []
    for j in data["jobs"]:
        job = make_job(
            title=j.get("title", ""),
            company=j.get("company_name", ""),
            url=j.get("url", ""),
            source="remotive",
            location=j.get("candidate_required_location", "") or "Remote",
            salary_range=(j.get("salary") or None),
            description=j.get("description", ""),
            posted=j.get("publication_date"),
            source_job_id=j.get("id", ""),
            job_type=j.get("job_type"),
            remote=True,
        )
        if job:
            out.append(job)
    return out


def fetch_arbeitnow() -> List[Dict]:
    data = http_json("https://www.arbeitnow.com/api/job-board-api")
    if not data or "data" not in data:
        return []
    out = []
    for j in data["data"]:
        jtypes = j.get("job_types") or []
        job = make_job(
            title=j.get("title", ""),
            company=j.get("company_name", ""),
            url=j.get("url", ""),
            source="arbeitnow",
            location=j.get("location", ""),
            description=j.get("description", ""),
            posted=j.get("created_at"),
            source_job_id=j.get("slug", ""),
            job_type=(jtypes[0] if jtypes else None),
            remote=bool(j.get("remote")),
        )
        if job:
            out.append(job)
    return out


def fetch_adzuna() -> List[Dict]:
    app_id = os.environ.get("ADZUNA_APP_ID")
    app_key = os.environ.get("ADZUNA_APP_KEY")
    if not app_id or not app_key:
        logger.info("[adzuna] no ADZUNA_APP_ID/KEY set — skipping (free key enables India + salary data)")
        return []

    countries = [c.strip() for c in os.environ.get("ADZUNA_COUNTRIES", "in,gb,us").split(",") if c.strip()]
    queries = [q.strip() for q in os.environ.get("ADZUNA_QUERIES", "manager,analyst,engineer,research,finance").split(",") if q.strip()]

    out: List[Dict] = []
    for country in countries:
        for q in queries:
            url = f"https://api.adzuna.com/v1/api/jobs/{country}/search/1"
            data = http_json(url, params={
                "app_id": app_id, "app_key": app_key,
                "results_per_page": 50, "what": q, "max_days_old": 14,
                "content-type": "application/json",
            })
            if not data or "results" not in data:
                continue
            for j in data["results"]:
                smin, smax = j.get("salary_min"), j.get("salary_max")
                salary = f"{int(smin)}-{int(smax)}" if smin and smax else None
                job = make_job(
                    title=j.get("title", ""),
                    company=(j.get("company") or {}).get("display_name", ""),
                    url=j.get("redirect_url", ""),
                    source=f"adzuna_{country}",
                    location=(j.get("location") or {}).get("display_name", ""),
                    salary_range=salary,
                    description=j.get("description", ""),
                    posted=j.get("created"),
                    source_job_id=j.get("id", ""),
                    job_type=j.get("contract_time"),
                )
                if job:
                    out.append(job)
    return out


def fetch() -> List[Dict]:
    jobs: List[Dict] = []
    for fn in (fetch_remotive, fetch_arbeitnow, fetch_adzuna):
        try:
            jobs.extend(fn())
        except Exception as e:
            logger.warning(f"[aggregators] {fn.__name__} failed: {e}")
    return jobs
