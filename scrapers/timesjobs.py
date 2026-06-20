"""
TimesJobs Scraper
------------------
timesjobs.com — Times Internet job board, reasonable Indian coverage especially BFSI.
"""

import requests
from bs4 import BeautifulSoup
import logging
from typing import List, Dict
from datetime import date
import re
import time

logger = logging.getLogger(__name__)

SEARCH_URL = "https://www.timesjobs.com/candidate/job-search.html"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Accept": "text/html,application/xhtml+xml",
    "Referer": "https://www.timesjobs.com/",
}


def scrape(profile: Dict) -> List[Dict]:
    all_jobs: List[Dict] = []
    roles = profile.get("target_roles", ["research manager"])
    locations = [l for l in profile.get("locations", ["India"]) if l.lower() not in ("uae", "gcc", "gulf")]

    for role in roles[:2]:
        params = {
            "searchType": "personalizedSearch",
            "from":       "submit",
            "txtKeywords": role,
            "txtLocation": locations[0] if locations else "India",
            "cboWorkExp1": max(0, profile.get("experience_years", 0) - 2),
        }

        try:
            resp = requests.get(SEARCH_URL, headers=HEADERS, params=params, timeout=20)
            resp.raise_for_status()
        except Exception as e:
            logger.warning(f"[TimesJobs] {role} failed: {e}")
            continue

        soup = BeautifulSoup(resp.text, "html.parser")
        cards = (
            soup.select(".clearfix.job-bx") or
            soup.select("[class*='job-bx']") or
            soup.select("li.job-bx")
        )

        for card in cards:
            try:
                title_el = card.select_one("h2 a") or card.select_one(".job-title a") or card.select_one("[class*='title'] a")
                if not title_el:
                    continue
                title = title_el.get_text(strip=True)
                job_url = title_el.get("href", "")

                company_el = card.select_one(".joblist-comp-name") or card.select_one("[class*='comp-name']")
                company = company_el.get_text(strip=True) if company_el else ""

                location_el = card.select_one(".srp-skills") or card.select_one("[class*='location']")
                location = location_el.get_text(strip=True) if location_el else ""

                salary_el = card.select_one(".salary") or card.select_one("[class*='salary']")
                salary = salary_el.get_text(strip=True) if salary_el else None

                job_id_match = re.search(r'(\d{7,})', job_url)
                source_id = job_id_match.group(1) if job_id_match else job_url[-40:]

                all_jobs.append({
                    "job_title":          title,
                    "company":            company,
                    "location":           location,
                    "salary_range":       salary,
                    "job_url":            job_url,
                    "description_snippet": "",
                    "posted_date":        date.today().isoformat(),
                    "source":             "timesjobs",
                    "source_job_id":      source_id,
                    "job_type":           "full_time",
                    "seniority":          None,
                })
            except Exception:
                continue

        time.sleep(1.5)

    logger.info(f"[TimesJobs] {len(all_jobs)} jobs found")
    return all_jobs
