"""
Zoho Recruit — hosted careers pages. The page embeds the FULL job list as clean
JSON in a hidden input (id="jobs"), including complete JDs and open dates — no
per-job N+1 needed:
  GET https://{host}/jobs/Careers
  → <input type="hidden" value="[{&#34;Posting_Title&#34;:...}]" id="jobs">
Fields: Posting_Title, Job_Opening_Name, City, State, Country, Job_Type,
        Work_Experience, Date_Opened (ISO), Remote_Job, Job_Description, id.

Job page: https://{host}/jobs/Careers/{id} (server-rendered; verified 2026-07-17).
Indian tenants live on .zohorecruit.in, others on .zohorecruit.com — the
registry stores the FULL host so both work. A dead tenant serves a small
"does not exist" shell with no jobs input → parses to [] naturally.

Registry entries are (host, display) in registry.ZOHO_RECRUIT. Failsafe: any
error returns [] and the run continues.

Config:
  ZOHO_MAX_PER_COMPANY  default 200
"""
import json
import logging
import os
import re
from html import unescape
from typing import Dict, List

import requests

from ..base import HEADERS, make_job

logger = logging.getLogger(__name__)
SOURCE = "zoho_recruit"

_JOBS_INPUT = re.compile(r'<input type="hidden" value="([^"]*)" id="jobs">')


def fetch_site(host: str, display: str, cap: int = 0) -> List[Dict]:
    cap = cap or int(os.environ.get("ZOHO_MAX_PER_COMPANY", "200"))
    try:
        r = requests.get(f"https://{host}/jobs/Careers",
                         headers={**HEADERS, "Accept": "text/html"}, timeout=25)
        r.raise_for_status()
    except Exception as e:
        logger.warning(f"[zoho_recruit] {host} failed: {type(e).__name__}")
        return []
    m = _JOBS_INPUT.search(r.text)
    if not m:
        return []  # dead tenant or template change — failsafe empty
    try:
        rows = json.loads(unescape(m.group(1)))
    except (json.JSONDecodeError, ValueError):
        logger.warning(f"[zoho_recruit] {host}: jobs JSON parse failed")
        return []

    out: List[Dict] = []
    for j in rows[:cap]:
        if j.get("Publish") is False or j.get("Is_Locked"):
            continue
        jid = str(j.get("id", ""))
        loc = ", ".join(p for p in (j.get("City"), j.get("State"), j.get("Country")) if p)
        job = make_job(
            title=j.get("Posting_Title") or j.get("Job_Opening_Name") or "",
            company=display,
            url=f"https://{host}/jobs/Careers/{jid}" if jid else "",
            source=SOURCE,
            location=loc,
            description=j.get("Job_Description") or "",
            posted=j.get("Date_Opened"),
            source_job_id=jid,
            job_type=j.get("Job_Type"),
            remote=bool(j.get("Remote_Job")),
        )
        if job:
            out.append(job)
    return out


def fetch() -> List[Dict]:
    from ..registry import ZOHO_RECRUIT
    jobs: List[Dict] = []
    for host, display in ZOHO_RECRUIT:
        try:
            jobs.extend(fetch_site(host, display))
        except Exception as e:
            logger.warning(f"[zoho_recruit] {host} failed: {e}")
    return jobs
