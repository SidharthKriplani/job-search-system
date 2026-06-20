"""
Greenhouse — free public board API, no auth.
  GET https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true
Job object: {title, location:{name}, absolute_url, updated_at, id, company_name, content}
"""
import logging
from typing import Dict, List

from ..base import http_json, make_job
from ..registry import GREENHOUSE

logger = logging.getLogger(__name__)
SOURCE = "greenhouse"


def fetch_board(slug: str, display: str) -> List[Dict]:
    data = http_json(f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs", params={"content": "true"})
    if not data or "jobs" not in data:
        return []
    out = []
    for j in data["jobs"]:
        loc = (j.get("location") or {}).get("name", "") if isinstance(j.get("location"), dict) else ""
        job = make_job(
            title=j.get("title", ""),
            company=j.get("company_name") or display,
            url=j.get("absolute_url", ""),
            source=SOURCE,
            location=loc,
            description=j.get("content", ""),
            posted=j.get("updated_at") or j.get("first_published"),
            source_job_id=j.get("id", ""),
            remote="remote" in loc.lower(),
        )
        if job:
            out.append(job)
    return out


def fetch() -> List[Dict]:
    jobs: List[Dict] = []
    for slug, display in GREENHOUSE:
        try:
            jobs.extend(fetch_board(slug, display))
        except Exception as e:
            logger.warning(f"[greenhouse] {slug} failed: {e}")
    return jobs
