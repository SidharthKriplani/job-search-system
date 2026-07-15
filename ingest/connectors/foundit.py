"""
foundit (formerly Monster India) — large India job board with a public JSON
search API. Reachable from datacenter IPs (unlike Naukri, which recaptcha-walls).

  GET https://www.foundit.in/middleware/jobsearch
      ?start=N&limit=25&query=<kw>&locations=India&sort=1
Response: {jobSearchResponse: {data: [ {title, companyName, locations, ...} ]}}
"""
import logging
import os
import time
from typing import Dict, List

import requests

from ..base import make_job, strip_html

logger = logging.getLogger(__name__)
SOURCE = "foundit"

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0 Safari/537.36",
    "Accept": "application/json",
    "Referer": "https://www.foundit.in/",
    "appid": "105",
    "systemid": "2323",
}

DEFAULT_TERMS = [
    "data scientist", "machine learning", "data analyst", "software engineer",
    "product manager", "business analyst", "financial analyst", "investment banking",
    "equity research", "credit analyst", "accountant", "devops",
]


def _page(term: str, start: int, limit: int) -> List[Dict]:
    try:
        r = requests.get(
            "https://www.foundit.in/middleware/jobsearch",
            headers=_HEADERS,
            params={"start": start, "sort": 1, "limit": limit, "query": term, "locations": "India"},
            timeout=20,
        )
        r.raise_for_status()
        return (r.json().get("jobSearchResponse") or {}).get("data") or []
    except Exception as e:
        logger.warning(f"[foundit] '{term}' start={start} failed: {type(e).__name__}: {e}")
        return []


def _salary(j: Dict):
    lo, hi, cur = j.get("minimumSalary"), j.get("maximumSalary"), j.get("currencyCode") or ""
    if j.get("hideSalary") or j.get("jobSalaryConfidential"):
        return None
    try:
        if lo and hi and float(lo) > 0 and float(hi) > 0:
            return f"{cur} {int(float(lo))}-{int(float(hi))}".strip()
    except (ValueError, TypeError):
        pass
    return None


def fetch() -> List[Dict]:
    terms = [t.strip() for t in os.environ.get("FOUNDIT_TERMS", "").split(",") if t.strip()] or DEFAULT_TERMS
    per_term = int(os.environ.get("FOUNDIT_PER_TERM", "75"))
    limit = 25
    out: List[Dict] = []
    for term in terms:
        for start in range(0, per_term, limit):
            rows = _page(term, start, limit)
            if not rows:
                break
            for j in rows:
                seo = j.get("seoJdUrl") or j.get("jdUrl") or ""
                url = (f"https://www.foundit.in{seo}" if seo.startswith("/") else seo) \
                    or j.get("redirectUrl") or j.get("applyUrl") or "https://www.foundit.in"
                job = make_job(
                    title=j.get("title", ""),
                    company=j.get("companyName", "") if not j.get("hideCompanyName") else "",
                    url=url,
                    source=SOURCE,
                    location=j.get("locations", "") or "India",
                    salary_range=_salary(j),
                    description=strip_html(j.get("skills", "") or ""),
                    posted=j.get("createdAt") or j.get("updatedAt"),
                    source_job_id=str(j.get("jobId") or j.get("id", "")),
                )
                if job:
                    out.append(job)
            if len(rows) < limit:
                break
            time.sleep(0.5)
    logger.info(f"[foundit] {len(out)} India jobs across {len(terms)} terms")
    return out
