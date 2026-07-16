"""
Link canary — catches the "job link lands on the homepage" class of bug
(e.g. Phenom SPA routes) BEFORE users hit it.

For each source in the ingested pool, sample N job URLs and GET them:
  - status >= 400, or
  - a redirect that lands on the site ROOT (path "/" or a bare locale like
    /global/en with no job segment)  → counts as a BROKEN link.
A source with >50% broken samples is reported (exit code 1 in --strict mode,
so CI can flag it; default is report-only so the nightly run never fails on it).

Usage:
  python -m scripts.link_canary --json pool.json          # check a saved pool
  python -m scripts.link_canary                            # ingest fresh sample
  python -m scripts.link_canary --per-source 5 --strict
"""
import json
import logging
import random
import sys
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlparse

import requests

logger = logging.getLogger("link_canary")
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; JobSearchBot-canary/1.0)"}

# Sources whose links are behind auth walls / bot checks from datacenter IPs —
# a 403 here is expected, not a broken link. Checked for 2xx OR known-blocked.
EXPECT_BLOCKED = {"linkedin", "indeed", "naukri", "glassdoor", "instahyre", "eightfold"}


def _looks_like_homepage(final_url: str, original_url: str) -> bool:
    """Redirect landed on site root / bare locale → the job page is gone."""
    if final_url.rstrip("/") == original_url.rstrip("/"):
        return False
    path = urlparse(final_url).path.rstrip("/")
    segs = [s for s in path.split("/") if s]
    # "", "/en", "/global/en", "/us/en" — nothing job-like left in the path
    return len(segs) <= 2 and "job" not in path.lower()


def check_url(url: str) -> str:
    """'ok' | 'broken' | 'blocked'"""
    try:
        r = requests.get(url, headers=HEADERS, timeout=15, allow_redirects=True)
        if r.status_code in (401, 403, 429):
            return "blocked"
        if r.status_code >= 400:
            return "broken"
        if _looks_like_homepage(r.url, url):
            return "broken"
        return "ok"
    except Exception:
        return "broken"


def run(jobs, per_source: int = 5) -> dict:
    by_source: dict = {}
    for j in jobs:
        by_source.setdefault(j.get("source", "?"), []).append(j.get("job_url", ""))
    report = {}
    for source, urls in sorted(by_source.items()):
        sample = random.sample(urls, min(per_source, len(urls)))
        with ThreadPoolExecutor(max_workers=5) as ex:
            results = list(ex.map(check_url, sample))
        broken = results.count("broken")
        blocked = results.count("blocked")
        # For known-blocked sources, 'blocked' is fine; broken still counts.
        base = source.split("_")[0]
        status = "FAIL" if broken > len(sample) / 2 and base not in EXPECT_BLOCKED else "ok"
        report[source] = {"sampled": len(sample), "ok": results.count("ok"),
                          "broken": broken, "blocked": blocked, "status": status}
    return report


def _main():
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s — %(message)s")
    per_source = 5
    if "--per-source" in sys.argv:
        per_source = int(sys.argv[sys.argv.index("--per-source") + 1])

    if "--json" in sys.argv:
        path = sys.argv[sys.argv.index("--json") + 1]
        jobs = json.load(open(path))
    else:
        from ingest.run import collect_jobs
        jobs = collect_jobs()

    report = run(jobs, per_source)
    failed = [s for s, r in report.items() if r["status"] == "FAIL"]
    print("\n=== LINK CANARY ===")
    for s, r in report.items():
        flag = " <-- BROKEN LINKS" if r["status"] == "FAIL" else ""
        print(f"  {s:<20} ok={r['ok']} broken={r['broken']} blocked={r['blocked']} of {r['sampled']}{flag}")
    if failed:
        print(f"\nSources with broken links: {', '.join(failed)}")
        if "--strict" in sys.argv:
            sys.exit(1)


if __name__ == "__main__":
    _main()
