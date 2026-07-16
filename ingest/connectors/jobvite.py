"""
Jobvite — public hosted career sites, server-rendered HTML (shared template).
  GET https://jobs.jobvite.com/{slug}/search?p={page}   (50 rows/page, p 0-based)
  → <td class="jv-job-list-name"><a href="/{slug}/job/{id}">Title</a></td>
    <td class="jv-job-list-location"> City, Region </td>

Job page: https://jobs.jobvite.com/{slug}/job/{id} (server-rendered; verified).
The listing has no posted date and no JD (per-job pages are N+1 — skipped, same
trade-off as bamboohr). The `l=` location param is IGNORED by some tenants
(egnyte returns its full global list for l=India — verified 2026-07-17), so we
fetch ALL rows and let the per-user pipeline filter, like bamboohr.

Registry entries are (slug, display) in registry.JOBVITE. Failsafe: any error
returns [] and the run continues.

Config:
  JOBVITE_MAX_PER_COMPANY  default 300
"""
import logging
import os
import re
from html import unescape
from typing import Dict, List

import requests

from ..base import HEADERS, make_job

logger = logging.getLogger(__name__)
SOURCE = "jobvite"
PAGE = 50  # rows per page, p is 0-based

_ROW = re.compile(
    r'<td class="jv-job-list-name">\s*<a href="(/[^"/]+/job/([^"]+))"[^>]*>(.*?)</a>'
    r'.*?<td class="jv-job-list-location">(.*?)</td>',
    re.S,
)


def _clean(text: str) -> str:
    """Collapse whitespace and strip the '<div class=jv-meta>N Locations</div>' wrapper."""
    text = re.sub(r"<[^>]+>", " ", text)
    return unescape(re.sub(r"\s+", " ", text)).strip().strip(",").strip()


def fetch_company(slug: str, display: str, cap: int = 0) -> List[Dict]:
    cap = cap or int(os.environ.get("JOBVITE_MAX_PER_COMPANY", "300"))
    out: List[Dict] = []
    seen: set = set()
    page = 0
    while len(out) < cap:
        try:
            r = requests.get(f"https://jobs.jobvite.com/{slug}/search",
                             params={"p": page},
                             headers={**HEADERS, "Accept": "text/html"}, timeout=20)
            r.raise_for_status()
        except Exception as e:
            logger.warning(f"[jobvite] {slug} page {page} failed: {type(e).__name__}")
            break
        rows = _ROW.findall(r.text)
        new = 0
        for href, jid, title, loc in rows:
            if jid in seen:
                continue
            seen.add(jid)
            new += 1
            job = make_job(
                title=_clean(title),
                company=display,
                url=f"https://jobs.jobvite.com{href}",
                source=SOURCE,
                location=_clean(loc),
                source_job_id=jid,
            )
            if job:
                out.append(job)
        if new == 0:  # empty page or pure duplicates → done
            break
        page += 1
    return out[:cap]


def fetch() -> List[Dict]:
    from ..registry import JOBVITE
    jobs: List[Dict] = []
    for slug, display in JOBVITE:
        try:
            jobs.extend(fetch_company(slug, display))
        except Exception as e:
            logger.warning(f"[jobvite] {slug} failed: {e}")
    return jobs
