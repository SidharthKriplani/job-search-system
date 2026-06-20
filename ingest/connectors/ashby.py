"""
Ashby — free public job-board API, no auth.
  GET https://api.ashbyhq.com/posting-api/job-board/{slug}
Job object: {title, location, employmentType, jobUrl, applyUrl, publishedAt, isRemote, id, descriptionPlain, department}
"""
import logging
from typing import Dict, List

from ..base import http_json, make_job
from ..registry import ASHBY

logger = logging.getLogger(__name__)
SOURCE = "ashby"


def fetch_board(slug: str, display: str) -> List[Dict]:
    data = http_json(f"https://api.ashbyhq.com/posting-api/job-board/{slug}")
    if not data or "jobs" not in data:
        return []
    out = []
    for j in data["jobs"]:
        job = make_job(
            title=j.get("title", ""),
            company=display,
            url=j.get("jobUrl") or j.get("applyUrl", ""),
            source=SOURCE,
            location=j.get("location", "") or "",
            description=j.get("descriptionPlain", ""),
            posted=j.get("publishedAt"),
            source_job_id=j.get("id", ""),
            job_type=j.get("employmentType"),
            remote=bool(j.get("isRemote")),
        )
        if job:
            out.append(job)
    return out


def fetch() -> List[Dict]:
    jobs: List[Dict] = []
    for slug, display in ASHBY:
        try:
            jobs.extend(fetch_board(slug, display))
        except Exception as e:
            logger.warning(f"[ashby] {slug} failed: {e}")
    return jobs
