"""
Naukri Profile Refresh
-----------------------
Keeps Naukri profiles "last active" date fresh for all users who have
stored their Naukri credentials in Supabase.

Credentials are optional — users who haven't set them are skipped.
Uses Playwright (headless Chromium) to simulate a login.

This runs AFTER the main scraper (see daily.yml) as a non-critical step.
Failure here does NOT affect job scraping.

Naukri credentials stored in user_profiles:
  naukri_email    TEXT  -- encrypted at rest by Supabase
  naukri_password TEXT  -- encrypted at rest by Supabase

NOTE: Store passwords only if users explicitly opt-in. Many users
      skip this feature entirely and rely on Gmail alerts only.
"""

import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def refresh_profile(naukri_email: str, naukri_password: str) -> bool:
    """
    Log in to Naukri via headless browser and trigger a profile update,
    which refreshes the 'last active' date shown to recruiters.
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        logger.error("[Naukri] Playwright not installed. Run: pip install playwright && playwright install chromium")
        return False

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            viewport={"width": 1280, "height": 800},
        )
        page = context.new_page()

        try:
            # Login
            page.goto("https://www.naukri.com/nlogin/login", timeout=30000)
            page.wait_for_selector("#usernameField", timeout=10000)

            page.fill("#usernameField", naukri_email)
            page.fill("#passwordField", naukri_password)
            page.click("button[type='submit']")

            page.wait_for_url("**/mnjuser/profile**", timeout=15000)

            # Navigate to profile edit — the edit action itself refreshes "last active"
            page.goto("https://www.naukri.com/mnjuser/profile?id=&altresid", timeout=15000)
            page.wait_for_load_state("networkidle", timeout=10000)

            logger.info(f"[Naukri] Profile refreshed for {naukri_email}")
            return True

        except Exception as e:
            logger.warning(f"[Naukri] Refresh failed for {naukri_email}: {e}")
            return False
        finally:
            browser.close()


def main():
    """Refresh Naukri profiles for all users who have credentials stored."""
    try:
        from utils.supabase_client import get_client
    except ImportError:
        logger.error("[Naukri] Cannot import supabase_client. Run from repo root.")
        return

    sb = get_client()

    # Only select users who have naukri_email set.
    # The naukri_email / naukri_password columns are optional — if the schema
    # migration that adds them hasn't been applied, this query raises. Guard it
    # so this non-critical step degrades gracefully instead of crashing.
    try:
        result = sb.table("user_profiles") \
            .select("user_id, naukri_email, naukri_password") \
            .eq("is_active", True) \
            .not_.is_("naukri_email", "null") \
            .execute()
    except Exception as e:
        logger.warning(f"[Naukri] Could not read credentials (columns may not exist): {e}")
        return

    users = result.data or []

    if not users:
        logger.info("[Naukri] No users with Naukri credentials. Skipping.")
        return

    logger.info(f"[Naukri] Refreshing {len(users)} profile(s)")

    for user in users:
        email    = user.get("naukri_email")
        password = user.get("naukri_password")
        if email and password:
            refresh_profile(email, password)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-8s %(name)s — %(message)s",
    )
    main()
