"""
Recruitee — public JSON careers API used by many companies (incl. India offices).

  GET https://{slug}.recruitee.com/api/offers/
Offer: {title, city, country, location, careers_url, department, description, id}
No auth. One board per company slug (mined + live-verified from OpenJobs).
"""
import logging
from typing import Dict, List

from ..base import http_json, make_job
from ..registry import RECRUITEE

logger = logging.getLogger(__name__)
SOURCE = "recruitee"


def fetch_board(slug: str, display: str) -> List[Dict]:
    data = http_json(f"https://{slug}.recruitee.com/api/offers/")
    if not data or "offers" not in data:
        return []
    out = []
    for o in data["offers"]:
        city = (o.get("city") or "").strip()
        country = (o.get("country") or "").strip()
        loc = ", ".join(p for p in (city, country) if p) or (o.get("location") or "")
        job = make_job(
            title=o.get("title", ""),
            company=display,
            url=o.get("careers_url", "") or o.get("careers_apply_url", ""),
            source=SOURCE,
            location=loc,
            description=o.get("description", ""),
            posted=o.get("published_at") or o.get("created_at"),
            source_job_id=str(o.get("id", "")),
            remote=bool(o.get("remote")) or "remote" in (o.get("location", "") or "").lower(),
        )
        if job:
            out.append(job)
    return out


def fetch() -> List[Dict]:
    jobs: List[Dict] = []
    for slug, display in RECRUITEE:
        try:
            jobs.extend(fetch_board(slug, display))
        except Exception as e:
            logger.warning(f"[recruitee] {slug} failed: {e}")
    logger.info(f"[recruitee] {len(jobs)} jobs")
    return jobs
