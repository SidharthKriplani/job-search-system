"""
SmartRecruiters — public jobs API (WNS, NielsenIQ, Sutherland, …).

  GET https://api.smartrecruiters.com/v1/companies/{companyId}/postings?limit=100&country=in

`country=in` filters to India server-side (no global-then-discard needed).
Apply URL: https://jobs.smartrecruiters.com/{companyId}/{postingId}

Registry entries are (company_id, display_name). Failsafe: any error → [].
"""
import logging
from typing import Dict, List

from ..base import http_json, make_job
from ..registry import SMARTRECRUITERS

logger = logging.getLogger(__name__)
SOURCE = "smartrecruiters"


def fetch_company(company_id: str, display: str) -> List[Dict]:
    api = f"https://api.smartrecruiters.com/v1/companies/{company_id}/postings"
    data = http_json(api, params={"limit": 100, "country": "in"})
    if not data:
        return []
    out: List[Dict] = []
    for raw in data.get("content", []):
        pid = raw.get("id")
        loc = raw.get("location") or {}
        location = loc.get("fullLocation") or ", ".join(
            x for x in [loc.get("city"), loc.get("region"), loc.get("country", "").upper()] if x
        )
        job = make_job(
            title=raw.get("name", ""),
            company=display,
            url=f"https://jobs.smartrecruiters.com/{company_id}/{pid}" if pid else "",
            source=SOURCE,
            location=location,
            posted=raw.get("releasedDate"),
            source_job_id=str(pid or ""),
            remote=bool(loc.get("remote")),
        )
        if job:
            out.append(job)
    return out


def fetch() -> List[Dict]:
    jobs: List[Dict] = []
    for company_id, display in SMARTRECRUITERS:
        try:
            jobs.extend(fetch_company(company_id, display))
        except Exception as e:
            logger.warning(f"[smartrecruiters] {display} failed: {e}")
    logger.info(f"[smartrecruiters] {len(jobs)} jobs across {len(SMARTRECRUITERS)} companies")
    return jobs
