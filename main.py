"""
Job Search System — Main Runner
--------------------------------
Runs once daily via GitHub Actions.
For each active user:
  1. Fetches their profile from Supabase
  2. Runs all scrapers in parallel (with failsafes)
  3. Filters and scores jobs against their profile
  4. Upserts new jobs to Supabase
  5. Sends daily email digest
  6. Sends follow-up reminders
  7. Updates scraper health

Environment variables required (GitHub Actions secrets):
  SUPABASE_URL           — your Supabase project URL
  SUPABASE_SERVICE_KEY   — service role key (bypasses RLS)
  GOOGLE_CLIENT_ID       — OAuth client ID for Gmail
  GOOGLE_CLIENT_SECRET   — OAuth client secret
  RESEND_API_KEY         — Resend API key for emails
  NEXT_PUBLIC_APP_URL    — your Vercel app URL (for email links)
"""

import os
import logging
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Callable, Tuple
from datetime import datetime, timezone

# ── Ingestion engine (durable data foundation) ─────────────────────────────────
# ATS source APIs (Greenhouse / Lever / Ashby) + official aggregators. No scraping.
from ingest import collect_jobs, SOURCE_SUMMARY

# ── Gmail (per-user, consent-based; the only path for Naukri/LinkedIn) ──────────
from scrapers import gmail_parser

# NOTE: the legacy HTML portal scrapers (foundit, shine, timesjobs, bayt,
# gulftalent, naukrigulf, instahyre, cutshort, ambitionbox, iimjobs) are
# deliberately no longer in the pipeline — they were fragile and broke on any
# site redesign. The ingest engine replaces them with stable JSON APIs.

# ── Utils ─────────────────────────────────────────────────────────────────────
from utils import supabase_client as sb
from utils import embeddings
from utils.filter import filter_and_score, deduplicate_across_sources
from utils.email_digest import send_daily_digest

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("main")


def fetch_gmail_jobs(profile: Dict) -> List[Dict]:
    """Per-user Gmail read (Naukri/LinkedIn alerts). Never raises."""
    if not profile.get("gmail_connected"):
        return []
    gmail_token = sb.get_gmail_token(profile["user_id"])
    if not gmail_token:
        return []
    try:
        return gmail_parser.scrape(
            profile, gmail_token,
            os.environ.get("GOOGLE_CLIENT_ID", ""),
            os.environ.get("GOOGLE_CLIENT_SECRET", ""),
            supabase_client=sb.get_client(),
        ) or []
    except Exception as e:
        logger.error(f"[gmail] FAILED for {profile['user_id'][:8]}: {e}")
        return []


def resync_user(profile: Dict) -> None:
    """Re-filter the user's STORED feed against their CURRENT profile.

    Without this, changing Settings (roles/locations/salary) has no effect on
    jobs already in the feed — they were scored against the OLD profile, so the
    feed shows stale matches (e.g. Engineers after you switch to "investment
    banker"). This re-scores everything stored and drops what no longer matches
    (unless the user applied to / saved it). It does NO scraping, so it's cheap
    and can run on its own the moment the profile changes.
    """
    user_id = profile["user_id"]
    try:
        stored = sb.get_user_feed_rows(user_id)
        if not stored:
            return
        matched = filter_and_score(stored, profile)
        matched_ids = {r.get("id") for r in matched}
        stale_ids = [
            r["id"] for r in stored
            if r.get("id") not in matched_ids
            and not (r.get("is_applied") or r.get("is_saved"))
        ]
        removed = sb.delete_jobs(stale_ids)
        if matched:
            sb.upsert_jobs(user_id, matched)  # refresh scores/reasons
        logger.info(f"Re-sync {user_id[:8]}: {len(matched)} match, removed {removed} stale")
    except Exception as e:
        logger.error(f"[resync] failed for {user_id[:8]}: {e}")


def process_user(profile: Dict, shared_pool: List[Dict]) -> None:
    """
    Run the full pipeline for one user against the shared ATS job pool.

    The ATS/aggregator pool (`shared_pool`) is fetched ONCE per run in main()
    and reused for every user — it's global data, so there's no reason to pull
    it per user. Only Gmail is per-user (it reads that user's own inbox).
    """
    user_id    = profile["user_id"]
    user_email = profile.get("email", "")
    user_name  = profile.get("full_name", "there")

    logger.info(f"──────────────────────────────────")
    logger.info(f"Processing user: {user_email} ({user_id[:8]}...)")
    logger.info(f"Target roles: {profile.get('target_roles', [])}")
    logger.info(f"Locations:    {profile.get('locations', [])}")

    # Shared ATS pool + this user's Gmail jobs
    gmail_jobs = fetch_gmail_jobs(profile)
    all_raw_jobs: List[Dict] = list(shared_pool) + gmail_jobs
    logger.info(f"Pool: {len(shared_pool)} shared + {len(gmail_jobs)} gmail = {len(all_raw_jobs)} raw")

    # ── Filter, score, and dedup ───────────────────────────────────────────
    filtered = filter_and_score(all_raw_jobs, profile)
    unique   = deduplicate_across_sources(filtered)

    logger.info(f"After filter + dedup: {len(unique)} jobs")

    # ── Optional semantic re-rank (free local embeddings; opt-in) ──────────
    # Re-ranks the keyword-filtered shortlist by meaning ("ML Engineer" ≈
    # "Data Scientist"). No-op unless USE_EMBEDDINGS=1 and fastembed installed.
    if embeddings.available():
        profile_text = " ".join(profile.get("target_roles", []) or []) + " " + (profile.get("resume_text") or "")
        unique = embeddings.rerank(profile_text, unique)

    # ── Determine which jobs are genuinely NEW (not already in the feed) ────
    # Must run BEFORE upsert. We mirror the same source_job_id fallback that
    # upsert_jobs() uses (hash of job_url) so the keys line up exactly.
    import hashlib

    def _effective_key(job: Dict):
        sjid = job.get("source_job_id")
        if not sjid:
            sjid = hashlib.md5(job.get("job_url", "").encode()).hexdigest()[:20]
        return (job.get("source"), sjid)

    existing_keys = sb.get_existing_job_keys(user_id)
    new_jobs_for_digest = [j for j in unique if _effective_key(j) not in existing_keys]
    logger.info(f"Genuinely new (not seen before): {len(new_jobs_for_digest)}")

    # ── Upsert to Supabase ─────────────────────────────────────────────────
    new_count = sb.upsert_jobs(user_id, unique)
    logger.info(f"New jobs inserted: {new_count}")

    # ── Re-sync the STORED feed to the CURRENT profile ─────────────────────
    resync_user(profile)

    # ── Get follow-up reminders ────────────────────────────────────────────
    follow_ups = sb.get_follow_up_due(user_id)
    stale      = sb.get_stale_applications(user_id, days=7)

    if follow_ups:
        logger.info(f"Follow-ups due: {len(follow_ups)}")
    if stale:
        logger.info(f"Stale applications: {len(stale)}")

    # ── Send digest ────────────────────────────────────────────────────────
    if user_email:
        send_daily_digest(
            user_email  = user_email,
            user_name   = user_name,
            new_jobs    = new_jobs_for_digest[:20],  # top 20 for email
            follow_ups  = follow_ups,
            stale       = stale,
        )
    else:
        logger.warning(f"No email set for user {user_id[:8]}, skipping digest")


def main():
    start = datetime.now(timezone.utc)
    logger.info(f"╔══════════════════════════════════════╗")
    logger.info(f"║  Job Search System — Daily Run       ║")
    logger.info(f"║  {start.strftime('%Y-%m-%d %H:%M UTC')}                ║")
    logger.info(f"╚══════════════════════════════════════╝")

    # Verify required env vars
    required = ["SUPABASE_URL", "SUPABASE_SERVICE_KEY"]
    missing = [k for k in required if not os.environ.get(k)]
    if missing:
        logger.error(f"Missing required environment variables: {missing}")
        raise SystemExit(1)

    # Fetch all active users (clear, actionable message if the schema is missing)
    try:
        users = sb.get_active_users()
    except Exception as e:
        logger.error(f"Could not read user_profiles: {e}")
        logger.error("If this mentions a missing relation/table, run supabase/schema.sql "
                     "in the Supabase SQL editor first, then re-run.")
        raise SystemExit(1)
    logger.info(f"Active users: {len(users)}")

    if not users:
        logger.info("No active users. Exiting.")
        return

    # ── Re-sync-only fast path (no scraping) ───────────────────────────────────
    # Triggered when a user saves their profile: re-filter the stored feed to the
    # new profile in seconds, instead of waiting for the full scrape. Scope to one
    # user with TARGET_USER_ID; otherwise resync everyone.
    if os.environ.get("RESYNC_ONLY") == "1":
        target = os.environ.get("TARGET_USER_ID", "").strip()
        if target:
            users = [u for u in users if u.get("user_id") == target]
        logger.info(f"RESYNC-ONLY mode: re-matching {len(users)} user(s), no scraping.")
        for profile in users:
            resync_user(profile)
        logger.info("✓ Resync complete.")
        return

    # ── Fetch the shared ATS/aggregator pool (concurrent; optionally sharded) ──
    # Sharding spreads breadth across scheduled runs (see docs/SCALING.md). Set
    # BATCH_TOTAL>1 on the scheduled cron; each run takes shard = (UTC hour mod N).
    # Manual / unsharded runs (BATCH_TOTAL=1) do the full pool.
    shard_total = max(1, int(os.environ.get("BATCH_TOTAL", "1")))
    shard_index = int(os.environ.get("BATCH_INDEX", datetime.now(timezone.utc).hour % shard_total))
    logger.info(f"Fetching job pool (shard {shard_index + 1}/{shard_total}, concurrent)...")
    try:
        shared_pool = collect_jobs(shard_index, shard_total)
    except Exception as e:
        logger.error(f"Ingestion engine failed: {e}")
        shared_pool = []
    logger.info(f"Shared pool: {len(shared_pool)} jobs from {dict(SOURCE_SUMMARY)}")

    # Record per-source health once (the pool is global, not per-user)
    for source, count in SOURCE_SUMMARY.items():
        try:
            sb.update_scraper_health(source, count, None if count > 0 else "0 jobs returned")
        except Exception as e:
            logger.warning(f"[health] {source}: {e}")

    # Process each user sequentially against the shared pool
    for i, profile in enumerate(users, 1):
        logger.info(f"\n[User {i}/{len(users)}]")
        try:
            process_user(profile, shared_pool)
        except Exception as e:
            logger.error(f"FATAL error for user {profile.get('user_id', '?')[:8]}: {e}")
            logger.debug(traceback.format_exc())
            # Continue to next user — never let one user crash the whole run

    elapsed = (datetime.now(timezone.utc) - start).total_seconds()
    logger.info(f"\n✓ Run complete in {elapsed:.1f}s")


if __name__ == "__main__":
    main()
