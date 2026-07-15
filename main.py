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


def resync_user(profile: Dict, pool: List[Dict] = None) -> None:
    """Re-filter the user's feed against their CURRENT profile — sourcing
    candidates from BOTH their stored rows and the GLOBAL jobs_pool.

    The pool part is what makes onboarding instant: a brand-new user who saves
    a profile gets matched against last night's stored pool in ~a minute — no
    scraping, no waiting for the nightly cron. In the daily run the in-memory
    pool is passed in; in RESYNC_ONLY mode it's read from the jobs_pool table.
    """
    user_id = profile["user_id"]
    try:
        stored = sb.get_user_feed_rows(user_id)
        if pool is None:
            pool = sb.get_pool_jobs()

        # Candidates = stored rows (carry id/applied/saved state) ∪ pool rows
        # not already stored (deep-copied — filter mutates score fields).
        import hashlib
        def _key(j):
            sjid = j.get("source_job_id") or hashlib.md5((j.get("job_url") or "").encode()).hexdigest()[:20]
            return (j.get("source"), str(sjid))
        stored_keys = {_key(r) for r in stored}
        candidates = list(stored) + [dict(j) for j in pool if _key(j) not in stored_keys]

        if not candidates:
            return
        matched = filter_and_score(candidates, profile)
        matched_ids = {r.get("id") for r in matched if r.get("id")}
        stale_ids = [
            r["id"] for r in stored
            if r.get("id") not in matched_ids
            and not (r.get("is_applied") or r.get("is_saved"))
        ]
        removed = sb.delete_jobs(stale_ids, user_id=user_id)
        if matched:
            sb.upsert_jobs(user_id, matched)  # refresh scores/reasons + add pool finds
        logger.info(f"Re-sync {user_id[:8]}: {len(matched)} match "
                    f"({len(matched) - len(matched_ids)} new from pool), removed {removed} stale")
    except Exception as e:
        logger.error(f"[resync] failed for {user_id[:8]}: {e}")


def process_user(profile: Dict, shared_pool: List[Dict], pool_keys: set = frozenset(),
                 pool_companies: set = frozenset(), stale_capped_keys: set = frozenset()) -> Dict:
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

    # Shared ATS pool + this user's Gmail jobs.
    # IMPORTANT: deep-copy each shared dict. filter_and_score / embeddings.rerank
    # mutate job["match_score"] and job["match_reasons"] IN PLACE. `list(shared_pool)`
    # is only a shallow copy (same dict objects), so without this every user would
    # overwrite the previous user's per-profile scores/reasons on the shared dicts —
    # a multi-tenant data-contamination bug.
    gmail_jobs = fetch_gmail_jobs(profile)
    all_raw_jobs: List[Dict] = [dict(j) for j in shared_pool] + gmail_jobs
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
        # Re-rank ONLY the head of the keyword ranking. Embedding the full
        # shortlist (24k+ texts for a broad profile) took a 2-core runner past
        # the 30-min job timeout. The tail below the cap keeps keyword order —
        # nobody's reading past rank 1500 anyway.
        cap = int(os.environ.get("EMBED_RERANK_CAP", "1500"))
        if len(unique) > cap:
            head = embeddings.rerank(profile_text, unique[:cap])
            unique = head + unique[cap:]
        else:
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

    # Age out yesterday's "new" flags so the dashboard's "New Today" stat is
    # honest (is_new used to be write-once TRUE and counted every job ever).
    aged = sb.age_out_new_flags(user_id, hours=24)
    if aged:
        logger.info(f"Aged out {aged} stale is_new flags")

    existing_keys = sb.get_existing_job_keys(user_id)
    new_jobs_for_digest = [j for j in unique if _effective_key(j) not in existing_keys]
    logger.info(f"Genuinely new (not seen before): {len(new_jobs_for_digest)}")

    # ── Upsert to Supabase ─────────────────────────────────────────────────
    sb.upsert_jobs(user_id, unique)
    # Report the genuinely-new count (the upsert return mixes inserts + updates).
    logger.info(f"Upserted {len(unique)} jobs ({len(new_jobs_for_digest)} genuinely new)")

    # ── Re-sync the STORED feed to the CURRENT profile ─────────────────────
    resync_user(profile, pool=shared_pool)

    # ── Remove postings that have CLOSED at the source ─────────────────────
    # (absent from the current pool although their board fetch succeeded).
    removed_closed = 0
    if pool_keys:
        removed_closed = sb.cleanup_closed_jobs(user_id, pool_keys, pool_companies)
    # Capped sources (workday/oracle/smartrecruiters): same-run absence proves
    # nothing, but a week unseen in jobs_pool does — remove those too.
    if stale_capped_keys:
        removed_closed += sb.cleanup_stale_capped_jobs(user_id, stale_capped_keys)
    if removed_closed:
        logger.info(f"Removed {removed_closed} closed postings")

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

    return {
        "user": _mask_email(user_email),
        "matched": len(unique),
        "new": len(new_jobs_for_digest),
        "removed_closed": removed_closed,
    }


def _mask_email(email: str) -> str:
    """a***@domain — enough to identify, not enough to harvest."""
    if not email or "@" not in email:
        return "(no email)"
    local, dom = email.split("@", 1)
    return f"{local[:1]}***@{dom}"


def _write_run_report(path: str, *, started, shard_index: int, shard_total: int,
                      pool_size: int, user_stats: List[Dict], errors: List[str]) -> None:
    """Sanitized run summary committed back to the repo by the workflow — makes
    every production run diagnosable with a plain `git pull` (no Actions UI)."""
    from datetime import datetime, timezone
    lines = [
        "# Last run report",
        "",
        f"- **When:** {started.strftime('%Y-%m-%d %H:%M UTC')} (finished {datetime.now(timezone.utc).strftime('%H:%M UTC')})",
        f"- **Shard:** {shard_index + 1}/{shard_total}",
        f"- **Pool:** {pool_size} jobs — " + ", ".join(f"{k}: {v}" for k, v in SOURCE_SUMMARY.items()),
        "",
        "| user | matched | new | closed removed |",
        "|------|---------|-----|----------------|",
    ]
    for u in user_stats:
        lines.append(f"| {u['user']} | {u['matched']} | {u['new']} | {u['removed_closed']} |")
    if errors:
        lines += ["", "## Errors", ""] + [f"- {e}" for e in errors]
    else:
        lines += ["", "No errors."]
    lines.append("")
    try:
        with open(path, "w") as f:
            f.write("\n".join(lines))
    except Exception as e:
        logger.warning(f"[report] could not write {path}: {e}")


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

    # ── Persist the pool (instant onboarding + capped-source liveness) ─────────
    persisted = sb.upsert_pool_jobs(shared_pool)
    pruned = sb.prune_pool(days=14)
    logger.info(f"Pool persisted: {persisted} rows refreshed, {pruned} pruned (>14d unseen)")

    # ── Pool-drop alarm: tonight's pool vs recent comparable runs ─────────────
    baseline = sb.recent_pool_sizes(shard_total)
    pool_alarm = None
    if len(baseline) >= 3:
        med = sorted(baseline)[len(baseline) // 2]
        if med > 0 and len(shared_pool) < med * 0.5:
            pool_alarm = (f"Pool dropped to {len(shared_pool)} vs recent median {med} "
                          f"(-{100 - len(shared_pool) * 100 // med}%) — sources may be failing silently")
            logger.error(f"[ALARM] {pool_alarm}")
            try:
                sb.update_scraper_health("_pool", len(shared_pool), pool_alarm)
            except Exception:
                pass

    # ── Canary: a known-good synthetic profile must ALWAYS match something ────
    # Catches "run green but matching broken" — the failure mode that produced
    # a month of empty feeds. No DB user needed; purely in-memory.
    canary_alarm = None
    try:
        canary = {
            "user_id": "canary", "email": "", "gmail_connected": False,
            "target_roles": ["software engineer", "data analyst"],
            "locations": [], "industries": [], "salary_floor": 0,
        }
        canary_matches = filter_and_score([dict(j) for j in shared_pool[:20000]], canary)
        if len(canary_matches) < 10:
            canary_alarm = (f"Canary profile matched only {len(canary_matches)} jobs "
                            f"from a {len(shared_pool)}-job pool — matching may be broken")
            logger.error(f"[ALARM] {canary_alarm}")
            sb.update_scraper_health("_canary", len(canary_matches), canary_alarm)
        else:
            logger.info(f"Canary OK: {len(canary_matches)} matches")
            sb.update_scraper_health("_canary", len(canary_matches), None)
    except Exception as e:
        logger.warning(f"[canary] check failed: {e}")

    # Stale keys for capped sources (computed once, shared by all users)
    stale_capped_keys = sb.get_stale_pool_keys(days=7, sources=["workday", "oracle", "smartrecruiters"])
    if stale_capped_keys:
        logger.info(f"Capped-source stale keys (7d unseen): {len(stale_capped_keys)}")

    # Record per-source health once (the pool is global, not per-user)
    for source, count in SOURCE_SUMMARY.items():
        try:
            sb.update_scraper_health(source, count, None if count > 0 else "0 jobs returned")
        except Exception as e:
            logger.warning(f"[health] {source}: {e}")

    # Pool identity sets for closed-job cleanup (mirror upsert's key fallback).
    import hashlib as _hashlib
    def _pool_key(j):
        sjid = j.get("source_job_id") or _hashlib.md5((j.get("job_url") or "").encode()).hexdigest()[:20]
        return (j.get("source"), str(sjid))
    pool_keys      = {_pool_key(j) for j in shared_pool}
    pool_companies = {(j.get("source"), (j.get("company") or "").strip().lower()) for j in shared_pool}

    # Process each user sequentially against the shared pool
    user_stats: List[Dict] = []
    run_errors: List[str] = []
    for i, profile in enumerate(users, 1):
        logger.info(f"\n[User {i}/{len(users)}]")
        try:
            stats = process_user(profile, shared_pool, pool_keys, pool_companies, stale_capped_keys)
            if stats:
                user_stats.append(stats)
        except Exception as e:
            logger.error(f"FATAL error for user {profile.get('user_id', '?')[:8]}: {e}")
            logger.debug(traceback.format_exc())
            run_errors.append(f"user {profile.get('user_id', '?')[:8]}: {type(e).__name__}: {e}")
            # Continue to next user — never let one user crash the whole run

    for alarm in (pool_alarm, canary_alarm):
        if alarm:
            run_errors.insert(0, f"ALARM: {alarm}")

    sb.record_run_history(shard_index, shard_total, len(shared_pool),
                          len(user_stats), sum(u["matched"] for u in user_stats),
                          len(run_errors))

    if os.environ.get("WRITE_RUN_REPORT", "1") != "0":
        _write_run_report("docs/LAST_RUN.md", started=start,
                          shard_index=shard_index, shard_total=shard_total,
                          pool_size=len(shared_pool), user_stats=user_stats,
                          errors=run_errors)

    elapsed = (datetime.now(timezone.utc) - start).total_seconds()
    logger.info(f"\n✓ Run complete in {elapsed:.1f}s")


if __name__ == "__main__":
    main()
