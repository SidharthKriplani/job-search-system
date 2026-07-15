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
    # Tech
    "data scientist", "machine learning engineer", "data engineer",
    "data analyst", "software engineer", "backend developer", "product manager",
    "business analyst", "devops engineer",
    # Finance (the market this product serves + India KPO/GCC roles)
    "financial analyst", "investment banking", "equity research",
    "credit analyst", "risk analyst", "fp&a", "quantitative analyst",
]


def _s(v) -> str:
    """pandas cells are float NaN when missing; str(NaN) == 'nan' leaked as a
    literal company/title. Coerce NaN (and None) to empty string."""
    if v is None or v != v:   # NaN != NaN
        return ""
    return str(v).strip()


def _salary(row):
    # min/max come from a pandas row as float NaN when absent. NaN is truthy, so
    # `if lo and hi` passed and int(NaN) raised ValueError — which escaped the
    # row loop (outside the per-term try) and zeroed the ENTIRE jobspy source.
    lo, hi = row.get("min_amount"), row.get("max_amount")
    cur = row.get("currency") or ""
    try:
        if lo is not None and hi is not None and lo == lo and hi == hi:  # NaN != NaN
            return f"{cur} {int(lo)}–{int(hi)}".strip()
    except (ValueError, TypeError):
        pass
    return None


def fetch() -> List[Dict]:
    try:
        from jobspy import scrape_jobs
    except ImportError:
        logger.warning("[jobspy] python-jobspy not installed — skipping")
        return []

    # indeed + linkedin both return ~80 India jobs/term (verified). glassdoor/
    # google/naukri are broken or captcha-walled — don't add them.
    sites    = [s.strip() for s in os.environ.get("JOBSPY_SITES", "indeed,linkedin").split(",") if s.strip()]
    terms    = [t.strip() for t in os.environ.get("JOBSPY_TERMS", "").split(",") if t.strip()] or DEFAULT_TERMS
    location = os.environ.get("JOBSPY_LOCATION", "India")
    country  = os.environ.get("JOBSPY_COUNTRY", "India")
    per_term = int(os.environ.get("JOBSPY_PER_TERM", "60"))
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
                title=_s(row.get("title")),
                company=_s(row.get("company")),
                url=_s(row.get("job_url")),
                source=_s(row.get("site")) or "indeed",
                location=_s(row.get("location")) or location,
                salary_range=_salary(row),
                description=strip_html(_s(row.get("description"))),
                posted=_s(row.get("date_posted")),
                source_job_id=_s(row.get("id")) or _s(row.get("job_url")),
                job_type=_s(row.get("job_type")),
                remote=bool(row.get("is_remote")) if row.get("is_remote") == row.get("is_remote") else False,
            )
            if job:
                out.append(job)

    logger.info(f"[jobspy] {len(out)} India jobs across {len(terms)} terms")
    return out
