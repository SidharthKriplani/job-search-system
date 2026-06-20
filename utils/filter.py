"""
Job Filter + Scorer
--------------------
Applies per-user filters (role keywords, salary, location, seniority)
and computes a match_score (0–1) for display ranking.

Called after scrapers return raw jobs, before upsert.
"""

import re
import logging
from datetime import datetime, date
from typing import List, Dict, Tuple, Optional

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

    # Detect monthly / raw-currency amounts (e.g. "AED 25000/month").
    # We can't reliably convert these to INR LPA without an FX rate, and the
    # old code inflated them (25000 -> 275 "LPA"), which broke salary scoring
    # and made every GCC job falsely clear the salary floor. Treat as
    # "salary unknown" (0.0) so the salary filter is skipped rather than wrong.
    if any(v > 500 for v in vals):
        return 0.0

    if len(vals) >= 2:
        return (vals[0] + vals[1]) / 2
    return vals[0]


# ─── Recency helper ───────────────────────────────────────────────────────────

def _recency_score(posted_date: Optional[str]) -> Tuple[float, str]:
    """0..1 by how recently the job was posted, plus a human label."""
    if not posted_date:
        return 0.5, ""
    try:
        d = datetime.fromisoformat(str(posted_date)[:10]).date()
        days = (date.today() - d).days
    except Exception:
        return 0.5, ""
    if days <= 3:  return 1.0, "Posted in last 3 days"
    if days <= 7:  return 0.9, "Posted this week"
    if days <= 14: return 0.7, "Posted recently"
    if days <= 30: return 0.5, ""
    return 0.25, ""


# ─── Main filter + scorer (profile-driven, JD-aware) ──────────────────────────

# Score weights (sum to 1.0). Title + JD role fit dominate; the rest differentiate.
_W_TITLE, _W_JD, _W_IND, _W_LOC, _W_SAL, _W_REC = 0.30, 0.25, 0.15, 0.15, 0.08, 0.07


def filter_and_score(jobs: List[Dict], profile: Dict) -> List[Dict]:
    """
    Filter jobs against the user's profile and compute a JD-aware match_score.

    Hard filters drop jobs that can't be relevant; the score (0..1) then ranks
    what's left. The score reads the job DESCRIPTION, not just the title — a role
    keyword in the JD counts, and industry/skill terms in the JD raise the score.
    Returns jobs sorted by match_score desc.
    """
    target_roles      = [r.lower() for r in profile.get("target_roles", [])]
    # Per-role word lists (for best-match scoring) + a flat set (for the hard filter).
    roles_words       = [[w for w in r.split() if len(w) > 2] for r in target_roles]
    roles_words       = [rw for rw in roles_words if rw]
    role_words        = sorted({w for rw in roles_words for w in rw})
    locations         = [l.lower() for l in profile.get("locations", [])]
    industries        = [i.lower() for i in profile.get("industries", [])]
    exclude_companies = [c.lower() for c in profile.get("exclude_companies", [])]
    salary_floor      = profile.get("salary_floor", 0) or 0

    results: List[Dict] = []

    for job in jobs:
        title    = job.get("job_title", "").lower()
        company  = job.get("company", "").lower()
        location = job.get("location", "").lower()
        jd       = (job.get("description_snippet") or "").lower()
        salary_str = job.get("salary_range") or ""
        text     = f"{title} {jd}"  # title + JD, for JD-aware matching

        # ── Hard filters ──
        if any(ex in company for ex in exclude_companies):
            continue
        # Role must appear in the title OR the JD (JD-aware — not title-only).
        if role_words and not any(w in text for w in role_words):
            continue
        salary_lpa = _extract_salary_lpa(salary_str)
        if salary_lpa > 0 and salary_floor > 0 and salary_lpa < salary_floor * 0.8:
            continue

        reasons: List[str] = []

        # Best fraction of any ONE target role's words present in `s`.
        def best_role_fit(s: str) -> float:
            best = 0.0
            for rw in roles_words:
                best = max(best, sum(1 for w in rw if w in s) / len(rw))
            return best

        # 1. Title role fit (0..1) — against the best-matching single role
        if roles_words:
            title_score = best_role_fit(title)
            if title_score >= 0.5:
                reasons.append("Title matches your roles")
        else:
            title_score = 0.5  # no roles set → can't assess, stay neutral

        # 2. JD role fit (0..1) — M3: depends on the job description
        if roles_words and jd:
            jd_score = best_role_fit(jd)
            if jd_score >= 0.5:
                reasons.append("Description aligns with your roles")
        else:
            jd_score = 0.5

        # 3. Industry / domain terms in title+JD (0..1) — M3
        if industries:
            ind_hits = sum(1 for i in industries if i in text)
            ind_score = min(ind_hits / len(industries), 1.0)
            if ind_hits:
                reasons.append("Matches your industry")
        else:
            ind_score = 1.0  # not specified → don't penalise

        # 4. Location fit (0..1)
        if locations:
            if any(loc in location for loc in locations):
                loc_score = 1.0; reasons.append("Preferred location")
            elif any(k in location for k in ("remote", "wfh", "anywhere")):
                loc_score = 0.9; reasons.append("Remote")
            elif "india" in location:
                loc_score = 0.6
            else:
                loc_score = 0.15
        else:
            loc_score = 1.0

        # 5. Salary fit (0..1)
        if salary_lpa > 0 and salary_floor > 0:
            sal_score = min(salary_lpa / salary_floor, 1.0)
            if salary_lpa >= salary_floor:
                reasons.append(f"Salary ~{salary_lpa:.0f}L meets floor")
        else:
            sal_score = 0.6  # undisclosed → neutral

        # 6. Recency (0..1)
        rec_score, rec_label = _recency_score(job.get("posted_date"))
        if rec_label:
            reasons.append(rec_label)

        score = (
            _W_TITLE * title_score + _W_JD * jd_score + _W_IND * ind_score +
            _W_LOC * loc_score + _W_SAL * sal_score + _W_REC * rec_score
        )

        job["match_score"]   = round(score, 3)
        job["match_reasons"] = reasons[:4]
        results.append(job)

    results.sort(key=lambda j: j["match_score"], reverse=True)
    top = results[0]["match_score"] if results else 0
    logger.info(f"[Filter] {len(results)}/{len(jobs)} passed | top score {top}")
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
