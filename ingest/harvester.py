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
    # apply.workable.com/<account-slug>/... (job links /j/<SHORTCODE> are excluded
    # by the lowercase-only regex + the junk filter).
    "workable":   ("apply.workable.com/*",   r"apply\.workable\.com/([a-z0-9][a-z0-9-]{1,40})"),
    # <company>.bamboohr.com — the slug is the SUBDOMAIN, not a path segment.
    "bamboohr":   ("*.bamboohr.com/*",       r"(?:^|https?://)([a-z0-9][a-z0-9-]{1,40})\.bamboohr\.com"),
}
# Path segments / subdomains that are never company slugs.
_JUNK = {"embed", "api", "jobs", "job", "search", "careers", "apply", "static",
         "assets", "v1", "v2", "en-us", "login", "auth", "widget",
         # workable path junk
         "j", "oauth", "account", "backend", "plans", "help",
         # bamboohr subdomain junk
         "www", "app", "blog", "marketplace", "partners", "support",
         "status", "docs", "resources", "trial", "signup"}


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


def _cdx_fetch(url: str, tries: int = 3) -> str:
    """Fetch a CDX page with retries. The CC index sometimes drops chunked
    responses mid-stream (IncompleteRead) — the partial body is still valid
    newline-delimited JSON, so salvage whatever arrived instead of losing the page."""
    for attempt in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            return urllib.request.urlopen(req, timeout=60, context=_CTX).read().decode("utf-8", "ignore")
        except Exception as e:
            partial = getattr(e, "partial", None)
            if partial:
                logger.warning(f"[harvest] partial CDX read salvaged ({len(partial)} bytes)")
                return partial.decode("utf-8", "ignore")
            if attempt == tries - 1:
                raise
    return ""


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
            body = _cdx_fetch(url)
        except Exception as e:
            logger.warning(f"[harvest] {ats} page {page} failed: {e}")
            continue  # a flaky page shouldn't abort the remaining pages
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
        if ats == "workable":
            d = http_json(f"https://apply.workable.com/api/v1/widget/accounts/{slug}")
            return len(d.get("jobs", [])) if d else 0
        if ats == "bamboohr":
            d = http_json(f"https://{slug}.bamboohr.com/careers/list")
            return len(d.get("result", [])) if d else 0
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


# ── Workday (special case: identity is a (tenant, wd_number, site) TRIPLE) ────
# CDX-mine *.myworkdayjobs.com URLs like
#   https://{tenant}.{wdN}.myworkdayjobs.com/[{lang}/]{site}/job/{...}
# extract (tenant, wd, site) candidates, then VERIFY each via the public CXS
# POST (the same endpoint the connector uses). Output file format differs from
# the slug ATSes: data/workday_companies.json = {tenant: {wd, site, count}}.
# registry._harvested_workday() reads it; registry.all_workday() merges with
# the curated WORKDAY list (curated wins on tenant collisions).

_WD_HOST = re.compile(r"https?://([a-z0-9-]{2,40})\.(wd\d{1,3})\.myworkdayjobs\.com/([^?#]*)")
_WD_LANG = re.compile(r"^[a-z]{2}-[A-Z]{2}$")
_WD_JUNK_SITES = {"wday", "job", "jobs", "login", "api"}


def _wd_site_from_path(path: str):
    """First real path segment = career site id (skip a leading lang like en-US)."""
    segs = [s for s in path.split("/") if s]
    if segs and _WD_LANG.fullmatch(segs[0]):
        segs = segs[1:]
    if not segs:
        return None
    site = segs[0]
    if site.lower() in _WD_JUNK_SITES:
        return None
    return site if re.fullmatch(r"[A-Za-z0-9_-]{1,80}", site) else None


def discover_workday(max_pages: int = 5) -> dict:
    """Mine CC for Workday candidates → {tenant: set((wd, site))}."""
    idx = _cdx_index()
    cands: dict = {}
    for page in range(max_pages):
        url = (f"https://index.commoncrawl.org/{idx}-index"
               f"?url={urllib.parse.quote('*.myworkdayjobs.com/*', safe='')}"
               f"&output=json&fl=url&collapse=urlkey&page={page}")
        try:
            body = _cdx_fetch(url)
        except Exception as e:
            logger.warning(f"[harvest] workday page {page} failed: {e}")
            continue
        if not body.strip():
            break
        for line in body.splitlines():
            try:
                u = json.loads(line).get("url", "")
            except Exception:
                continue
            m = _WD_HOST.search(u)
            if not m:
                continue
            tenant, wd, path = m.group(1), m.group(2), m.group(3)
            site = _wd_site_from_path(path)
            if site:
                cands.setdefault(tenant, set()).add((wd, site))
    logger.info(f"[harvest] workday: {len(cands)} candidate tenants")
    return cands


def _wd_count(tenant: str, wd: str, site: str) -> int:
    """Total jobs the CXS endpoint reports (0 = dead/wrong site)."""
    d = http_json(f"https://{tenant}.{wd}.myworkdayjobs.com/wday/cxs/{tenant}/{site}/jobs",
                  method="POST",
                  json_body={"appliedFacets": {}, "limit": 1, "offset": 0, "searchText": ""})
    return int(d.get("total", 0)) if d else 0


def harvest_workday(max_pages: int = 5, max_verify: int = 300) -> int:
    """discover → verify (best site per tenant) → merge → write. Returns total stored."""
    os.makedirs(DATA_DIR, exist_ok=True)
    path = os.path.join(DATA_DIR, "workday_companies.json")
    existing = {}
    if os.path.exists(path):
        try:
            existing = json.load(open(path))
        except Exception:
            existing = {}

    cands = discover_workday(max_pages)
    new_tenants = [t for t in cands if t not in existing][:max_verify]

    def best(tenant):
        top = (0, None, None)
        for wd, site in sorted(cands[tenant]):
            n = _wd_count(tenant, wd, site)
            if n > top[0]:
                top = (n, wd, site)
        return tenant, top

    live = {}
    with ThreadPoolExecutor(max_workers=12) as ex:
        for tenant, (n, wd, site) in ex.map(best, new_tenants):
            if n > 0:
                live[tenant] = {"wd": wd, "site": site, "count": n}
    merged = {**existing, **live}

    with open(path, "w") as f:
        json.dump(merged, f, indent=0, sort_keys=True)
    logger.info(f"[harvest] workday: wrote {len(merged)} tenants (+{len(live)} new) → {path}")
    return len(merged)


# urllib.parse imported late to keep top clean
import urllib.parse  # noqa: E402


def _main():
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s — %(message)s")
    # Positional targets only — skip --flags AND their values.
    argv, args, skip = sys.argv[1:], [], False
    for a in argv:
        if skip:
            skip = False
            continue
        if a.startswith("--"):
            skip = a in ("--max-pages", "--max-verify")
            continue
        args.append(a)
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
        elif ats == "workday":
            harvest_workday(max_pages=max_pages, max_verify=min(max_verify, 300))
        else:
            logger.warning(f"[harvest] unknown target: {ats}")


if __name__ == "__main__":
    _main()
