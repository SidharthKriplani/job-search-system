"""
SAP SuccessFactors — Career Site Builder (CSB) sites. The template is SHARED
across tenants and SERVER-RENDERED, so one parser covers Birlasoft, Capgemini,
SAP, LTTS, Asian Paints, Tata Motors, LTIMindtree, ... (the Indian IT majors
that no JSON ATS API reaches).

  GET https://{host}/search/?q=&locationsearch={loc}&startrow={n}
  → HTML rows: <tr class="data-row"> containing
      <a class="jobTitle-link" href="/job/{slug}/{id}/">Title</a>
      <span class="jobLocation">City, IN</span>
      <span class="jobDate">Jun 29, 2026</span>

This parses the shared CSB template, not per-company HTML — the template is
identical across tenants and versioned by SAP, so it's closer to Workday's
stability than to ad-hoc scraping. Tenants with CUSTOMIZED templates
(HCLTech, Wipro, Chargebee — client-rendered) return 0 rows and are simply
not registered. Failsafe: any error → [].

Registry entries are (host, display). Config:
  SFCSB_MAX_PER_COMPANY  default 200
  SFCSB_LOCATION         default "India"
"""
import logging
import os
import re
from datetime import datetime
from html import unescape
from typing import Dict, List

import requests

from ..base import HEADERS, make_job

logger = logging.getLogger(__name__)
SOURCE = "successfactors"
PAGE = 25  # CSB serves 25 rows/page

_ROW = re.compile(r'<tr class="data-row">(.*?)</tr>', re.S)
_TITLE = re.compile(r'class="jobTitle-link"[^>]*href="(/job/[^"]+)"[^>]*>([^<]+)<|href="(/job/[^"]+)"[^>]*class="jobTitle-link"[^>]*>([^<]+)<')
_LOC = re.compile(r'class="jobLocation">\s*([^<]{2,80}?)\s*<', re.S)
_DATE = re.compile(r'class="jobDate[^"]*">\s*([A-Z][a-z]{2}\s+\d{1,2},\s+\d{4})')


def fetch_site(host: str, display: str, cap: int = 0) -> List[Dict]:
    cap = cap or int(os.environ.get("SFCSB_MAX_PER_COMPANY", "200"))
    loc_q = os.environ.get("SFCSB_LOCATION", "India")
    out: List[Dict] = []
    seen: set = set()
    startrow = 0
    while startrow < cap:
        try:
            r = requests.get(f"https://{host}/search/",
                             params={"q": "", "locationsearch": loc_q, "startrow": startrow},
                             headers={**HEADERS, "Accept": "text/html"}, timeout=20)
            r.raise_for_status()
        except Exception as e:
            logger.warning(f"[sf_csb] {host} page {startrow} failed: {type(e).__name__}")
            break
        rows = _ROW.findall(r.text)
        if not rows:
            break
        new = 0
        for row in rows:
            m = _TITLE.search(row)
            if not m:
                continue
            href = m.group(1) or m.group(3) or ""
            title = unescape((m.group(2) or m.group(4) or "").strip())
            if not href or href in seen:
                continue
            seen.add(href)
            new += 1
            lm = _LOC.search(row)
            dm = _DATE.search(row)
            posted = None
            if dm:
                try:  # "Jun 29, 2026" → ISO (base.to_iso_date can't parse this format)
                    posted = datetime.strptime(dm.group(1), "%b %d, %Y").date().isoformat()
                except ValueError:
                    posted = None
            job = make_job(
                title=title,
                company=display,
                url=f"https://{host}{href}",
                source=SOURCE,
                location=unescape(re.sub(r"\s+", " ", lm.group(1))).strip() if lm else "",
                posted=posted,
                source_job_id=(re.search(r"/(\d+)/?$", href) or [None, href])[1],
            )
            if job:
                out.append(job)
        if new == 0:          # page of pure duplicates → done
            break
        startrow += PAGE
    return out


def fetch() -> List[Dict]:
    from ..registry import SFCSB
    cap = int(os.environ.get("SFCSB_MAX_PER_COMPANY", "200"))
    jobs: List[Dict] = []
    for host, display in SFCSB:
        try:
            jobs.extend(fetch_site(host, display, cap))
        except Exception as e:
            logger.warning(f"[sf_csb] {host} failed: {e}")
    return jobs
