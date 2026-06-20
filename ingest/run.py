"""
Ingestion orchestrator.

collect_jobs() runs every connector (each failsafe — one dead source never stops
the run), normalizes, deduplicates, and returns the pool. SOURCE_SUMMARY records
per-source counts so silent breakage is visible (observability is part of the
foundation, not an afterthought).

CLI:
  python -m ingest.run            # prints summary + samples
  python -m ingest.run --json out.json
"""
import json
import logging
import sys
from typing import Callable, Dict, List

from .connectors import greenhouse, lever, ashby, aggregators
from .dedup import deduplicate

logger = logging.getLogger("ingest")

# (label, fetch_fn)
SOURCES: List[tuple] = [
    ("greenhouse",  greenhouse.fetch),
    ("lever",       lever.fetch),
    ("ashby",       ashby.fetch),
    ("aggregators", aggregators.fetch),
]

# Filled in by collect_jobs(): {source_label: raw_count}
SOURCE_SUMMARY: Dict[str, int] = {}


def collect_jobs() -> List[Dict]:
    """Run all connectors, normalize + dedup, return the job pool."""
    SOURCE_SUMMARY.clear()
    raw: List[Dict] = []
    for label, fn in SOURCES:
        try:
            jobs = fn()
        except Exception as e:  # belt-and-suspenders; connectors already failsafe
            logger.error(f"[{label}] crashed: {e}")
            jobs = []
        SOURCE_SUMMARY[label] = len(jobs)
        logger.info(f"[{label}] {len(jobs)} jobs")
        raw.extend(jobs)

    deduped = deduplicate(raw)
    logger.info(f"[ingest] {len(raw)} raw -> {len(deduped)} after dedup")
    return deduped


def _main():
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s — %(message)s")
    jobs = collect_jobs()

    print("\n=== SOURCE SUMMARY ===")
    for label, n in SOURCE_SUMMARY.items():
        print(f"  {label:14} {n:5} raw")
    print(f"  {'TOTAL deduped':14} {len(jobs):5}")

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
