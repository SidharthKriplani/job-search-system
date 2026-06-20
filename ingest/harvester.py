"""
Registry harvester — discover ATS company boards OURSELVES (own the data).

Instead of depending on a third-party (CC-BY-NC) company list, we mine the
**Common Crawl** public index for ATS board URLs, extract company slugs, then
VERIFY each is live before adding it to our own registry data files. The output
(`ingest/data/{ats}_companies.json`) is ours, license-clean, and regenerable.

Pipeline:  discover (Common Crawl CDX)  →  verify (live + has jobs)  →  merge + write

Run (weekly, or manually):
  python -m ingest.harvester greenhouse lever ashby
  python -m ingest.harvester greenhouse --max-pages 5
"""
import json
import logging
import os
import re
import ssl
import sys
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

from .base import http_json

logger = logging.getLogger("harvester")
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
_CTX = ssl.create_default_context()
_CTX.check_hostname = False
_CTX.verify_mode = ssl.CERT_NONE

# ATS → (Common Crawl URL pattern, slug regex)
ATS = {
    "greenhouse": ("boards.greenhouse.io/*", r"greenhouse\.io/([a-z0-9][a-z0-9-]{1,40})"),
    "lever":      ("jobs.lever.co/*",        r"lever\.co/([a-z0-9][a-z0-9-]{1,40})"),
    "ashby":      ("jobs.ashbyhq.com/*",     r"ashbyhq\.com/([a-z0-9][a-z0-9-]{1,40})"),
}
# Path segments that are never company slugs.
_JUNK = {"embed", "api", "jobs", "job", "search", "careers", "apply", "static",
         "assets", "v1", "v2", "en-us", "login", "auth", "widget"}


def _cdx_index() -> str:
    """Latest Common Crawl index id (fallback to a known-good one)."""
    try:
        req = urllib.request.Request("https://index.commoncrawl.org/collinfo.json",
                                     headers={"User-Agent": "Mozilla/5.0"})
        data = json.loads(urllib.request.urlopen(req, timeout=20, context=_CTX).read())
        return data[0]["id"]
    except Exception as e:
        logger.warning(f"[harvest] could not read CC index list: {e}; using fallback")
        return "CC-MAIN-2026-21"


def _ok_slug(s: str) -> bool:
    if s in _JUNK:
        return False
    if re.fullmatch(r"\d+", s):           # pure numeric
        return False
    if re.fullmatch(r"[0-9a-f]{12,}", s):  # hex blob
        return False
    return bool(re.fullmatch(r"[a-z0-9][a-z0-9-]{1,40}", s))


def discover(ats: str, max_pages: int = 5) -> set:
    """Mine Common Crawl CDX for company slugs on this ATS domain."""
    pattern, rx = ATS[ats]
    idx = _cdx_index()
    rxc = re.compile(rx)
    slugs: set = set()
    for page in range(max_pages):
        url = (f"https://index.commoncrawl.org/{idx}-index"
               f"?url={urllib.parse.quote(pattern, safe='')}"
               f"&output=json&fl=url&collapse=urlkey&page={page}")
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            body = urllib.request.urlopen(req, timeout=30, context=_CTX).read().decode("utf-8", "ignore")
        except Exception as e:
            logger.warning(f"[harvest] {ats} page {page} failed: {e}")
            break
        if not body.strip():
            break
        for line in body.splitlines():
            try:
                u = json.loads(line).get("url", "")
            except Exception:
                continue
            m = rxc.search(u)
            if m and _ok_slug(m.group(1)):
                slugs.add(m.group(1))
    logger.info(f"[harvest] {ats}: discovered {len(slugs)} candidate slugs")
    return slugs


def _count(ats: str, slug: str) -> int:
    """How many jobs the board currently returns (0 = dead/empty → skip)."""
    try:
        if ats == "greenhouse":
            d = http_json(f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs")
            return len(d.get("jobs", [])) if d else 0
        if ats == "lever":
            d = http_json(f"https://api.lever.co/v0/postings/{slug}", params={"mode": "json"})
            return len(d) if isinstance(d, list) else 0
        if ats == "ashby":
            d = http_json(f"https://api.ashbyhq.com/posting-api/job-board/{slug}")
            return len(d.get("jobs", [])) if d else 0
    except Exception:
        return 0
    return 0


def verify(ats: str, slugs, workers: int = 24) -> dict:
    """Keep only slugs whose board is live and has jobs → {slug: job_count}."""
    live: dict = {}
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(_count, ats, s): s for s in slugs}
        for f in as_completed(futs):
            n = f.result()
            if n > 0:
                live[futs[f]] = n
    logger.info(f"[harvest] {ats}: {len(live)} live of {len(slugs)}")
    return live


def harvest(ats: str, max_pages: int = 5, do_verify: bool = True, max_verify: int = 1200) -> int:
    """discover → verify → merge with existing data file → write. Returns total slugs stored.

    `max_verify` bounds how many NEW candidates we probe per run (verification is the
    slow part). Unverified leftovers are simply picked up on the next harvest — the
    data file accumulates over weekly runs.
    """
    os.makedirs(DATA_DIR, exist_ok=True)
    path = os.path.join(DATA_DIR, f"{ats}_companies.json")
    existing = {}
    if os.path.exists(path):
        try:
            existing = json.load(open(path))
        except Exception:
            existing = {}

    candidates = discover(ats, max_pages)
    # Don't re-verify ones we already trust; only verify new candidates (capped).
    new = [s for s in candidates if s not in existing][:max_verify]
    live = verify(ats, new) if do_verify else {s: 0 for s in new}
    merged = {**existing, **live}

    with open(path, "w") as f:
        json.dump(merged, f, indent=0, sort_keys=True)
    logger.info(f"[harvest] {ats}: wrote {len(merged)} slugs (+{len(live)} new) → {path}")
    return len(merged)


# urllib.parse imported late to keep top clean
import urllib.parse  # noqa: E402


def _main():
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s — %(message)s")
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    targets = args or list(ATS.keys())
    max_pages = 5
    if "--max-pages" in sys.argv:
        max_pages = int(sys.argv[sys.argv.index("--max-pages") + 1])
    max_verify = int(os.environ.get("HARVEST_VERIFY_LIMIT", "1200"))
    if "--max-verify" in sys.argv:
        max_verify = int(sys.argv[sys.argv.index("--max-verify") + 1])
    for ats in targets:
        if ats in ATS:
            harvest(ats, max_pages=max_pages, max_verify=max_verify)


if __name__ == "__main__":
    _main()
