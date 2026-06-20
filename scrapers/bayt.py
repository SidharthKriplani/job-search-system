"""
Bayt.com Scraper
-----------------
bayt.com — largest job board in MENA region (UAE, Saudi, Qatar, etc.)
Good complement to NaukriGulf for GCC roles.
"""

import requests
from bs4 import BeautifulSoup
import logging
from typing import List, Dict
from datetime import date
import re
import time

logger = logging.getLogger(__name__)

BASE_URL = "https://www.bayt.com/en/international/jobs/"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Accept": "text/html,application/xhtml+xml",
    "Referer": "https://www.bayt.com/",
}

GCC_KEYWORDS = ["uae", "dubai", "abu dhabi", "qatar", "doha", "saudi", "riyadh", "kuwait", "gcc", "gulf", "bahrain", "oman"]


def scrape(profile: Dict) -> List[Dict]:
    locations = profile.get("locations", [])
    has_gcc = any(any(g in loc.lower() for g in GCC_KEYWORDS) for loc in locations)

    if not has_gcc:
        return []

    all_jobs: List[Dict] = []
    roles = profile.get("target_roles", ["research manager"])

    for role in roles[:3]:  # limit to top 3 roles
        query = role.replace(" ", "-").lower()
        url = f"{BASE_URL}{query}-jobs/"

        for page in range(1, 3):
            page_url = url if page == 1 else f"{url}?page={page}"
            try:
                resp = requests.get(page_url, headers=HEADERS, timeout=20)
                resp.raise_for_status()
            except Exception as e:
                logger.warning(f"[Bayt] {role} page {page} failed: {e}")
                break

            soup = BeautifulSoup(resp.text, "html.parser")
            cards = soup.select("li[data-js-job]") or soup.select(".jobs-content li") or soup.select("article.job-card")

            if not cards:
                break

            for card in cards:
                try:
                    title_el = card.select_one("h2 a") or card.select_one("[class*='title'] a")
                    if not title_el:
                        continue
                    title = title_el.get_text(strip=True)
                    job_url = "https://www.bayt.com" + title_el.get("href", "")

                    company_el = card.select_one("[class*='company']") or card.select_one("[data-company]")
                    company = company_el.get_text(strip=True) if company_el else ""

                    location_el = card.select_one("[class*='location']") or card.select_one("[data-location]")
                    location = location_el.get_text(strip=True) if location_el else ""

                    all_jobs.append({
                        "job_title":          title,
                        "company":            company,
                        "location":           location,
                        "salary_range":       None,
                        "job_url":            job_url,
                        "description_snippet": "",
                        "posted_date":        date.today().isoformat(),
                        "source":             "bayt",
                        "source_job_id":      re.search(r'-(\d+)/?$', job_url).group(1) if re.search(r'-(\d+)/?$', job_url) else job_url,
                        "job_type":           "full_time",
                        "seniority":          None,
                    })
                except Exception:
                    continue

            time.sleep(1.5)

    logger.info(f"[Bayt] {len(all_jobs)} jobs found")
    return all_jobs
