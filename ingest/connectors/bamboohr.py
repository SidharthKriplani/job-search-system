"""
BambooHR — public careers JSON, no auth. Mid-size employers (incl. India offices).
  GET https://{slug}.bamboohr.com/careers/list
Response: {meta, result:[{id, jobOpeningName, departmentLabel, employmentStatusLabel,
           location:{city,state}, isRemote, ...}]}
Job page: https://{slug}.bamboohr.com/careers/{id}

Notes: the list endpoint has no posted date and no JD (a per-job /careers/{id}/detail
exists but is N+1 — deliberately skipped; the snippet stays empty and the link
carries the JD). Registry lists in registry.BAMBOOHR are (slug, display_name).
Curated is UNIONed with our harvested list (data/bamboohr_companies.json).
Failsafe: any error returns [] and the run continues.

Config:
  BAMBOOHR_MAX_PER_COMPANY  default 200
"""
import logging
import os
from typing import Dict, List

from ..base import http_json, make_job

logger = logging.getLogger(__name__)
SOURCE = "bamboohr"


def fetch_company(slug: str, display: str, cap: int = 0) -> List[Dict]:
    cap = cap or int(os.environ.get("BAMBOOHR_MAX_PER_COMPANY", "200"))
    data = http_json(f"https://{slug}.bamboohr.com/careers/list")
    if not data or "result" not in data:
        return []
    out: List[Dict] = []
    for r in (data.get("result") or [])[:cap]:
        loc_d = r.get("location") or {}
        loc = ", ".join(p for p in (loc_d.get("city"), loc_d.get("state")) if p)
        dept = r.get("departmentLabel") or ""
        jid = r.get("id", "")
        job = make_job(
            title=r.get("jobOpeningName", ""),
            company=display,
            url=f"https://{slug}.bamboohr.com/careers/{jid}" if jid else "",
            source=SOURCE,
            location=loc,
            description=dept,  # best available context; list API has no JD
            source_job_id=str(jid),
            job_type=r.get("employmentStatusLabel"),
            remote=bool(r.get("isRemote")),
        )
        if job:
            out.append(job)
    return out


def fetch() -> List[Dict]:
    from ..registry import all_bamboohr
    jobs: List[Dict] = []
    for slug, display in all_bamboohr():
        try:
            jobs.extend(fetch_company(slug, display))
        except Exception as e:
            logger.warning(f"[bamboohr] {slug} failed: {e}")
    return jobs
