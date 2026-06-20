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
    mx = max(vals)

    # Disambiguate units by magnitude:
    #  • >= 1,00,000  → absolute annual INR (e.g. Adzuna India "1200000-1800000")
    #                   → convert to LPA by /100000. (Previously these were ALL
    #                     discarded by a `v > 500` guard, so every Adzuna India
    #                     salary was silently dropped from scoring.)
    #  • 500–99,999   → ambiguous monthly / foreign-currency (e.g. "AED 25000/mo");
    #                   we can't convert without an FX rate → treat as unknown.
    #  • < 500        → already in LPA units (e.g. "30-40 LPA").
    if mx >= 100000:
        vals = [v / 100000 for v in vals]
    elif mx > 500:
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


# ─── Résumé tokenisation (résumé-aware matching) ──────────────────────────────

_STOPWORDS = {
    "the","and","for","with","you","our","your","are","will","that","this","from",
    "have","has","work","working","team","teams","role","roles","jobs","that","they",
    "their","who","what","when","where","all","any","can","new","using","use","into",
    "experience","years","year","strong","ability","including","across","within",
    "skills","knowledge","required","preferred","plus","etc","per","via","such",
    "company","companies","candidate","candidates","opportunity","looking","join","also",
}

def _tokens(text: str) -> set:
    """Significant lowercase tokens (len>=4, no stopwords) — for résumé overlap."""
    return {w for w in re.findall(r"[a-z][a-z0-9+#.]{3,}", (text or "").lower())
            if w not in _STOPWORDS}


def _stem(w: str) -> str:
    """Crude prefix stem so word-forms unify: science/scientist/scientific → 'scien',
    analyst/analytics/analysis → 'analy', manager/management → 'manag'. Cheap, no LLM —
    it won't catch true synonyms (ML eng ≈ data scientist) or typos; that's Stage-2's job."""
    return w[:5] if len(w) >= 6 else w


def _stems(text: str) -> set:
    return {_stem(w) for w in _tokens(text)}


# India detection by TOKEN (not substring) so "Indianapolis" ≠ India and a job
# that merely mentions a foreign city in a hybrid location isn't misread.
_INDIA_TOKENS = {
    "india", "bharat", "bangalore", "bengaluru", "mumbai", "delhi", "ncr",
    "hyderabad", "chennai", "pune", "kolkata", "gurgaon", "gurugram", "noida",
    "ahmedabad", "jaipur", "kochi", "chandigarh", "indore", "nashik",
    "coimbatore", "thiruvananthapuram", "vadodara", "nagpur", "surat",
}

def _is_india(location: str) -> bool:
    loc = (location or "").lower()
    toks = set(re.split(r"[^a-z0-9]+", loc))
    if toks & _INDIA_TOKENS:
        return True
    # Indeed India formats state rows as "<STATE>, IN" (e.g. "KA, IN", "MH, IN").
    if re.search(r",\s*in\b", loc):
        return True
    return False


# ─── Role-matching tokens (keep short, meaningful terms like "ai", "ml", "qa") ──
# The résumé tokenizer above drops <4-char words, which silently turned the role
# "ai engineer" into just "engineer" — so every Security/Backend/Service Engineer
# matched. For ROLE matching we keep 2+ char tokens.
def _mtokens(text: str) -> set:
    return {w for w in re.findall(r"[a-z][a-z0-9+#.]{1,}", (text or "").lower())
            if w not in _STOPWORDS}


def _mstems(text: str) -> set:
    return {_stem(w) for w in _mtokens(text)}


# Stemmed role words too generic to qualify a match on their own. "Engineer",
# "manager", "analyst"… appear in thousands of unrelated titles, so a multi-word
# role like "ai engineer" needs its DISTINCTIVE word ("ai") to also be present.
_GENERIC_ROLE_STEMS = {
    "engin", "manag", "analy", "devel", "lead", "senio", "junio", "assoc",
    "speci", "consu", "offic", "execu", "head", "staff", "princ", "direc",
    "inter", "train", "exper", "profe", "techn", "suppo", "opera",
}

# Clearly-foreign locations — used to drop overseas, non-remote jobs when the
# user has set India/city preferences. Conservative on purpose (full names, not
# 2-letter codes) so we never accidentally nuke Indian listings. Heuristic, not
# a real geocoder; proper location normalisation is a later step.
_FOREIGN_HINTS = (
    "new york", "san francisco", " seattle", " austin", " boston", " chicago",
    "los angeles", " denver", " atlanta", "new jersey", " texas", "california",
    "london", " dublin", " berlin", "amsterdam", " paris", " munich",
    "toronto", " sydney", "tel aviv", "united states", " usa", " u.s.",
    "united kingdom", " u.k.", "germany", "singapore", "netherlands",
)


# ─── Main filter + scorer (profile-driven, JD-aware, résumé-aware) ────────────

# Component weights. With a résumé, the résumé drives the score; without, role fit does.
_WEIGHTS_RESUME    = dict(title=0.20, jd=0.15, ind=0.10, loc=0.15, sal=0.08, rec=0.07, resume=0.25)
_WEIGHTS_NO_RESUME = dict(title=0.30, jd=0.25, ind=0.15, loc=0.15, sal=0.08, rec=0.07, resume=0.0)


def filter_and_score(jobs: List[Dict], profile: Dict) -> List[Dict]:
    """
    Filter jobs against the user's profile and compute a JD-aware match_score.

    Hard filters drop jobs that can't be relevant; the score (0..1) then ranks
    what's left. The score reads the job DESCRIPTION, not just the title — a role
    keyword in the JD counts, and industry/skill terms in the JD raise the score.
    Returns jobs sorted by match_score desc.
    """
    target_roles      = [r.lower() for r in profile.get("target_roles", [])]
    # Per-role word lists (for best-match scoring). Keep 2+ char words so short,
    # meaningful terms ("ai", "ml", "qa", "ux") survive — they're often the most
    # distinctive part of the role.
    roles_words       = [[w for w in r.split() if len(w) >= 2] for r in target_roles]
    roles_words       = [rw for rw in roles_words if rw]
    # Stemmed role words — so "data science" matches "Data Scientist", etc.
    roles_stems       = [[_stem(w) for w in rw] for rw in roles_words]
    locations         = [l.lower() for l in profile.get("locations", [])]
    industries        = [i.lower() for i in profile.get("industries", [])]
    exclude_companies = [c.lower() for c in profile.get("exclude_companies", [])]
    salary_floor      = profile.get("salary_floor", 0) or 0
    resume_stems      = _stems(profile.get("resume_text") or "")
    has_resume        = len(resume_stems) >= 12
    W                 = _WEIGHTS_RESUME if has_resume else _WEIGHTS_NO_RESUME

    results: List[Dict] = []

    for job in jobs:
        title    = job.get("job_title", "").lower()
        company  = job.get("company", "").lower()
        location = job.get("location", "").lower()
        jd       = (job.get("description_snippet") or "").lower()
        salary_str = job.get("salary_range") or ""
        title_stems = _mstems(title)            # role-matching tokens (keep short words)
        jd_stems    = _mstems(jd)
        text_stems  = title_stems | jd_stems    # title+JD, for role/fuzzy matching

        # Best fraction of any ONE role's words present, but only counts as a real
        # match if a DISTINCTIVE (non-generic) word is present, or the whole role
        # is present. Returns (fraction, qualifies).
        def role_fit(stem_set: set):
            best, ok = 0.0, False
            for rs in roles_stems:
                matched = [s for s in rs if s in stem_set]
                if not matched:
                    continue
                distinctive = [s for s in matched if s not in _GENERIC_ROLE_STEMS]
                full = len(matched) == len(rs)
                if full or distinctive:          # generic word alone ≠ a match
                    ok = True
                    best = max(best, len(matched) / len(rs))
            return best, ok

        # ── Hard filters ──
        if any(ex in company for ex in exclude_companies):
            continue
        # A target role must really match the title or JD (not just a generic word).
        if roles_stems:
            _, role_ok = role_fit(text_stems)
            if not role_ok:
                continue
        # Location: when the user sets preferences, drop clearly-overseas,
        # non-remote roles (keeps India + remote + anything we can't classify).
        # India/remote/preferred always win, so a Bangalore job that merely
        # mentions an overseas team isn't dropped as "foreign".
        if locations:
            matched_loc = any(loc in location for loc in locations)
            is_remote   = any(k in location for k in ("remote", "wfh", "anywhere"))
            is_foreign  = any(h in location for h in _FOREIGN_HINTS)
            if is_foreign and not (matched_loc or is_remote or _is_india(location)):
                continue
        salary_lpa = _extract_salary_lpa(salary_str)
        if salary_lpa > 0 and salary_floor > 0 and salary_lpa < salary_floor * 0.8:
            continue

        reasons: List[str] = []

        # 1. Title role fit (0..1) — against the best-matching single role
        if roles_stems:
            title_score, _ = role_fit(title_stems)
            if title_score >= 0.5:
                reasons.append("Title matches your roles")
        else:
            title_score = 0.5  # no roles set → can't assess, stay neutral

        # 2. JD role fit (0..1) — M3: depends on the job description
        if roles_stems and jd:
            jd_score, _ = role_fit(jd_stems)
            if jd_score >= 0.5:
                reasons.append("Description aligns with your roles")
        else:
            jd_score = 0.5

        # 3. Industry / domain terms in title+JD (0..1) — M3
        if industries:
            text = title + " " + jd
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
            elif _is_india(location):
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

        # 7. Résumé fit (0..1) — how much of this job's vocabulary the résumé covers
        resume_score = 0.0
        if has_resume:
            matched = text_stems & resume_stems
            resume_score = min(len(matched) / max(len(text_stems), 1) * 1.6, 1.0)
            if matched and resume_score >= 0.35:
                top3 = sorted(matched, key=len, reverse=True)[:3]
                reasons.insert(0, "Résumé match: " + ", ".join(top3))

        score = (
            W["title"] * title_score + W["jd"] * jd_score + W["ind"] * ind_score +
            W["loc"] * loc_score + W["sal"] * sal_score + W["rec"] * rec_score +
            W["resume"] * resume_score
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
