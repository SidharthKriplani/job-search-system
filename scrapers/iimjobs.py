"""
iimjobs.com Scraper
--------------------
iimjobs targets premium roles (7L+ salary) — highest signal for senior Indian finance/consulting roles.
Uses requests + BeautifulSoup. Falls back gracefully if structure changes.

Health monitoring: logs extraction rate so we can detect breakage.
"""

import requests
from bs4 import BeautifulSoup
import logging
from typing import List, Dict
from datetime import date
import re
import time

logger = logging.getLogger(__name__)

BASE_URL = "https://www.iimjobs.com/j"
SEARCH_URL = "https://www.iimjobs.com/search/jobs"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Referer": "https://www.iimjobs.com/",
}

CATEGORY_IDS = {
    "Banking & Finance": "1",
    "Consulting":        "4",
    "Research & Analytics": "12",
    "Strategy":          "15",
    "General Management": "7",
}


def _parse_job_card(card, category: str) -> Dict:
    """Extract fields from a single job listing card."""
    try:
        title_el = card.select_one("h2 a") or card.select_one(".job-title a") or card.select_one("a[href*='/j/']")
        title = title_el.get_text(strip=True) if title_el else "Unknown"
        url   = title_el.get("href", "") if title_el else ""
        if url and not url.startswith("http"):
            url = "https://www.iimjobs.com" + url

        company_el = card.select_one(".company-name") or card.select_one(".comp-name") or card.select_one("[class*='company']")
        company = company_el.get_text(strip=True) if company_el else ""

        location_el = card.select_one(".loc") or card.select_one("[class*='location']") or card.select_one("[class*='loc']")
        location = location_el.get_text(strip=True) if location_el else ""

        salary_el = card.select_one(".salary") or card.select_one("[class*='salary']") or card.select_one("[class*='ctc']")
        salary = salary_el.get_text(strip=True) if salary_el else None

        # Source job ID from URL
        url_id_match = re.search(r'/j/(\d+)', url)
        source_id = url_id_match.group(1) if url_id_match else url

        return {
            "job_title":          title,
            "company":            company,
            "location":           location,
            "salary_range":       salary,
            "job_url":            url,
            "description_snippet": "",
            "posted_date":        date.today().isoformat(),
            "source":             "iimjobs",
            "source_job_id":      source_id,
            "job_type":           "full_time",
            "seniority":          None,
        }
    except Exception as e:
        logger.debug(f"[iimjobs] Card parse error: {e}")
        return None


def scrape_category(category_name: str, category_id: str, profile: Dict) -> List[Dict]:
    """Scrape one category page."""
    jobs = []
    page = 1
    max_pages = 3
    roles = [r.lower() for r in profile.get("target_roles", [])]
    min_salary_lpa = profile.get("salary_floor", 0)

    while page <= max_pages:
        params = {
            "category": category_id,
            "page":     page,
        }
        try:
            resp = requests.get(SEARCH_URL, headers=HEADERS, params=params, timeout=20)
            resp.raise_for_status()
        except requests.RequestException as e:
            logger.warning(f"[iimjobs] Category {category_name} page {page} failed: {e}")
            break

        soup = BeautifulSoup(resp.text, "html.parser")

        # Try multiple selectors — the site redesigns occasionally
        cards = (
            soup.select(".job-container") or
            soup.select(".job-listing") or
            soup.select("article.job") or
            soup.select("[class*='job-card']") or
            soup.select("li.job")
        )

        if not cards:
            logger.debug(f"[iimjobs] No cards found on page {page} for {category_name}")
            break

        for card in cards:
            job = _parse_job_card(card, category_name)
            if not job:
                continue
            # Role filter
            if roles:
                title_lower = job["job_title"].lower()
                if not any(kw in title_lower for role in roles for kw in role.split()):
                    continue
            jobs.append(job)

        # Check for next page
        next_btn = soup.select_one("a[rel='next']") or soup.select_one(".pagination .next")
        if not next_btn:
            break

        page += 1
        time.sleep(1)  # polite delay

    return jobs


def scrape(profile: Dict) -> List[Dict]:
    """Main entry. Scrapes all relevant iimjobs categories for this user's profile."""
    all_jobs: List[Dict] = []

    # Always scrape Finance + Research for finance roles; add others based on industry
    industries = profile.get("industries", [])
    active_categories = {"Banking & Finance", "Research & Analytics"}

    if any(i.lower() in ("consulting", "strategy") for i in industries):
        active_categories.add("Consulting")
        active_categories.add("Strategy")
    if any(i.lower() in ("general management", "gm") for i in industries):
        active_categories.add("General Management")

    for cat_name, cat_id in CATEGORY_IDS.items():
        if cat_name not in active_categories:
            continue
        try:
            jobs = scrape_category(cat_name, cat_id, profile)
            all_jobs.extend(jobs)
            logger.info(f"[iimjobs] {cat_name}: {len(jobs)} relevant jobs")
        except Exception as e:
            logger.error(f"[iimjobs] Category {cat_name} error: {e}")

    return all_jobs
