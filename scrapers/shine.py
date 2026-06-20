"""
Shine.com Scraper
------------------
shine.com — HT Media's job board, decent volume for Indian mid-senior roles.
"""

import requests
from bs4 import BeautifulSoup
import logging
from typing import List, Dict
from datetime import date
import re
import time

logger = logging.getLogger(__name__)

SEARCH_URL = "https://www.shine.com/job-search/"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Accept": "text/html,application/xhtml+xml",
    "Referer": "https://www.shine.com/",
}


def scrape(profile: Dict) -> List[Dict]:
    all_jobs: List[Dict] = []
    roles = profile.get("target_roles", ["research manager"])
    locations = [l for l in profile.get("locations", ["India"]) if l.lower() not in ("uae", "gcc", "gulf")]

    for role in roles[:2]:
        query_slug = role.lower().replace(" ", "-")
        url = f"{SEARCH_URL}{query_slug}-jobs/"

        try:
            resp = requests.get(url, headers=HEADERS, timeout=20)
            resp.raise_for_status()
        except Exception as e:
            logger.warning(f"[Shine] {role} failed: {e}")
            continue

        soup = BeautifulSoup(resp.text, "html.parser")
        cards = (
            soup.select(".jobCard") or
            soup.select(".job-container") or
            soup.select("[class*='job-card']") or
            soup.select("article.job")
        )

        for card in cards:
            try:
                title_el = card.select_one("h2 a") or card.select_one("h3 a") or card.select_one("[class*='title'] a")
                if not title_el:
                    continue
                title = title_el.get_text(strip=True)
                job_url = title_el.get("href", "")
                if job_url and not job_url.startswith("http"):
                    job_url = "https://www.shine.com" + job_url

                company_el = card.select_one("[class*='company']") or card.select_one("[class*='org']")
                company = company_el.get_text(strip=True) if company_el else ""

                location_el = card.select_one("[class*='loc']") or card.select_one("[class*='location']")
                location = location_el.get_text(strip=True) if location_el else ""

                salary_el = card.select_one("[class*='salary']") or card.select_one("[class*='sal']")
                salary = salary_el.get_text(strip=True) if salary_el else None

                all_jobs.append({
                    "job_title":          title,
                    "company":            company,
                    "location":           location,
                    "salary_range":       salary,
                    "job_url":            job_url,
                    "description_snippet": "",
                    "posted_date":        date.today().isoformat(),
                    "source":             "shine",
                    "source_job_id":      re.search(r'-(\d+)/?(?:\?|$)', job_url).group(1) if re.search(r'-(\d+)/?(?:\?|$)', job_url) else job_url[-40:],
                    "job_type":           "full_time",
                    "seniority":          None,
                })
            except Exception:
                continue

        time.sleep(1.5)

    logger.info(f"[Shine] {len(all_jobs)} jobs found")
    return all_jobs
