"""
Deduplication for the ingestion pool.

Two-pass, matching the rest of the system's contract:
  1. by job_url (primary key)
  2. by (normalized title, normalized company)
The same role posted on a company's ATS and an aggregator collapses to one.
"""
import re
from typing import Dict, List, Tuple


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9 ]", "", (s or "").lower()).strip()


def deduplicate(jobs: List[Dict]) -> List[Dict]:
    seen_urls = set()
    seen_keys: set[Tuple[str, str]] = set()
    out: List[Dict] = []
    for j in jobs:
        url = (j.get("job_url") or "").strip()
        key = (_norm(j.get("job_title", "")), _norm(j.get("company", "")))
        if url and url in seen_urls:
            continue
        if key != ("", "") and key in seen_keys:
            continue
        if url:
            seen_urls.add(url)
        if key != ("", ""):
            seen_keys.add(key)
        out.append(j)
    return out
