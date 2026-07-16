"""
Shared helpers for all ingestion connectors.

Design rules (mirrors the rest of the system):
  - A connector must NEVER raise. On any error it logs and returns [].
  - Every connector returns a list of dicts in ONE normalized schema, with
    every key always present (empty string / None when unknown). This matches
    the existing job_feed contract so utils.filter and supabase_client.upsert_jobs
    work unchanged.
"""

import logging
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import requests

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 15
HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; JobSearchBot/1.0)",
    "Accept": "application/json",
}

# Normalized job schema — keys match what utils/filter.py and upsert_jobs expect.
# Every key here MUST be a real column in the job_feed table.
JOB_KEYS = (
    "job_title", "company", "location", "salary_range", "job_url",
    "description_snippet", "posted_date", "source", "source_job_id",
    "job_type", "seniority",
)


def http_json(
    url: str,
    method: str = "GET",
    json_body: Optional[dict] = None,
    params: Optional[dict] = None,
    timeout: int = DEFAULT_TIMEOUT,
) -> Optional[Any]:
    """GET/POST a JSON endpoint. Returns parsed JSON or None on any failure."""
    try:
        if method == "POST":
            resp = requests.post(url, json=json_body, headers=HEADERS, params=params, timeout=timeout)
        else:
            resp = requests.get(url, headers=HEADERS, params=params, timeout=timeout)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        logger.warning(f"[http] {url[:70]} failed: {type(e).__name__}: {e}")
        return None


def strip_html(text: Optional[str], limit: int = 280) -> str:
    if not text:
        return ""
    # 280 chars is enough for keyword/JD matching; keeping full JDs bloated every
    # per-user job_feed row (storage + egress). The link goes to the full posting.
    return re.sub(r"<[^>]+>", " ", text).strip()[:limit]


def to_iso_date(value: Any) -> Optional[str]:
    """Best-effort parse of various date formats to YYYY-MM-DD. None on failure."""
    if value is None or value == "":
        return None
    try:
        # epoch seconds or milliseconds
        if isinstance(value, (int, float)) or (isinstance(value, str) and value.isdigit()):
            ts = float(value)
            if ts > 1e12:  # milliseconds
                ts /= 1000.0
            return datetime.fromtimestamp(ts, tz=timezone.utc).date().isoformat()
        # ISO-ish string
        s = str(value).replace("Z", "+00:00")
        return datetime.fromisoformat(s).date().isoformat()
    except Exception:
        return None


_SENIORITY_PATTERNS = [
    ("director", "director"), ("vice president", "vp"), (" vp ", "vp"),
    ("head of", "head"), ("principal", "principal"), ("lead", "lead"),
    ("manager", "manager"), ("senior", "senior"), ("sr.", "senior"),
    ("junior", "junior"), ("intern", "intern"), ("associate", "associate"),
]


def infer_seniority(title: str) -> Optional[str]:
    t = f" {title.lower()} "
    for needle, label in _SENIORITY_PATTERNS:
        if needle in t:
            return label
    return None


def normalize_job_type(value: Optional[str]) -> str:
    if not value:
        return "full_time"
    v = str(value).lower()
    if "full" in v:
        return "full_time"
    if "part" in v:
        return "part_time"
    if "contract" in v or "temp" in v:
        return "contract"
    if "intern" in v:
        return "internship"
    return "full_time"


def make_job(
    *,
    title: str,
    company: str,
    url: str,
    source: str,
    location: str = "",
    salary_range: Optional[str] = None,
    description: str = "",
    posted: Any = None,
    source_job_id: str = "",
    job_type: Optional[str] = None,
    remote: bool = False,
) -> Optional[Dict]:
    """Build a normalized job dict. Returns None if title or url is missing."""
    title = (title or "").strip()
    url = (url or "").strip()
    if not title or not url:
        return None

    loc = (location or "").strip()
    if remote and "remote" not in loc.lower():
        loc = (loc + " · Remote").strip(" ·") if loc else "Remote"

    from .normalize import canonical_company
    return {
        "job_title":           title,
        "company":             canonical_company(company or ""),
        "location":            loc,
        "salary_range":        salary_range or None,
        "job_url":             url,
        "description_snippet": strip_html(description),
        "posted_date":         to_iso_date(posted),
        "source":              source,
        "source_job_id":       str(source_job_id) if source_job_id else "",
        "job_type":            normalize_job_type(job_type),
        "seniority":           infer_seniority(title),
        # NOTE: do NOT add keys that aren't columns in the job_feed table — the
        # whole dict is sent straight to Supabase upsert, and an unknown column
        # makes the insert fail (silently, returning 0). `remote` is folded into
        # `location` above instead of being its own field.
    }
