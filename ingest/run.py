"""
Ingestion orchestrator — concurrent + shardable.

The unit of work is a single board/tenant/source ("fetch unit"). Units run
CONCURRENTLY (pure network I/O), and can be SHARDED across scheduled runs so the
breadth is spread over the night instead of one giant run (see docs/SCALING.md).

collect_jobs(shard_index, shard_total):
  - builds the flat list of fetch units
  - keeps only this shard's slice (units[shard_index::shard_total])
  - runs them in a thread pool, normalizes, dedups, returns the pool
SOURCE_SUMMARY records per-connector counts so silent breakage stays visible.

CLI:
  python -m ingest.run                 # full run
  python -m ingest.run --shard 0 3     # shard 0 of 3
  python -m ingest.run --json out.json
"""
import json
import logging
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Callable, Dict, List, Tuple

from .connectors import greenhouse, lever, ashby, aggregators, jobspy, workday, oracle, smartrecruiters, instahyre, recruitee, foundit, workable, bamboohr
from .dedup import deduplicate
from . import registry
from .registry import unit_domain

logger = logging.getLogger("ingest")

MAX_WORKERS = int(os.environ.get("INGEST_WORKERS", "16"))

# Filled in by collect_jobs(): {connector_label: job_count}
SOURCE_SUMMARY: Dict[str, int] = {}


def _build_units() -> List[Tuple[str, str, Callable[[], List[Dict]], str]]:
    """Flat list of (connector_label, unit_id, fetch_callable, domain). One per board/tenant."""
    units: List[Tuple[str, str, Callable]] = []

    # Curated lists UNIONed with our own harvested lists (data/*_companies.json).
    for slug, disp in registry.all_greenhouse():
        units.append(("greenhouse", slug, lambda s=slug, d=disp: greenhouse.fetch_board(s, d)))
    for slug, disp in registry.all_lever():
        units.append(("lever", slug, lambda s=slug, d=disp: lever.fetch_board(s, d)))
    for slug, disp in registry.all_ashby():
        units.append(("ashby", slug, lambda s=slug, d=disp: ashby.fetch_board(s, d)))

    wcap = int(os.environ.get("WORKABLE_MAX_PER_COMPANY", "500"))
    for slug, disp in registry.all_workable():
        units.append(("workable", slug, lambda s=slug, d=disp, c=wcap: workable.fetch_board(s, d, c)))
    bcap = int(os.environ.get("BAMBOOHR_MAX_PER_COMPANY", "200"))
    for slug, disp in registry.all_bamboohr():
        units.append(("bamboohr", slug, lambda s=slug, d=disp, c=bcap: bamboohr.fetch_company(s, d, c)))

    cap = int(os.environ.get("WORKDAY_MAX_PER_COMPANY", "150"))
    # Curated tenants unioned with harvested triples (data/workday_companies.json).
    for tenant, wd, site, disp in registry.all_workday():
        units.append(("workday", tenant,
                      lambda t=tenant, w=wd, st=site, d=disp: workday.fetch_company(t, w, st, d, cap)))

    # Oracle Recruiting Cloud (banks/finance) + SmartRecruiters — one unit each.
    ocap = int(os.environ.get("ORACLE_MAX_PER_COMPANY", "200"))
    for host, site, disp in registry.ORACLE:
        units.append(("oracle", host,
                      lambda h=host, st=site, d=disp: oracle.fetch_company(h, st, d, ocap)))
    for cid, disp in registry.SMARTRECRUITERS:
        units.append(("smartrecruiters", cid,
                      lambda c=cid, d=disp: smartrecruiters.fetch_company(c, d)))

    # Broad engines run as single units (they internally cover many terms/sources).
    units.append(("jobspy", "jobspy", jobspy.fetch))
    units.append(("aggregators", "aggregators", aggregators.fetch))
    units.append(("instahyre", "instahyre", instahyre.fetch))
    units.append(("recruitee", "recruitee", recruitee.fetch))
    units.append(("foundit", "foundit", foundit.fetch))
    return [(label, uid, fn, unit_domain(label, uid)) for (label, uid, fn) in units]


def collect_jobs(shard_index: int = 0, shard_total: int = 1,
                 priority_domains=None) -> List[Dict]:
    """Run this shard's fetch units concurrently, normalize + dedup, return the pool.

    priority_domains: domains the night's active users need (e.g. {"finance","tech"}).
    Units in those domains are ordered FIRST so they're never starved by a job
    timeout, and each returned job is stamped with its source_domain for scoring.
    """
    SOURCE_SUMMARY.clear()
    units = _build_units()

    # Prioritise the domains active users actually need (stable, keeps order).
    if priority_domains:
        pset = set(priority_domains)
        units.sort(key=lambda u: 0 if u[3] in pset else 1)

    if shard_total > 1:
        units = units[shard_index::shard_total]
        logger.info(f"[ingest] shard {shard_index+1}/{shard_total}: {len(units)} fetch units")
    else:
        logger.info(f"[ingest] full run: {len(units)} fetch units")

    # Pre-seed every label in THIS shard with 0 so a connector that contributes
    # nothing still shows an explicit 0 in the summary / LAST_RUN.md — silent
    # absence and "ran but returned 0" must be distinguishable.
    for label, _uid, _fn, _domain in units:
        SOURCE_SUMMARY.setdefault(label, 0)

    raw: List[Dict] = []
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
        futs = {ex.submit(_safe, fn): (label, domain) for label, _uid, fn, domain in units}
        for fut in as_completed(futs):
            label, domain = futs[fut]
            jobs = fut.result()
            for j in jobs:
                j["source_domain"] = domain   # stamped for scoring; stripped at upsert unless whitelisted
            SOURCE_SUMMARY[label] = SOURCE_SUMMARY.get(label, 0) + len(jobs)
            raw.extend(jobs)

    for label, n in SOURCE_SUMMARY.items():
        logger.info(f"  [{label}] {n} jobs")
    deduped = deduplicate(raw)
    logger.info(f"[ingest] {len(raw)} raw -> {len(deduped)} after dedup")
    return deduped


def _safe(fn: Callable[[], List[Dict]]) -> List[Dict]:
    """A fetch unit must never raise — one bad board can't stop the shard."""
    try:
        return fn() or []
    except Exception as e:
        logger.warning(f"[ingest] unit failed: {type(e).__name__}: {e}")
        return []


def _main():
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s — %(message)s")
    shard_index, shard_total = 0, 1
    if "--shard" in sys.argv:
        i = sys.argv.index("--shard")
        shard_index, shard_total = int(sys.argv[i + 1]), int(sys.argv[i + 2])

    jobs = collect_jobs(shard_index, shard_total)

    print("\n=== SOURCE SUMMARY ===")
    for label, n in SOURCE_SUMMARY.items():
        print(f"  {label:14} {n:6} jobs")
    print(f"  {'TOTAL deduped':14} {len(jobs):6}")

    print("\n=== SAMPLE (first 8) ===")
    for j in jobs[:8]:
        sal = f" | {j['salary_range']}" if j.get("salary_range") else ""
        print(f"  [{j['source']}] {j['job_title']} @ {j['company']} — {j['location']}{sal}")

    if "--json" in sys.argv:
        path = sys.argv[sys.argv.index("--json") + 1]
        with open(path, "w") as f:
            json.dump(jobs, f, indent=2)
        print(f"\nWrote {len(jobs)} jobs to {path}")


if __name__ == "__main__":
    _main()
