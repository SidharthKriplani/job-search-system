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

def upsert_jobs(user_id: str, jobs: List[Dict]) -> int:
    """
    Upsert a batch of jobs for a user.
    Unique constraint: (user_id, source, source_job_id)
    Returns number of new rows inserted.
    """
    if not jobs:
        return 0

    sb = get_client()
    rows = []
    for job in jobs:
        row = {**job, "user_id": user_id}
        # Ensure source_job_id is set (fallback to URL hash)
        if not row.get("source_job_id"):
            import hashlib
            row["source_job_id"] = hashlib.md5(row.get("job_url", "").encode()).hexdigest()[:20]
        rows.append(row)

    # Upsert in batches of 100
    total_new = 0
    for i in range(0, len(rows), 100):
        batch = rows[i:i+100]
        try:
            result = sb.table("job_feed").upsert(
                batch,
                on_conflict="user_id,source,source_job_id",
                ignore_duplicates=True,
            ).execute()
            total_new += len(result.data or [])
        except Exception as e:
            logger.error(f"[Supabase] upsert_jobs batch failed: {e}")

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
