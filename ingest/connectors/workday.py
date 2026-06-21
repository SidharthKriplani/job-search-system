"""
Workday — the ATS most big global firms (and their India GCCs) run on.

Each company exposes a public CXS JSON endpoint:
  POST https://{tenant}.wd{N}.myworkdayjobs.com/wday/cxs/{tenant}/{site}/jobs
  body: {"appliedFacets":{}, "limit":20, "offset":0, "searchText":""}
Response: {"total": N, "jobPostings":[{title, locationsText, externalPath, ...}]}

Tenants in registry.WORKDAY are (tenant, wd, site, display_name) — each verified
to return jobs. Failsafe: any error returns [] and the run continues.

Config:
  WORKDAY_MAX_PER_COMPANY  default 150   (cap pages so a 2,000-job board is bounded)
"""
import logging
import os
from typing import Dict, List

from ..base import http_json, make_job
from ..registry import WORKDAY

logger = logging.getLogger(__name__)
SOURCE = "workday"
PAGE = 20
# India-focused product: search the board for India directly instead of fetching
# the first N GLOBAL jobs and discarding the rest. On a huge board (e.g. Citi has
# thousands of global jobs, ~170 in India), the global-first approach never
# reached the India roles. `searchText` is a loose ranker, so India jobs come back
# first; the downstream location filter still drops any stray non-India result.
SEARCH_TEXT = os.environ.get("WORKDAY_SEARCH_TEXT", "India")


def fetch_company(tenant: str, wd: str, site: str, display: str, cap: int) -> List[Dict]:
    api  = f"https://{tenant}.{wd}.myworkdayjobs.com/wday/cxs/{tenant}/{site}/jobs"
    base = f"https://{tenant}.{wd}.myworkdayjobs.com/en-US/{site}"
    out: List[Dict] = []
    offset = 0
    while offset < cap:
        data = http_json(api, method="POST",
                         json_body={"appliedFacets": {}, "limit": PAGE, "offset": offset, "searchText": SEARCH_TEXT})
        if not data:
            break
        postings = data.get("jobPostings", [])
        if not postings:
            break
        for raw in postings:
            ext = raw.get("externalPath", "")
            job = make_job(
                title=raw.get("title", ""),
                company=display,
                url=f"{base}{ext}" if ext else base,
                source=SOURCE,
                location=raw.get("locationsText", "") or "",
                posted=raw.get("startDate") or raw.get("postedOn"),
                source_job_id=(raw.get("bulletFields") or [ext])[0] or ext,
            )
            if job:
                out.append(job)
        total = data.get("total", 0)
        offset += PAGE
        if offset >= total:
            break
    return out


def fetch() -> List[Dict]:
    cap = int(os.environ.get("WORKDAY_MAX_PER_COMPANY", "150"))
    jobs: List[Dict] = []
    for tenant, wd, site, display in WORKDAY:
        try:
            jobs.extend(fetch_company(tenant, wd, site, display, cap))
        except Exception as e:
            logger.warning(f"[workday] {display} failed: {e}")
    logger.info(f"[workday] {len(jobs)} jobs across {len(WORKDAY)} tenants")
    return jobs
