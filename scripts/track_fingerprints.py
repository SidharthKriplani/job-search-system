"""
Fingerprint tracker — the repost/lifetime FLYWHEEL. Runs nightly after the
scrape (daily.yml step, continue-on-error).

For every job currently in jobs_pool, compute
    fingerprint = md5(canonical_company | normalized_title | location_city)
and reconcile against job_fingerprints:

  - new fingerprint            → insert (first_seen)
  - seen, small gap (<GAP)     → refresh last_seen, times_seen+1, open_days+gap
  - seen, gap >= GAP_DAYS      → REPOST: reappearances+1, last_gap_days=gap

Repost rate per (company, position) and posting lifetimes both read from this
table later (home dashboard, "Reposted 3×" card chip). Failsafe: any error
logs and exits 0 — the run report never breaks on the flywheel.

Env: SUPABASE_URL / SUPABASE_SERVICE_KEY (same as main.py), FP_GAP_DAYS (7).
"""
import hashlib
import logging
import os
import re
import sys
from datetime import datetime, timezone

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s — %(message)s")
logger = logging.getLogger("fingerprints")

GAP_DAYS = int(os.environ.get("FP_GAP_DAYS", "7"))
PAGE = 1000


def _norm_title(t: str) -> str:
    """Aggressive title normalization: casefold, strip req-ids/levels/punct."""
    s = (t or "").lower()
    s = re.sub(r"\(.*?\)", " ", s)                      # (remote), (2 openings)
    s = re.sub(r"[^a-z0-9+#/ ]", " ", s)
    s = re.sub(r"\b(?:i{1,3}|iv|v|1|2|3|4|5)\b\s*$", "", s.strip())  # trailing level
    return re.sub(r"\s+", " ", s).strip()


def _fp(company: str, title: str, city: str) -> str:
    key = f"{(company or '').lower()}|{_norm_title(title)}|{(city or '').lower()}"
    return hashlib.md5(key.encode()).hexdigest()


def main() -> int:
    try:
        from utils.supabase_client import get_client
        sb = get_client()
    except Exception as e:
        logger.error(f"no supabase client: {e}")
        return 0

    now = datetime.now(timezone.utc)

    # 1) current pool → fingerprint map (dedupe: keep any one representative)
    current = {}
    offset = 0
    while True:
        rows = (sb.table("jobs_pool")
                  .select("company, job_title, location_city, position")
                  .range(offset, offset + PAGE - 1).execute().data) or []
        if not rows:
            break
        for r in rows:
            f = _fp(r.get("company"), r.get("job_title"), r.get("location_city"))
            current.setdefault(f, r)
        offset += PAGE
    logger.info(f"pool fingerprints: {len(current)}")
    if not current:
        return 0

    # 2) existing fingerprint rows (paginated)
    existing = {}
    offset = 0
    while True:
        rows = (sb.table("job_fingerprints")
                  .select("fingerprint, last_seen_at, times_seen, reappearances, open_days")
                  .range(offset, offset + PAGE - 1).execute().data) or []
        if not rows:
            break
        for r in rows:
            existing[r["fingerprint"]] = r
        offset += PAGE

    # 3) reconcile
    upserts = []
    reposts = 0
    for f, r in current.items():
        base = {
            "fingerprint": f,
            "company": (r.get("company") or "")[:200],
            "title_norm": _norm_title(r.get("job_title"))[:300],
            "location_city": r.get("location_city"),
            "position": r.get("position"),
            "last_seen_at": now.isoformat(),
        }
        ex = existing.get(f)
        if not ex:
            upserts.append(base)  # defaults: times_seen 1, reappearances 0
            continue
        try:
            last = datetime.fromisoformat(str(ex["last_seen_at"]).replace("Z", "+00:00"))
            gap = (now - last).days
        except Exception:
            gap = 0
        base["times_seen"] = (ex.get("times_seen") or 1) + 1
        if gap >= GAP_DAYS:
            base["reappearances"] = (ex.get("reappearances") or 0) + 1
            base["last_gap_days"] = gap
            reposts += 1
        else:
            base["reappearances"] = ex.get("reappearances") or 0
            base["open_days"] = (ex.get("open_days") or 0) + max(gap, 1)
        upserts.append(base)

    for i in range(0, len(upserts), 500):
        try:
            sb.table("job_fingerprints").upsert(upserts[i:i + 500], on_conflict="fingerprint").execute()
        except Exception as e:
            logger.error(f"fingerprint upsert batch failed: {e}")

    logger.info(f"fingerprints reconciled: {len(upserts)} upserted, {reposts} reposts detected tonight")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:  # flywheel must NEVER fail the pipeline
        logger.error(f"fingerprint tracker failed (non-fatal): {e}")
        sys.exit(0)
