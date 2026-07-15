"""
Supabase Client
----------------
Centralised Supabase access for the scraper backend.
Uses the SERVICE ROLE key (bypasses RLS) so scrapers can write
to any user's job_feed rows.

All public frontend access uses the ANON key with RLS enforced.
"""

import os
import logging
from typing import List, Dict, Optional, Any
from supabase import create_client, Client

logger = logging.getLogger(__name__)

_client: Optional[Client] = None


def get_client() -> Client:
    """Return a cached Supabase service-role client."""
    global _client
    if _client is None:
        url = os.environ["SUPABASE_URL"]
        key = os.environ["SUPABASE_SERVICE_KEY"]  # SERVICE key, not anon
        _client = create_client(url, key)
    return _client


# ─── User profile helpers ────────────────────────────────────────────────────

def get_active_users() -> List[Dict]:
    """Return all user_profiles where is_active = true."""
    sb = get_client()
    result = sb.table("user_profiles").select("*").eq("is_active", True).execute()
    return result.data or []


def get_gmail_token(user_id: str) -> Optional[Dict]:
    """Return gmail_tokens row for a user, or None."""
    sb = get_client()
    result = sb.table("gmail_tokens").select("*").eq("user_id", user_id).maybe_single().execute()
    return result.data


def update_gmail_token(user_id: str, access_token: str, token_expiry: Optional[str]) -> None:
    sb = get_client()
    sb.table("gmail_tokens").update({
        "access_token": access_token,
        "token_expiry": token_expiry,
    }).eq("user_id", user_id).execute()


# ─── Job feed helpers ────────────────────────────────────────────────────────

# Exact set of writable columns in job_feed. Any key not in here is dropped
# before upsert — an unknown column makes the WHOLE insert fail (Supabase
# rejects it), which previously returned 0 silently and looked like "no jobs".
JOB_FEED_COLUMNS = {
    "user_id", "job_title", "company", "location", "salary_range", "job_url",
    "description_snippet", "posted_date", "source", "source_job_id", "job_type",
    "seniority", "is_new", "is_applied", "is_saved",
    "is_dismissed", "match_score", "match_reasons",
}
# NOTE: "experience_required" was removed — there is NO such column in job_feed
# (see supabase/schema.sql). Whitelisting a non-existent column is a landmine:
# if any connector ever emits it, Supabase rejects the ENTIRE batch and the rows
# are silently lost.


def upsert_jobs(user_id: str, jobs: List[Dict]) -> int:
    """
    Upsert a batch of jobs for a user.
    Unique constraint: (user_id, source, source_job_id)
    Returns number of new rows inserted.
    """
    if not jobs:
        return 0

    import hashlib
    sb = get_client()
    rows = []
    for job in jobs:
        # Keep only real job_feed columns — stray keys (e.g. a "remote" flag)
        # would make Supabase reject the entire batch.
        row = {k: v for k, v in job.items() if k in JOB_FEED_COLUMNS}
        row["user_id"] = user_id
        if not row.get("source_job_id"):
            row["source_job_id"] = hashlib.md5(row.get("job_url", "").encode()).hexdigest()[:20]
        rows.append(row)

    # Upsert in batches of 100
    total_new = 0
    for i in range(0, len(rows), 100):
        batch = rows[i:i+100]
        try:
            # ignore_duplicates=False → on conflict, UPDATE the row's columns
            # (match_score, match_reasons, title, …). Only payload columns are
            # touched, so is_applied / is_saved / is_dismissed are preserved.
            # This lets a changed profile re-score existing jobs.
            result = sb.table("job_feed").upsert(
                batch,
                on_conflict="user_id,source,source_job_id",
                ignore_duplicates=False,
            ).execute()
            total_new += len(result.data or [])
        except Exception as e:
            # Loud, not silent — a failed insert is the difference between
            # "jobs on screen" and a green-but-empty run.
            logger.error(f"[Supabase] upsert_jobs batch FAILED ({len(batch)} rows lost): {e}")

    return total_new


def get_seen_job_ids(user_id: str, source: str) -> set:
    """
    Return set of source_job_ids already in the DB for this user+source.
    Used for pre-dedup before upsert.
    """
    sb = get_client()
    result = sb.table("job_feed") \
        .select("source_job_id") \
        .eq("user_id", user_id) \
        .eq("source", source) \
        .execute()
    return {row["source_job_id"] for row in (result.data or [])}


def get_user_feed_rows(user_id: str) -> List[Dict]:
    """Return the user's stored job_feed rows (fields needed to re-filter + prune)."""
    sb = get_client()
    # Paginated: PostgREST caps a single select at 1000 rows by default, so the
    # old un-ranged select silently re-synced only the first 1000 rows of a
    # large feed. Page with .range() until a short page.
    out: List[Dict] = []
    cols = ("id, job_title, company, location, salary_range, job_url, "
            "description_snippet, posted_date, source, source_job_id, seniority, "
            "job_type, is_applied, is_saved")
    page = 1000
    try:
        start = 0
        while True:
            rows = sb.table("job_feed").select(cols) \
                .eq("user_id", user_id) \
                .order("id") \
                .range(start, start + page - 1) \
                .execute().data or []
            out.extend(rows)
            if len(rows) < page:
                break
            start += page
        return out
    except Exception as e:
        logger.error(f"[Supabase] get_user_feed_rows failed (got {len(out)}): {e}")
        return out


def delete_jobs(job_ids: List[str], user_id: Optional[str] = None) -> int:
    """Delete job_feed rows by id (batched).

    Pass `user_id` to scope the delete to that user — defense-in-depth so a stray
    id can never delete another user's rows (the service-role key bypasses RLS).
    """
    if not job_ids:
        return 0
    sb = get_client()
    deleted = 0
    for i in range(0, len(job_ids), 100):
        batch = job_ids[i:i+100]
        try:
            q = sb.table("job_feed").delete().in_("id", batch)
            if user_id:
                q = q.eq("user_id", user_id)
            q.execute()
            deleted += len(batch)
        except Exception as e:
            logger.error(f"[Supabase] delete_jobs failed: {e}")
    return deleted


def get_existing_job_keys(user_id: str) -> set:
    """
    Return the set of (source, source_job_id) tuples already stored for a user,
    across ALL sources. Used to decide which scraped jobs are genuinely *new*
    so the daily digest only emails new jobs (not the whole feed every day).
    """
    sb = get_client()
    try:
        result = sb.table("job_feed") \
            .select("source, source_job_id") \
            .eq("user_id", user_id) \
            .execute()
    except Exception as e:
        logger.error(f"[Supabase] get_existing_job_keys failed: {e}")
        return set()
    return {(row.get("source"), row.get("source_job_id")) for row in (result.data or [])}


def age_out_new_flags(user_id: str, hours: int = 24) -> int:
    """
    Reset is_new=false on feed rows older than `hours`. Without this the
    dashboard's "New Today" stat counts every un-applied job EVER (is_new was
    write-once TRUE). Runs at the start of each user's daily pass, so "new"
    means "arrived in the last day", matching what the stat claims.
    """
    from datetime import datetime, timedelta, timezone
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
    sb = get_client()
    # Batched: one big UPDATE hit Supabase's statement timeout (57014) on a
    # large feed. Select matching ids in pages, update in chunks of 500.
    total = 0
    try:
        while True:
            rows = sb.table("job_feed").select("id") \
                .eq("user_id", user_id) \
                .eq("is_new", True) \
                .lt("created_at", cutoff) \
                .limit(500).execute().data or []
            if not rows:
                break
            ids = [r["id"] for r in rows]
            sb.table("job_feed").update({"is_new": False}).in_("id", ids).execute()
            total += len(ids)
            if len(rows) < 500:
                break
        return total
    except Exception as e:
        logger.error(f"[Supabase] age_out_new_flags failed (after {total}): {e}")
        return total


# Sources whose pool listing is COMPLETE for each company board (deterministic
# ATS APIs). Rotating/partial sources (jobspy, aggregators, gmail_*) must never
# be cleaned by pool-absence — a job can be live yet absent from their sample.
DETERMINISTIC_SOURCES = {"greenhouse", "lever", "ashby", "workday", "oracle", "smartrecruiters"}


def cleanup_closed_jobs(user_id: str, pool_keys: set, pool_companies: set) -> int:
    """
    Remove stored feed rows whose posting has CLOSED at the source.

    A row is deleted only when ALL of:
      - its source is a deterministic ATS API (complete board listings),
      - its (source, source_job_id) is absent from the current pool,
      - its company DID appear in the pool for that source (board fetch
        succeeded — a failed/missing board never triggers deletion),
      - the user hasn't saved or applied to it.
    This is what keeps the feed free of dead links without ever deleting on a
    transient fetch failure.
    """
    sb = get_client()
    doomed: List[str] = []
    page, start = 1000, 0
    try:
        while True:
            rows = sb.table("job_feed") \
                .select("id, source, source_job_id, company, is_saved, is_applied") \
                .eq("user_id", user_id) \
                .order("id") \
                .range(start, start + page - 1) \
                .execute().data or []
            for r in rows:
                src = r.get("source")
                if src not in DETERMINISTIC_SOURCES:
                    continue
                if r.get("is_saved") or r.get("is_applied"):
                    continue
                if (src, str(r.get("source_job_id"))) in pool_keys:
                    continue
                if (src, (r.get("company") or "").strip().lower()) not in pool_companies:
                    continue  # board absent/failed this run — don't judge
                doomed.append(r["id"])
            if len(rows) < page:
                break
            start += page
        if doomed:
            return delete_jobs(doomed, user_id=user_id)
        return 0
    except Exception as e:
        logger.error(f"[Supabase] cleanup_closed_jobs failed: {e}")
        return 0


# ─── Scraper health helpers ──────────────────────────────────────────────────

def update_scraper_health(
    source: str,
    job_count: int,
    error: Optional[str] = None
) -> None:
    """Log scraper health after each run."""
    from datetime import datetime, timezone
    sb = get_client()
    now = datetime.now(timezone.utc).isoformat()

    if error:
        # Read current consecutive_failures
        current = sb.table("scraper_health").select("consecutive_failures").eq("source", source).maybe_single().execute()
        prev_failures = (current.data or {}).get("consecutive_failures", 0)
        status = "warning" if prev_failures < 3 else "error"

        sb.table("scraper_health").upsert({
            "source":               source,
            "last_run_at":          now,
            "consecutive_failures": prev_failures + 1,
            "last_error":           error[:500],
            "status":               status,
            "updated_at":           now,
        }, on_conflict="source").execute()
    else:
        sb.table("scraper_health").upsert({
            "source":               source,
            "last_run_at":          now,
            "last_success_at":      now,
            "last_job_count":       job_count,
            "consecutive_failures": 0,
            "last_error":           None,
            "status":               "ok",
            "updated_at":           now,
        }, on_conflict="source").execute()


# ─── Application reminders ───────────────────────────────────────────────────

def get_follow_up_due(user_id: str) -> List[Dict]:
    """Return applications where follow_up_date <= today and stage is active."""
    from datetime import date
    sb = get_client()
    today = date.today().isoformat()
    result = sb.table("applications") \
        .select("*") \
        .eq("user_id", user_id) \
        .lte("follow_up_date", today) \
        .not_.in_("stage", ["Rejected", "Withdrawn", "Ghosted", "Offer Accepted"]) \
        .execute()
    return result.data or []


def get_stale_applications(user_id: str, days: int = 7) -> List[Dict]:
    """Return applications not updated in `days` days and still active."""
    from datetime import date, timedelta
    sb = get_client()
    cutoff = (date.today() - timedelta(days=days)).isoformat()
    result = sb.table("applications") \
        .select("*") \
        .eq("user_id", user_id) \
        .lt("date_stage_updated", cutoff) \
        .not_.in_("stage", ["Rejected", "Withdrawn", "Ghosted", "Offer Accepted", "Not Applied"]) \
        .execute()
    return result.data or []
