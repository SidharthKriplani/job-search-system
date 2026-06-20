"""
JobSpy — all-India job coverage, any field.

Wraps the maintained `python-jobspy` library (github.com/speedyapply/JobSpy),
which scrapes Indeed / Naukri / LinkedIn / Glassdoor / Google across 60+
countries. We use it as the broad India engine: it returns general jobs (sales,
engineering, ops, marketing, finance — everything), not a curated company list.

This IS scraping, but via a community-maintained library that handles the
anti-bot work — far more durable than hand-rolled scrapers. It's fully failsafe:
any error (including an IP block on the runner) returns [] and the run continues.

Config (env, all optional):
  JOBSPY_SITES     default "indeed"          (comma list: indeed,naukri,google)
  JOBSPY_TERMS     default broad cross-sector terms
  JOBSPY_LOCATION  default "India"
  JOBSPY_COUNTRY   default "India"           (Indeed country)
  JOBSPY_PER_TERM  default 25                (results per term)
  JOBSPY_HOURS_OLD default 168               (last 7 days)
"""
import logging
import os
from typing import Dict, List

from ..base import make_job, strip_html

logger = logging.getLogger(__name__)

DEFAULT_TERMS = [
    "manager", "engineer", "analyst", "executive", "developer",
    "sales", "marketing", "operations", "consultant", "associate",
]


def _salary(row) -> str:
    lo, hi = row.get("min_amount"), row.get("max_amount")
    cur = row.get("currency") or ""
    if lo and hi:
        return f"{cur} {int(lo)}–{int(hi)}".strip()
    return None


def fetch() -> List[Dict]:
    try:
        from jobspy import scrape_jobs
    except ImportError:
        logger.warning("[jobspy] python-jobspy not installed — skipping")
        return []

    sites    = [s.strip() for s in os.environ.get("JOBSPY_SITES", "indeed").split(",") if s.strip()]
    terms    = [t.strip() for t in os.environ.get("JOBSPY_TERMS", "").split(",") if t.strip()] or DEFAULT_TERMS
    location = os.environ.get("JOBSPY_LOCATION", "India")
    country  = os.environ.get("JOBSPY_COUNTRY", "India")
    per_term = int(os.environ.get("JOBSPY_PER_TERM", "25"))
    hours    = int(os.environ.get("JOBSPY_HOURS_OLD", "168"))

    out: List[Dict] = []
    for term in terms:
        try:
            df = scrape_jobs(
                site_name=sites,
                search_term=term,
                location=location,
                country_indeed=country,
                results_wanted=per_term,
                hours_old=hours,
                description_format="markdown",
                verbose=0,
            )
        except Exception as e:
            logger.warning(f"[jobspy] term '{term}' failed: {type(e).__name__}: {e}")
            continue

        if df is None or len(df) == 0:
            continue

        for _, r in df.iterrows():
            row = r.to_dict()
            job = make_job(
                title=str(row.get("title") or ""),
                company=str(row.get("company") or ""),
                url=str(row.get("job_url") or ""),
                source=str(row.get("site") or "indeed"),
                location=str(row.get("location") or location),
                salary_range=_salary(row),
                description=strip_html(str(row.get("description") or "")),
                posted=str(row.get("date_posted") or ""),
                source_job_id=str(row.get("id") or row.get("job_url") or ""),
                job_type=str(row.get("job_type") or ""),
                remote=bool(row.get("is_remote")),
            )
            if job:
                out.append(job)

    logger.info(f"[jobspy] {len(out)} India jobs across {len(terms)} terms")
    return out
