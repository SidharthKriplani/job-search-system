"""
Eightfold AI — enterprise career sites ({tenant}.eightfold.ai). Public JSON:

  GET https://{tenant}.eightfold.ai/api/apply/v2/jobs
      ?domain={company-domain}&start=0&num=100&location=India
  Response: {count, positions: [{id, name, location, locations, t_update,
             canonicalPositionUrl, ...}]}
Job page fallback: https://{tenant}.eightfold.ai/careers/job/{id}

BEST-EFFORT (instahyre precedent): Eightfold 403s datacenter IPs (verified
2026-07-15 from a cloud runner with browser UA + referer). The connector is
fully failsafe — contributes jobs if/when unblocked, else 0 at the cost of a
couple of requests. If it stays 0 on /health for a month, delist the tenants.

Config:
  EIGHTFOLD_MAX_PER_COMPANY  default 200
  EIGHTFOLD_LOCATION         default "India"
"""
import logging
import os
from typing import Dict, List

from ..base import http_json, make_job

logger = logging.getLogger(__name__)
SOURCE = "eightfold"
PAGE = 100
LOCATION = os.environ.get("EIGHTFOLD_LOCATION", "India")


def fetch_company(tenant: str, domain: str, display: str, cap: int = 0) -> List[Dict]:
    cap = cap or int(os.environ.get("EIGHTFOLD_MAX_PER_COMPANY", "200"))
    out: List[Dict] = []
    start = 0
    while start < cap:
        data = http_json(
            f"https://{tenant}.eightfold.ai/api/apply/v2/jobs",
            params={"domain": domain, "start": start,
                    "num": min(PAGE, cap - start), "location": LOCATION},
        )
        if not data:
            break
        positions = data.get("positions") or []
        if not positions:
            break
        for p in positions:
            pid = p.get("id", "")
            locs = p.get("locations") or []
            loc = p.get("location") or (", ".join(str(x) for x in locs[:2]) if locs else "")
            job = make_job(
                title=p.get("name", ""),
                company=display,
                url=p.get("canonicalPositionUrl")
                    or (f"https://{tenant}.eightfold.ai/careers/job/{pid}" if pid else ""),
                source=SOURCE,
                location=loc,
                description=p.get("job_description", ""),
                posted=p.get("t_update") or p.get("t_create"),
                source_job_id=str(pid),
            )
            if job:
                out.append(job)
        total = int(data.get("count") or 0)
        start += PAGE
        if start >= total:
            break
    return out


def fetch() -> List[Dict]:
    from ..registry import EIGHTFOLD
    cap = int(os.environ.get("EIGHTFOLD_MAX_PER_COMPANY", "200"))
    jobs: List[Dict] = []
    for tenant, domain, display in EIGHTFOLD:
        try:
            jobs.extend(fetch_company(tenant, domain, display, cap))
        except Exception as e:
            logger.warning(f"[eightfold] {tenant} failed: {e}")
    return jobs
