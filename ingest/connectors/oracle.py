"""
Oracle Recruiting Cloud (ORC) — the ATS many banks / finance firms run on
(JPMorgan, Jefferies, EXL, …). Public unauthenticated JSON endpoint:

  GET https://{host}/hcmRestApi/resources/latest/recruitingCEJobRequisitions
      ?onlyData=true&expand=requisitionList.secondaryLocations
      &finder=findReqs;siteNumber={site},keyword=India,limit=N,sortBy=POSTING_DATES_DESC

`keyword=India` is a loose ranker (India-focused product) so India roles come
back first; the downstream location filter drops any stray non-India result.
Apply URL: https://{host}/hcmUI/CandidateExperience/en/sites/{site}/job/{Id}

Registry entries are (host, site_number, display_name). Failsafe: any error → [].
"""
import logging
import os
from typing import Dict, List

from ..base import http_json, make_job
from ..registry import ORACLE

logger = logging.getLogger(__name__)
SOURCE = "oracle"
SEARCH = os.environ.get("ORACLE_SEARCH_KEYWORD", "India")


def fetch_company(host: str, site: str, display: str, cap: int) -> List[Dict]:
    api = f"https://{host}/hcmRestApi/resources/latest/recruitingCEJobRequisitions"
    job_base = f"https://{host}/hcmUI/CandidateExperience/en/sites/{site}/job"
    limit = min(max(cap, 1), 200)   # ORC caps a page at 200
    finder = (f"findReqs;siteNumber={site},keyword={SEARCH},"
              f"limit={limit},sortBy=POSTING_DATES_DESC")
    data = http_json(api, params={
        "onlyData": "true",
        "expand": "requisitionList.secondaryLocations",
        "finder": finder,
    })
    if not data:
        return []
    items = data.get("items") or [{}]
    reqs = (items[0] or {}).get("requisitionList") or []
    out: List[Dict] = []
    for raw in reqs:
        jid = raw.get("Id")
        job = make_job(
            title=raw.get("Title", ""),
            company=display,
            url=f"{job_base}/{jid}" if jid else job_base,
            source=SOURCE,
            location=raw.get("PrimaryLocation", "") or "",
            description=raw.get("ShortDescriptionStr", "") or "",
            posted=raw.get("PostedDate"),
            source_job_id=str(jid or ""),
            job_type=raw.get("JobType"),
        )
        if job:
            out.append(job)
    return out


def fetch() -> List[Dict]:
    cap = int(os.environ.get("ORACLE_MAX_PER_COMPANY", "200"))
    jobs: List[Dict] = []
    for host, site, display in ORACLE:
        try:
            jobs.extend(fetch_company(host, site, display, cap))
        except Exception as e:
            logger.warning(f"[oracle] {display} failed: {e}")
    logger.info(f"[oracle] {len(jobs)} jobs across {len(ORACLE)} tenants")
    return jobs
