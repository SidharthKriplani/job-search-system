"""
Workable — public widget API, no auth. Many startups (incl. India) hire on it.
  GET https://apply.workable.com/api/v1/widget/accounts/{slug}?details=true
Response: {name, description, jobs:[{title, shortcode, url, city, state, country,
           employment_type, telecommuting, published_on, description, ...}]}
(details=true includes the JD; strip_html trims it to the snippet limit anyway.)

Registry lists in registry.WORKABLE are (slug, display_name) — verified live.
Curated is UNIONed with our harvested list (data/workable_companies.json, built
by ingest/harvester.py). Failsafe: any error returns [] and the run continues.

Config:
  WORKABLE_MAX_PER_COMPANY  default 500  (bound one giant board)
"""
import logging
import os
from typing import Dict, List

from ..base import http_json, make_job

logger = logging.getLogger(__name__)
SOURCE = "workable"
API = "https://apply.workable.com/api/v1/widget/accounts/{slug}"


def fetch_board(slug: str, display: str, cap: int = 0) -> List[Dict]:
    cap = cap or int(os.environ.get("WORKABLE_MAX_PER_COMPANY", "500"))
    data = http_json(API.format(slug=slug), params={"details": "true"})
    if not data or "jobs" not in data:
        return []
    company = data.get("name") or display
    out: List[Dict] = []
    for j in data["jobs"][:cap]:
        loc = ", ".join(p for p in (j.get("city"), j.get("state"), j.get("country")) if p)
        job = make_job(
            title=j.get("title", ""),
            company=company,
            url=j.get("url") or j.get("shortlink") or "",
            source=SOURCE,
            location=loc,
            description=j.get("description", ""),
            posted=j.get("published_on") or j.get("created_at"),
            source_job_id=j.get("shortcode", ""),
            job_type=j.get("employment_type"),
            remote=str(j.get("telecommuting", "")).lower() == "true",
        )
        if job:
            out.append(job)
    return out


def fetch() -> List[Dict]:
    from ..registry import all_workable
    jobs: List[Dict] = []
    for slug, display in all_workable():
        try:
            jobs.extend(fetch_board(slug, display))
        except Exception as e:
            logger.warning(f"[workable] {slug} failed: {e}")
    return jobs
