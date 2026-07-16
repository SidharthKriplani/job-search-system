"""
Kula ATS — India-startup career sites hosted at careers.kula.ai/{slug}
(Cashfree, Plum, CleverTap, ...). No public JSON API, BUT the jobs are
server-rendered into the page's Next.js RSC flight payload
(self.__next_f.push chunks), so one GET + payload parse yields clean JSON:

  "jobs": [{id, title, listed, kind, ats_job: {job_description, workplace,
            employment_type, ats_department:{name}, offices:[{location}]}}]

Job page: https://careers.kula.ai/{slug}/{id}

This parses an embedded payload, not the DOM — stabler than HTML scraping but
softer than a real API: if Kula changes their serialization, the connector
degrades to 0 (failsafe) and the link canary / SOURCE_SUMMARY will show it.

Config:
  KULA_MAX_PER_COMPANY  default 200
"""
import json
import logging
import os
import re
from typing import Dict, List

import requests

from ..base import HEADERS, make_job

logger = logging.getLogger(__name__)
SOURCE = "kula"
_PUSH = re.compile(r'self\.__next_f\.push\(\[1,\s*"((?:[^"\\]|\\.)*)"\]\)')


def _flight_jobs(slug: str):
    """GET the careers page and pull the jobs array out of the RSC payload."""
    r = requests.get(f"https://careers.kula.ai/{slug}",
                     headers={**HEADERS, "Accept": "text/html"}, timeout=20)
    r.raise_for_status()
    blob = "".join(_PUSH.findall(r.text)).encode().decode("unicode_escape")
    i = blob.find('"jobs":[')
    if i < 0:
        return []
    arr, _ = json.JSONDecoder().raw_decode(blob[i + len('"jobs":'):])
    return arr if isinstance(arr, list) else []


def fetch_company(slug: str, display: str, cap: int = 0) -> List[Dict]:
    cap = cap or int(os.environ.get("KULA_MAX_PER_COMPANY", "200"))
    try:
        raw = _flight_jobs(slug)
    except Exception as e:
        logger.warning(f"[kula] {slug} failed: {type(e).__name__}: {e}")
        return []
    out: List[Dict] = []
    for j in raw[:cap]:
        if j.get("listed") is False:
            continue
        aj = j.get("ats_job") or {}
        offices = aj.get("offices") or []
        loc = (offices[0].get("location") or "") if offices else ""
        jid = j.get("id", "")
        job = make_job(
            title=j.get("title", ""),
            company=display,
            url=f"https://careers.kula.ai/{slug}/{jid}" if jid else "",
            source=SOURCE,
            location=loc,
            description=aj.get("job_description", ""),
            source_job_id=str(jid),
            job_type=aj.get("employment_type"),
            remote=(aj.get("workplace") == "remote"),
        )
        if job:
            out.append(job)
    return out


def fetch() -> List[Dict]:
    from ..registry import KULA
    jobs: List[Dict] = []
    for slug, display in KULA:
        try:
            jobs.extend(fetch_company(slug, display))
        except Exception as e:
            logger.warning(f"[kula] {slug} failed: {e}")
    return jobs
