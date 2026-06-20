"""
Job Filter + Scorer
--------------------
Applies per-user filters (role keywords, salary, location, seniority)
and computes a match_score (0–1) for display ranking.

Called after scrapers return raw jobs, before upsert.
"""

import re
import logging
from typing import List, Dict, Tuple

logger = logging.getLogger(__name__)

# ─── Salary parsing ──────────────────────────────────────────────────────────

def _extract_salary_lpa(salary_str: str) -> float:
    """Best-effort extraction of midpoint salary in LPA from a salary string."""
    if not salary_str:
        return 0.0

    # Patterns: "30-40 LPA", "₹30L–₹40L", "30 to 45 lakhs", "AED 25000/month"
    nums = re.findall(r'\d+(?:\.\d+)?', salary_str.replace(",", ""))
    if not nums:
        return 0.0

    vals = [float(n) for n in nums]

    # Detect if values are in monthly (likely if > 500 — currency amount)
    if any(v > 500 for v in vals):
        # Convert approximate monthly to LPA (×12 / 100000 * exchange estimate)
        # AED: 1 AED ≈ 0.022 LPA roughly; just flag as high if monthly > 5000
        return sum(vals) / len(vals) / 100  # rough normalisation

    if len(vals) >= 2:
        return (vals[0] + vals[1]) / 2
    return vals[0]


# ─── Main filter + scorer ─────────────────────────────────────────────────────

def filter_and_score(jobs: List[Dict], profile: Dict) -> List[Dict]:
    """
    Filter jobs against user profile and compute match_score.
    Returns only jobs that pass all hard filters, sorted by match_score desc.
    """
    target_roles    = [r.lower() for r in profile.get("target_roles", [])]
    salary_floor    = profile.get("salary_floor", 0)           # LPA
    locations       = [l.lower() for l in profile.get("locations", [])]
    exclude_companies = [c.lower() for c in profile.get("exclude_companies", [])]
    industries      = [i.lower() for i in profile.get("industries", [])]

    results = []

    for job in jobs:
        title_lower    = job.get("job_title", "").lower()
        company_lower  = job.get("company", "").lower()
        location_lower = job.get("location", "").lower()
        salary_str     = job.get("salary_range") or ""

        # ── Hard filters ──

        # 1. Excluded companies
        if any(ex in company_lower for ex in exclude_companies):
            continue

        # 2. Role keyword match (at least one target role keyword must appear)
        if target_roles:
            role_match = any(
                kw in title_lower
                for role in target_roles
                for kw in role.split()
                if len(kw) > 2  # skip short words like "of", "in"
            )
            if not role_match:
                continue

        # 3. Salary floor (only if salary is disclosed and non-zero)
        salary_lpa = _extract_salary_lpa(salary_str)
        if salary_lpa > 0 and salary_floor > 0 and salary_lpa < salary_floor * 0.8:
            # 20% tolerance below floor (some listings show base not total)
            continue

        # ── Scoring ──
        score = 0.0
        reasons = []

        # Role match score (0–0.4)
        best_role_score = 0.0
        for role in target_roles:
            role_words = [w for w in role.split() if len(w) > 2]
            matched = sum(1 for w in role_words if w in title_lower)
            ratio = matched / len(role_words) if role_words else 0
            if ratio > best_role_score:
                best_role_score = ratio
        score += best_role_score * 0.4
        if best_role_score > 0.5:
            reasons.append("Strong role match")

        # Location match (0–0.3)
        if locations:
            loc_match = any(loc in location_lower for loc in locations) or \
                        "remote" in location_lower or "wfh" in location_lower or \
                        "anywhere" in location_lower
            if loc_match:
                score += 0.3
                reasons.append("Location match")
        else:
            score += 0.3  # no location filter = full score

        # Salary match (0–0.2)
        if salary_lpa > 0 and salary_floor > 0:
            ratio = min(salary_lpa / salary_floor, 1.5)
            score += min(ratio * 0.2, 0.2)
            if salary_lpa >= salary_floor:
                reasons.append(f"Salary {salary_lpa:.0f}L meets floor")

        # Source signal (0–0.1)
        # iimjobs and ATS sources are higher signal
        high_signal_sources = {"iimjobs", "workday", "greenhouse", "lever"}
        if job.get("source") in high_signal_sources:
            score += 0.1
            reasons.append("High-signal source")

        job["match_score"]   = round(score, 3)
        job["match_reasons"] = reasons
        results.append(job)

    # Sort by match_score descending
    results.sort(key=lambda j: j["match_score"], reverse=True)

    logger.info(f"[Filter] {len(results)}/{len(jobs)} jobs passed filters")
    return results


def deduplicate_across_sources(jobs: List[Dict]) -> List[Dict]:
    """
    Remove cross-source duplicates (same job posted on Naukri + Gmail + Foundit).
    Dedup key: (normalised_title, normalised_company).
    Keeps the highest match_score version.
    """
    seen: Dict[Tuple[str, str], Dict] = {}

    for job in jobs:
        key = (
            re.sub(r'[^a-z0-9 ]', '', job.get("job_title", "").lower()).strip(),
            re.sub(r'[^a-z0-9 ]', '', job.get("company", "").lower()).strip(),
        )
        if key not in seen:
            seen[key] = job
        else:
            # Keep higher match_score
            if job.get("match_score", 0) > seen[key].get("match_score", 0):
                seen[key] = job

    unique_jobs = list(seen.values())
    logger.info(f"[Dedup] {len(jobs)} → {len(unique_jobs)} after cross-source dedup")
    return unique_jobs
