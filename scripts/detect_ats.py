"""
ATS detector — company-first coverage engine.

For each company in ingest/data/target_companies.json, probe its careers
surface and identify which ATS platform it hires on:

  1. Try careers URL candidates (careers.{domain}, {domain}/careers, jobs.{domain}, …)
  2. Follow redirects — many careers pages redirect straight to the ATS
     (e.g. cashfree.com/careers → careers.kula.ai/cashfree).
  3. Scan the final URL + HTML for ATS fingerprints (hosted domains, embed
     scripts, SPA markers like Phenom's data-ph-id).
  4. For platforms with a connector, extract the slug/config so the company can
     be added to the matching registry list.

Output: ingest/data/ats_detection.json
  {company: {platform, evidence, config, connector: "supported"|"gap"|"unknown"}}
plus a printed GAP REPORT (platforms we can't ingest yet, ranked by count) —
that ranking decides which connector gets built next.

Usage:
  python -m scripts.detect_ats                # all companies
  python -m scripts.detect_ats --tier 1       # only must-cover tier
  python -m scripts.detect_ats --company cashfree.com
"""
import json
import logging
import os
import re
import sys
from concurrent.futures import ThreadPoolExecutor

import requests

logger = logging.getLogger("detect_ats")
HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
           "Accept": "text/html,application/json"}
DATA = os.path.join(os.path.dirname(__file__), "..", "ingest", "data")

# platform → (regexes over final URL + HTML, have_connector)
FINGERPRINTS = [
    ("greenhouse",      [r"boards\.greenhouse\.io/(?:embed/job_board\?for=)?([a-z0-9-]+)",
                         r"greenhouse\.io/([a-z0-9-]+)"], True),
    ("lever",           [r"jobs\.lever\.co/([a-z0-9-]+)"], True),
    ("ashby",           [r"jobs\.ashbyhq\.com/([A-Za-z0-9-]+)"], True),
    ("workday",         [r"([a-z0-9-]+)\.(wd\d+)\.myworkdayjobs\.com"], True),
    ("workable",        [r"apply\.workable\.com/([a-z0-9-]+)"], True),
    ("bamboohr",        [r"([a-z0-9-]+)\.bamboohr\.com"], True),
    ("smartrecruiters", [r"(?:careers|jobs)\.smartrecruiters\.com/([A-Za-z0-9]+)",
                         r"api\.smartrecruiters\.com"], True),
    ("oracle_orc",      [r"([a-z0-9.-]+\.oraclecloud\.com)"], True),
    ("recruitee",       [r"([a-z0-9-]+)\.recruitee\.com"], True),
    ("eightfold",       [r"([a-z0-9-]+)\.eightfold\.ai"], True),
    ("phenom",          [r"data-ph-id=", r"phenompeople", r"phenom-feeds"], True),
    # ── no connector yet (the gap list) ──
    ("kula",            [r"careers\.kula\.ai/([a-z0-9-]+)", r"kula\.ai"], True),
    ("keka",            [r"([a-z0-9-]+)\.keka\.com"], False),
    ("darwinbox",       [r"([a-z0-9-]+)\.darwinbox\.in", r"darwinbox\.com"], False),
    ("zoho_recruit",    [r"([a-z0-9-]+)\.zohorecruit\.(?:com|in)"], False),
    ("freshteam",       [r"([a-z0-9-]+)\.freshteam\.com"], False),
    ("jobvite",         [r"jobs\.jobvite\.com/([a-z0-9-]+)", r"jobvite\.com"], False),
    ("breezy",          [r"([a-z0-9-]+)\.breezy\.hr"], False),
    ("teamtailor",      [r"([a-z0-9-]+)\.teamtailor\.com"], False),
    ("personio",        [r"([a-z0-9-]+)\.jobs\.personio\.(?:de|com)"], False),
    ("icims",           [r"careers?-([a-z0-9-]+)\.icims\.com", r"icims\.com"], False),
    ("taleo",           [r"([a-z0-9-]+)\.taleo\.net"], False),
    ("successfactors",  [r"successfactors\.(?:com|eu)", r"career\d+\.successfactors"], False),
    ("avature",         [r"([a-z0-9-]+)\.avature\.net"], False),
    ("jibe/icims-attract", [r"\.jibeapply\.com", r"jibecdn"], False),
    ("pinpoint",        [r"([a-z0-9-]+)\.pinpointhq\.com"], False),
    ("rippling",        [r"ats\.rippling\.com/([a-z0-9-]+)"], False),
    ("jazzhr",          [r"([a-z0-9-]+)\.applytojob\.com"], False),
    ("homerun",         [r"([a-z0-9-]+)\.homerun\.co"], False),
    ("zoho_workerly/custom", [r"turbohire\.co", r"skillate\.com", r"hirist"], False),
]

CANDIDATE_PATHS = ["https://careers.{d}", "https://{d}/careers", "https://{d}/careers/",
                   "https://jobs.{d}", "https://{d}/jobs", "https://www.{d}/careers"]


def _fetch(url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=12, allow_redirects=True)
        if r.status_code < 400:
            return r.url, r.text[:400000]
    except Exception:
        pass
    return None, None


def detect(company: dict) -> dict:
    d = company["domain"].split("/")[0]
    tried = []
    for tpl in CANDIDATE_PATHS:
        url = tpl.format(d=d)
        final, html = _fetch(url)
        if not final:
            continue
        tried.append(final)
        haystack = final + "\n" + (html or "")
        for platform, patterns, supported in FINGERPRINTS:
            for pat in patterns:
                m = re.search(pat, haystack)
                if m:
                    slug = m.group(1) if m.groups() else None
                    return {"platform": platform, "slug": slug,
                            "evidence": final,
                            "connector": "supported" if supported else "gap"}
        # Phenom needs an active probe (marker can be minified away)
        if html and ("refineSearch" in html or "phenom" in html.lower()):
            return {"platform": "phenom", "slug": None, "evidence": final, "connector": "supported"}
    return {"platform": "custom/unknown", "slug": None,
            "evidence": tried[0] if tried else None, "connector": "unknown"}


def _main():
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s — %(message)s")
    data = json.load(open(os.path.join(DATA, "target_companies.json")))
    companies = data["companies"]
    if "--tier" in sys.argv:
        t = int(sys.argv[sys.argv.index("--tier") + 1])
        companies = [c for c in companies if c.get("tier", 3) <= t]
    if "--company" in sys.argv:
        d = sys.argv[sys.argv.index("--company") + 1]
        companies = [c for c in companies if d in c["domain"]]

    with ThreadPoolExecutor(max_workers=16) as ex:
        results = dict(zip((c["name"] for c in companies), ex.map(detect, companies)))

    out = os.path.join(DATA, "ats_detection.json")
    existing = {}
    if os.path.exists(out):
        try:
            existing = json.load(open(out))
        except Exception:
            existing = {}
    merged = {**existing, **results}
    with open(out, "w") as f:
        json.dump(merged, f, indent=1, sort_keys=True)

    from collections import Counter
    plat = Counter(r["platform"] for r in results.values())
    print(f"\n=== DETECTED ({len(results)} companies) ===")
    for p, n in plat.most_common():
        print(f"  {p:22} {n}")
    print("\n=== GAP REPORT (no connector — ranked; this decides the next build) ===")
    gaps = Counter(r["platform"] for r in results.values() if r["connector"] == "gap")
    for p, n in gaps.most_common():
        names = [k for k, v in results.items() if v["platform"] == p][:6]
        print(f"  {p:22} {n:3}  e.g. {', '.join(names)}")
    print("\n=== SUPPORTED but possibly missing from registry ===")
    for name, r in sorted(results.items()):
        if r["connector"] == "supported" and r.get("slug"):
            print(f"  {r['platform']:16} {str(r['slug']):28} {name}")
    print(f"\nWrote {out}")


if __name__ == "__main__":
    _main()
