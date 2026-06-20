"""
Ingestion engine — the durable data foundation.

Replaces the fragile HTML portal scrapers. Every source here is either an
official ATS JSON API (Greenhouse / Lever / Ashby / Workday) or an official
aggregator API (Remotive / Arbeitnow / Adzuna). No DOM scraping, no bot
detection, no Terms-of-Service grey zone — these endpoints are meant to be
called programmatically and do not break when a site redesigns.

Public surface:
    from ingest import collect_jobs
    jobs = collect_jobs()          # -> List[normalized job dict]
"""

from .run import collect_jobs, SOURCE_SUMMARY  # noqa: F401
