"""
Lever — free public postings API, no auth.
  GET https://api.lever.co/v0/postings/{slug}?mode=json
Job object: {text, categories:{location,commitment,department}, hostedUrl, createdAt, id, descriptionPlain, workplaceType}
"""
import logging
from typing import Dict, List

from ..base import http_json, make_job
from ..registry import LEVER

logger = logging.getLogger(__name__)
SOURCE = "lever"


def fetch_board(slug: str, display: str) -> List[Dict]:
    data = http_json(f"https://api.lever.co/v0/postings/{slug}", params={"mode": "json"})
    if not isinstance(data, list):
        return []
    out = []
    for j in data:
        cats = j.get("categories") or {}
        loc = cats.get("location") or ""
        if not loc:
            all_locs = cats.get("allLocations") or []
            loc = all_locs[0] if all_locs else ""
        remote = str(j.get("workplaceType", "")).lower() == "remote" or "remote" in str(loc).lower()
        job = make_job(
            title=j.get("text", ""),
            company=display,
            url=j.get("hostedUrl") or j.get("applyUrl", ""),
            source=SOURCE,
            location=loc or "",
            description=j.get("descriptionPlain", ""),
            posted=j.get("createdAt"),
            source_job_id=j.get("id", ""),
            job_type=cats.get("commitment"),
            remote=remote,
        )
        if job:
            out.append(job)
    return out


def fetch() -> List[Dict]:
    jobs: List[Dict] = []
    for slug, display in LEVER:
        try:
            jobs.extend(fetch_board(slug, display))
        except Exception as e:
            logger.warning(f"[lever] {slug} failed: {e}")
    return jobs
