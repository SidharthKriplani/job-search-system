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

# ── Scrapers ──────────────────────────────────────────────────────────────────
from scrapers import workday, greenhouse, lever
from scrapers import gmail_parser
from scrapers import iimjobs, foundit, naukrigulf
from scrapers import bayt, gulftalent
from scrapers import instahyre, cutshort, ambitionbox
from scrapers import shine, timesjobs

# ── Utils ─────────────────────────────────────────────────────────────────────
from utils import supabase_client as sb
from utils.filter import filter_and_score, deduplicate_across_sources
from utils.email_digest import send_daily_digest

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("main")


# ─── Scraper registry ─────────────────────────────────────────────────────────
# Each entry: (source_name, scraper_module, needs_gmail_token)
SCRAPERS: List[Tuple[str, object, bool]] = [
    ("workday",     workday,     False),
    ("greenhouse",  greenhouse,  False),
    ("lever",       lever,       False),
    ("iimjobs",     iimjobs,     False),
    ("foundit",     foundit,     False),
    ("naukrigulf",  naukrigulf,  False),
    ("bayt",        bayt,        False),
    ("gulftalent",  gulftalent,  False),
    ("instahyre",   instahyre,   False),
    ("cutshort",    cutshort,    False),
    ("ambitionbox", ambitionbox, False),
    ("shine",       shine,       False),
    ("timesjobs",   timesjobs,   False),
    ("gmail",       gmail_parser, True),  # requires connected Gmail
]


def run_scraper(
    source: str,
    scraper,
    profile: Dict,
    gmail_token: Dict = None,
) -> Tuple[str, List[Dict], str]:
    """
    Run one scraper and return (source, jobs, error_or_None).
    All exceptions are caught — never propagates.
    """
    try:
        if source == "gmail":
            if not gmail_token:
                return source, [], None  # user hasn't connected Gmail
            client_id     = os.environ.get("GOOGLE_CLIENT_ID", "")
            client_secret = os.environ.get("GOOGLE_CLIENT_SECRET", "")
            jobs = scraper.scrape(
                profile, gmail_token, client_id, client_secret,
                supabase_client=sb.get_client()
            )
        else:
            jobs = scraper.scrape(profile)
        return source, jobs, None
    except Exception as e:
        err = f"{type(e).__name__}: {e}"
        logger.error(f"[{source}] FAILED: {err}")
        logger.debug(traceback.format_exc())
        return source, [], err


def process_user(profile: Dict) -> None:
    """Run the full pipeline for one user."""
    user_id    = profile["user_id"]
    user_email = profile.get("email", "")
    user_name  = profile.get("full_name", "there")

    logger.info(f"──────────────────────────────────")
    logger.info(f"Processing user: {user_email} ({user_id[:8]}...)")
    logger.info(f"Target roles: {profile.get('target_roles', [])}")
    logger.info(f"Locations:    {profile.get('locations', [])}")

    # Fetch Gmail token if available
    gmail_token = sb.get_gmail_token(user_id) if profile.get("gmail_connected") else None

    # ── Run all scrapers concurrently ──────────────────────────────────────
    all_raw_jobs: List[Dict] = []
    source_results: Dict[str, Tuple[List[Dict], str]] = {}

    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = {
            executor.submit(run_scraper, src, mod, profile, gmail_token if needs_token else None): src
            for src, mod, needs_token in SCRAPERS
        }
        for future in as_completed(futures):
            source, jobs, error = future.result()
            source_results[source] = (jobs, error)
            all_raw_jobs.extend(jobs)
            logger.info(f"  [{source}] {'ERROR' if error else f'{len(jobs)} jobs'}")

    # ── Update scraper health ──────────────────────────────────────────────
    for source, (jobs, error) in source_results.items():
        sb.update_scraper_health(source, len(jobs), error)

    logger.info(f"Total raw jobs: {len(all_raw_jobs)}")

    # ── Filter, score, and dedup ───────────────────────────────────────────
    filtered = filter_and_score(all_raw_jobs, profile)
    unique   = deduplicate_across_sources(filtered)

    logger.info(f"After filter + dedup: {len(unique)} jobs")

    # ── Upsert to Supabase ─────────────────────────────────────────────────
    new_count = sb.upsert_jobs(user_id, unique)
    logger.info(f"New jobs inserted: {new_count}")

    # ── Get jobs for digest (only the new ones) ────────────────────────────
    new_jobs_for_digest = [j for j in unique if True]  # all newly scraped, dedup handles seen

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

    # Fetch all active users
    users = sb.get_active_users()
    logger.info(f"Active users: {len(users)}")

    if not users:
        logger.info("No active users. Exiting.")
        return

    # Process each user sequentially (polite to external services)
    for i, profile in enumerate(users, 1):
        logger.info(f"\n[User {i}/{len(users)}]")
        try:
            process_user(profile)
        except Exception as e:
            logger.error(f"FATAL error for user {profile.get('user_id', '?')[:8]}: {e}")
            logger.debug(traceback.format_exc())
            # Continue to next user — never let one user crash the whole run

    elapsed = (datetime.now(timezone.utc) - start).total_seconds()
    logger.info(f"\n✓ Run complete in {elapsed:.1f}s")


if __name__ == "__main__":
    main()
