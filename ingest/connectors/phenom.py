"""
Phenom — the career-site engine behind many large enterprises' India hiring
(NTT, Mastercard, DuPont, Danaher, ...). Public widgets JSON, no auth:

  POST https://{host}/widgets
  body: {"ddoKey":"refineSearch", "keywords":"India", "from":0, "size":N, ...}
  Response: {refineSearch: {totalHits, data: {jobs: [{title, jobSeqNo, jobId,
             location, cityStateCountry, country, descriptionTeaser, postedDate,
             type, category, ...}]}}}

Job page: https://{host}{locale_path}/job/{jobSeqNo} — the locale prefix is
REQUIRED (e.g. /global/en for NTT, /us/en for Mastercard). The bare /job/{seq}
route serves the SPA shell which client-redirects to the homepage. locale_path
lives per tenant in registry.PHENOM, verified by title-in-HTML probe.

NOTE: keywords is a loose ranker (like Workday's searchText) — India jobs come
back first but strays appear; the downstream location filter drops them. Some
Phenom tenants sit behind bot protection (403) — failsafe returns [] and the
run continues (some hosts also just aren't Phenom; probing is how tenants are
verified before entering registry.PHENOM).

Config:
  PHENOM_MAX_PER_COMPANY  default 200
  PHENOM_SEARCH_TEXT      default "India"
"""
import logging
import os
from typing import Dict, List

from ..base import http_json, make_job

logger = logging.getLogger(__name__)
SOURCE = "phenom"
PAGE = 50
SEARCH_TEXT = os.environ.get("PHENOM_SEARCH_TEXT", "India")


def _body(offset: int, size: int) -> dict:
    return {
        "lang": "en_us", "deviceType": "desktop", "country": "us",
        "pageName": "search-results", "ddoKey": "refineSearch",
        "sortBy": "", "subsearch": "", "from": offset, "jobs": True,
        "counts": True, "all_fields": ["country", "city"], "size": size,
        "clearAll": False, "jdsource": "facets", "isSliderEnable": False,
        "keywords": SEARCH_TEXT, "global": True, "selected_fields": {},
        "locationData": {},
    }


def fetch_site(host: str, display: str, cap: int = 0, locale: str = "") -> List[Dict]:
    cap = cap or int(os.environ.get("PHENOM_MAX_PER_COMPANY", "200"))
    if not locale:  # look up from registry when not passed explicitly
        from ..registry import PHENOM
        locale = next((lp for h, lp, _d in PHENOM if h == host), "/us/en")
    out: List[Dict] = []
    offset = 0
    while offset < cap:
        data = http_json(f"https://{host}/widgets", method="POST",
                         json_body=_body(offset, min(PAGE, cap - offset)))
        if not data:
            break
        rs = data.get("refineSearch") or {}
        jobs = ((rs.get("data") or {}).get("jobs")) or []
        if not jobs:
            break
        for j in jobs:
            seq = j.get("jobSeqNo") or j.get("jobId") or ""
            job = make_job(
                title=j.get("title", ""),
                company=display,
                url=f"https://{host}{locale}/job/{seq}" if seq else "",
                source=SOURCE,
                location=j.get("location") or j.get("cityStateCountry") or "",
                description=j.get("descriptionTeaser", ""),
                posted=j.get("postedDate") or j.get("dateCreated"),
                source_job_id=str(seq),
                job_type=j.get("type"),
            )
            if job:
                out.append(job)
        total = int(rs.get("totalHits") or 0)
        offset += PAGE
        if offset >= total:
            break
    return out


def fetch() -> List[Dict]:
    from ..registry import PHENOM
    cap = int(os.environ.get("PHENOM_MAX_PER_COMPANY", "200"))
    jobs: List[Dict] = []
    for host, locale, display in PHENOM:
        try:
            jobs.extend(fetch_site(host, display, cap, locale))
        except Exception as e:
            logger.warning(f"[phenom] {host} failed: {e}")
    return jobs
