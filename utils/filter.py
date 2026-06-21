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

from . import role_graph

logger = logging.getLogger(__name__)

# A weighted role match must clear this to count as relevant. A close neighbour
# (e.g. ML Engineer ≈ Data Scientist, weight ~0.6–0.9) clears it; a generic-only
# or very distant match does not.
ROLE_PASS = 0.33

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


# Words that share a 5-char prefix but are DIFFERENT domains — give them distinct
# stems so they don't false-match (the 5-char prefix is tuned for science↔scientist
# and can't be lengthened without breaking that, so we override the few offenders).
_STEM_OVERRIDES = {
    "marketplace": "mktpl",   # vs marketing → "marke"
    "production":  "prodn",   # vs product/productivity → "produ"
}

def _stem(w: str) -> str:
    """Crude prefix stem so word-forms unify: science/scientist/scientific → 'scien',
    analyst/analytics/analysis → 'analy', manager/management → 'manag'. Cheap, no LLM —
    it won't catch true synonyms (ML eng ≈ data scientist) or typos; that's Stage-2's job.
    A small override table separates same-prefix-but-different-domain words
    (marketing vs marketplace, product vs production)."""
    if w in _STEM_OVERRIDES:
        return _STEM_OVERRIDES[w]
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
    # broadened — common foreign hubs seen in ATS/aggregator feeds
    "mexico", "brazil", "são paulo", "sao paulo", "argentina", "colombia",
    "philippines", "manila", "jakarta", "indonesia", "vietnam", "hanoi",
    "warsaw", "poland", "madrid", "spain", "barcelona", "france", "italy",
    " canada", "australia", "japan", "tokyo", "china", "shanghai", "beijing",
    "hong kong", "kuala lumpur", "malaysia", "thailand", "bangkok", "egypt",
    "nigeria", "kenya", "south africa", "ireland", "portugal", "lisbon",
    "stockholm", "sweden", "zurich", "switzerland", "austria", "belgium",
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
    # NOTE: `.get(k, [])` returns None when the column exists but is NULL (the case
    # for freshly-signed-up users whose profile row was created by the DB trigger
    # without these fields). Use `or []` so a NULL never crashes the whole user's
    # run (which would silently leave them with no feed).
    target_roles      = [r.lower() for r in (profile.get("target_roles") or [])]
    industries        = [i.lower() for i in (profile.get("industries") or [])]

    # ── Role-family expansion (the neighbourhood graph) ──
    # Each target role activates a weighted neighbourhood: target = 1.0, adjacent
    # roles < 1.0. We pre-stem every expanded role once. Unknown roles still work
    # (they expand to just themselves at weight 1.0).
    resume_text  = profile.get("resume_text") or ""
    # The résumé DRIVES the search: roles detected in it augment the target roles
    # (at a slightly lower weight so explicitly-typed roles still dominate). This
    # also makes the feed work for a user who only uploaded a résumé.
    resume_roles = role_graph.roles_from_text(resume_text) if resume_text else []

    expanded = role_graph.expand_roles(target_roles)   # {role_phrase: weight}
    for phrase, weight in role_graph.expand_roles(resume_roles).items():
        expanded[phrase] = max(expanded.get(phrase, 0.0), weight * 0.9)
    expanded_stems = []                                # [(phrase, weight, [stems])]
    for phrase, weight in expanded.items():
        stems = [_stem(w) for w in phrase.split() if len(w) >= 2]
        if stems:
            expanded_stems.append((phrase, weight, stems))
    target_canon = {role_graph.normalize_role(r) for r in target_roles}

    # ── Sector / domain layer ── (résumé roles count toward sector detection too)
    sectors        = role_graph.sectors_for(target_roles + resume_roles, industries)
    sect_kw        = role_graph.sector_keywords(sectors)
    industries_set = bool(industries)

    locations         = [l.lower() for l in (profile.get("locations") or [])]
    exclude_companies = [c.lower() for c in (profile.get("exclude_companies") or [])]
    salary_floor      = profile.get("salary_floor", 0) or 0
    resume_stems      = _stems(profile.get("resume_text") or "")
    has_resume        = len(resume_stems) >= 12
    W                 = _WEIGHTS_RESUME if has_resume else _WEIGHTS_NO_RESUME

    results: List[Dict] = []

    for job in jobs:
        title    = (job.get("job_title") or "").lower()
        company  = (job.get("company") or "").lower()
        location = (job.get("location") or "").lower()
        jd       = (job.get("description_snippet") or "").lower()
        salary_str = job.get("salary_range") or ""
        title_stems = _mstems(title)            # role-matching tokens (keep short words)
        jd_stems    = _mstems(jd)
        text_stems  = title_stems | jd_stems    # title+JD, for role/fuzzy matching

        blob = title + " " + jd + " " + company

        # Best WEIGHTED role fit over the expanded neighbourhood. Returns
        # (effective_score, best_role_phrase). A generic word alone never counts.
        def role_fit(stem_set: set):
            best_eff, best_role = 0.0, None
            for phrase, weight, rs in expanded_stems:
                matched = [s for s in rs if s in stem_set]
                if not matched:
                    continue
                distinctive = [s for s in matched if s not in _GENERIC_ROLE_STEMS]
                full = len(matched) == len(rs)
                if full or distinctive:          # generic word alone ≠ a match
                    eff = (len(matched) / len(rs)) * weight
                    if eff > best_eff:
                        best_eff, best_role = eff, phrase
            return best_eff, best_role

        # ── Hard filters ──
        if any(ex in company for ex in exclude_companies):
            continue

        sector_hit = bool(sect_kw) and any(kw in blob for kw in sect_kw)

        # A job qualifies if it matches the role neighbourhood OR (when the user
        # set industries) the sector net. This is what lets "any finance role"
        # work and lets a Data Scientist target surface ML/Analytics jobs.
        if expanded_stems or sect_kw:
            text_eff, _ = role_fit(text_stems)
            role_pass = text_eff >= ROLE_PASS
            if not (role_pass or (industries_set and sector_hit)):
                continue
        # Location: this is an India-focused product, so we drop clearly-overseas,
        # non-remote roles by DEFAULT (even when the user hasn't set a location —
        # otherwise the feed fills with US/Mexico/London jobs). India / remote /
        # any preferred location always win, so a Bangalore job that merely
        # mentions an overseas team isn't dropped as "foreign".
        matched_loc = bool(locations) and any(loc in location for loc in locations)
        is_remote   = any(k in location for k in ("remote", "wfh", "anywhere"))
        is_foreign  = any(h in location for h in _FOREIGN_HINTS)
        if is_foreign and not (matched_loc or is_remote or _is_india(location)):
            continue
        salary_lpa = _extract_salary_lpa(salary_str)
        if salary_lpa > 0 and salary_floor > 0 and salary_lpa < salary_floor * 0.8:
            continue

        reasons: List[str] = []

        # 1. Title role fit (0..1, weighted by neighbourhood closeness)
        if expanded_stems:
            title_score, title_role = role_fit(title_stems)
            if title_score >= ROLE_PASS:
                if title_role and role_graph.normalize_role(title_role) not in target_canon:
                    reasons.append(f"Related role: {title_role.title()}")
                else:
                    reasons.append("Title matches your roles")
        else:
            title_score, title_role = 0.5, None  # no roles set → neutral

        # 2. JD role fit (0..1)
        if expanded_stems and jd:
            jd_score, _ = role_fit(jd_stems)
            if jd_score >= ROLE_PASS and "Related role" not in " ".join(reasons) \
               and "Title matches your roles" not in reasons:
                reasons.append("Description aligns with your roles")
        else:
            jd_score = 0.5

        # 3. Sector / domain fit (0..1) — the keyword net (esp. for finance)
        if sect_kw:
            ind_score = 1.0 if sector_hit else 0.3
            if sector_hit:
                for s in sectors:
                    if any(kw in blob for kw in role_graph.SECTORS.get(s, set())):
                        reasons.append(f"{s.title()} sector")
                        break
        else:
            ind_score = 1.0  # no sector specified → don't penalise

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
            re.sub(r'[^a-z0-9 ]', '', (job.get("job_title") or "").lower()).strip(),
            re.sub(r'[^a-z0-9 ]', '', (job.get("company") or "").lower()).strip(),
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
