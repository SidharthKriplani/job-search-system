"""
Instahyre — India-native tech/analytics job board with a public JSON API.

  GET https://www.instahyre.com/api/v1/job_search/?limit=35&offset=N
Returns anonymous public listings (no auth). India-only, so every result counts
toward the India coverage this product cares about (unlike the global-remote
APIs, whose 'India' is mostly US-remote noise).
"""
import logging
import time
from typing import Dict, List

import requests
from ..base import make_job

logger = logging.getLogger(__name__)
SOURCE = "instahyre"

# Instahyre serves ~35/page; walk until a short/empty page or the safety cap.
PAGE = 35
MAX_JOBS = int(__import__("os").environ.get("INSTAHYRE_MAX", "1000"))
# Instahyre 503s the default bot UA — send a realistic browser UA.
_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0 Safari/537.36",
    "Accept": "application/json",
    "Referer": "https://www.instahyre.com/",
    "X-Requested-With": "XMLHttpRequest",
}


def _get(offset: int):
    try:
        r = requests.get("https://www.instahyre.com/api/v1/job_search/",
                         params={"limit": PAGE, "offset": offset}, headers=_HEADERS, timeout=15)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        logger.warning(f"[instahyre] offset {offset} failed: {type(e).__name__}: {e}")
        return None


def fetch() -> List[Dict]:
    out: List[Dict] = []
    offset = 0
    while offset < MAX_JOBS:
        data = _get(offset)
        rows = (data.get("objects") if isinstance(data, dict) else data) or []
        if not rows:
            break
        for r in rows:
            emp = r.get("employer") or {}
            company = emp.get("company_name", "") if isinstance(emp, dict) else str(emp)
            loc = r.get("locations")
            location = loc if isinstance(loc, str) else ", ".join(
                (l.get("name", "") if isinstance(l, dict) else str(l)) for l in (loc or [])
            )
            kws = r.get("keywords")
            desc = ", ".join(kws) if isinstance(kws, list) else (kws or "")
            job = make_job(
                title=r.get("title", ""),
                company=company,
                url=r.get("public_url", "") or "https://www.instahyre.com",
                source=SOURCE,
                location=location or "India",
                description=desc,
                source_job_id=str(r.get("id", "")),
            )
            if job:
                out.append(job)
        if len(rows) < PAGE:
            break
        offset += PAGE
        time.sleep(1.0)  # be polite — instahyre rate-limits bursts
    logger.info(f"[instahyre] {len(out)} India jobs")
    return out
