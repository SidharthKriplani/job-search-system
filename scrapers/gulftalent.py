"""
GulfTalent Scraper
-------------------
gulftalent.com — senior executive roles in GCC, especially finance and banking.
"""

import requests
from bs4 import BeautifulSoup
import logging
from typing import List, Dict
from datetime import date
import re
import time

logger = logging.getLogger(__name__)

BASE_URL = "https://www.gulftalent.com/jobs"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Accept": "text/html,application/xhtml+xml",
    "Referer": "https://www.gulftalent.com/",
}

GCC_KEYWORDS = ["uae", "dubai", "qatar", "saudi", "riyadh", "doha", "kuwait", "gcc", "gulf"]


def scrape(profile: Dict) -> List[Dict]:
    locations = profile.get("locations", [])
    has_gcc = any(any(g in loc.lower() for g in GCC_KEYWORDS) for loc in locations)
    if not has_gcc:
        return []

    all_jobs: List[Dict] = []
    roles = profile.get("target_roles", ["research manager"])

    for role in roles[:2]:
        params = {
            "q": role,
            "l": "UAE",   # default GCC country; could extend to all
        }
        try:
            resp = requests.get(BASE_URL, headers=HEADERS, params=params, timeout=20)
            resp.raise_for_status()
        except Exception as e:
            logger.warning(f"[GulfTalent] {role} failed: {e}")
            continue

        soup = BeautifulSoup(resp.text, "html.parser")
        cards = soup.select(".job-item") or soup.select("[class*='job']")

        for card in cards:
            try:
                title_el = card.select_one("h2 a") or card.select_one("h3 a") or card.select_one("a[href*='/job']")
                if not title_el:
                    continue
                title = title_el.get_text(strip=True)
                job_url = title_el.get("href", "")
                if job_url and not job_url.startswith("http"):
                    job_url = "https://www.gulftalent.com" + job_url

                company_el = card.select_one("[class*='company']") or card.select_one("[class*='employer']")
                company = company_el.get_text(strip=True) if company_el else ""

                location_el = card.select_one("[class*='location']")
                location = location_el.get_text(strip=True) if location_el else "GCC"

                all_jobs.append({
                    "job_title":          title,
                    "company":            company,
                    "location":           location,
                    "salary_range":       None,
                    "job_url":            job_url,
                    "description_snippet": "",
                    "posted_date":        date.today().isoformat(),
                    "source":             "gulftalent",
                    "source_job_id":      re.search(r'/(\d+)', job_url).group(1) if re.search(r'/(\d+)', job_url) else job_url,
                    "job_type":           "full_time",
                    "seniority":          None,
                })
            except Exception:
                continue

        time.sleep(1.5)

    logger.info(f"[GulfTalent] {len(all_jobs)} jobs found")
    return all_jobs
