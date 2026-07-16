"""
Salary stats — the CTC-TO-ASK heuristic's data layer. Runs nightly after the
scrape (daily.yml step, continue-on-error).

Parses every jobs_pool.salary_range into LPA (same magnitude heuristics as
utils.filter._extract_salary_lpa — the ONE parser, imported not copied) and
aggregates p25/median/p75 per (position, location_city), plus an all-city
rollup per position (location_city = ''). Groups with fewer than MIN_N
samples are dropped — a 3-posting "market band" is noise, not signal.

The dashboard reads the resulting salary_stats table to render "market band /
ask" context on job cards and the home CTC-benchmarks card. Everything here is
a heuristic over posted ranges (mostly aggregator postings carry salaries) —
labelled as such in the UI, never presented as ground truth.

Failsafe: any error logs and exits 0 — the run report never breaks on this.
Env: SUPABASE_URL / SUPABASE_SERVICE_KEY (same as main.py), SALARY_MIN_N (5).
"""
import logging
import os
import sys
from datetime import datetime, timezone

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s — %(message)s")
logger = logging.getLogger("salary_stats")

MIN_N = int(os.environ.get("SALARY_MIN_N", "5"))
PAGE = 1000


def _percentile(sorted_vals, q: float) -> float:
    """Linear-interpolated percentile on a pre-sorted list (no numpy needed)."""
    if not sorted_vals:
        return 0.0
    k = (len(sorted_vals) - 1) * q
    lo, hi = int(k), min(int(k) + 1, len(sorted_vals) - 1)
    return round(sorted_vals[lo] + (sorted_vals[hi] - sorted_vals[lo]) * (k - lo), 1)


def main() -> int:
    try:
        from utils.supabase_client import get_client
        from utils.filter import _extract_salary_lpa
        sb = get_client()
    except Exception as e:
        logger.error(f"no supabase client: {e}")
        return 0

    # 1) pull every priced posting (paginated; salary_range is sparse — most
    #    ATS postings carry none, aggregators do)
    groups: dict = {}   # (position, city) -> [lpa, ...]
    offset = 0
    priced = 0
    while True:
        rows = (sb.table("jobs_pool")
                  .select("position, location_city, salary_range")
                  .not_.is_("salary_range", "null")
                  .range(offset, offset + PAGE - 1).execute().data) or []
        if not rows:
            break
        for r in rows:
            lpa = _extract_salary_lpa(r.get("salary_range") or "")
            if lpa <= 0 or lpa > 400:   # >4Cr midpoint → parse artifact, drop
                continue
            priced += 1
            pos = (r.get("position") or "").strip()
            city = (r.get("location_city") or "").strip()
            if not pos:
                continue
            groups.setdefault((pos, city), []).append(lpa)
            groups.setdefault((pos, ""), []).append(lpa)   # all-city rollup
        offset += PAGE
    logger.info(f"priced postings parsed: {priced}; raw groups: {len(groups)}")

    # 2) aggregate → rows (drop thin groups)
    now = datetime.now(timezone.utc).isoformat()
    upserts = []
    for (pos, city), vals in groups.items():
        if len(vals) < MIN_N:
            continue
        vals.sort()
        upserts.append({
            "position": pos,
            "location_city": city,
            "n": len(vals),
            "p25": _percentile(vals, 0.25),
            "p50": _percentile(vals, 0.50),
            "p75": _percentile(vals, 0.75),
            "updated_at": now,
        })
    logger.info(f"salary_stats groups kept (n>={MIN_N}): {len(upserts)}")
    if not upserts:
        return 0

    for i in range(0, len(upserts), 500):
        try:
            sb.table("salary_stats").upsert(
                upserts[i:i + 500], on_conflict="position,location_city").execute()
        except Exception as e:
            logger.error(f"salary_stats upsert batch failed: {e}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:  # flywheel must NEVER fail the pipeline
        logger.error(f"salary stats failed (non-fatal): {e}")
        sys.exit(0)
