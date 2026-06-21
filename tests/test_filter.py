"""
Regression tests for the matching engine (utils/filter.py).

Every test here corresponds to a bug we actually shipped and fixed — if any of
these fail, a real user-facing regression is back. Keep them behavioural (assert
ordering / membership), not exact-score, so they don't break on tuning.
"""
from utils.filter import filter_and_score, deduplicate_across_sources, _extract_salary_lpa, _is_india


def _titles(results):
    return [j["job_title"] for j in results]


# ── The "investment banker → engineers" disaster must never come back ──────────
def test_finance_role_excludes_engineers():
    jobs = [
        {"job_title": "Investment Banking Analyst", "company": "ICICI", "location": "Mumbai", "description_snippet": "M&A"},
        {"job_title": "Security Engineer", "company": "OLX", "location": "Bangalore", "description_snippet": "appsec"},
        {"job_title": "Backend Engineer", "company": "noon", "location": "India", "description_snippet": "apis"},
        {"job_title": "Service Engineer", "company": "X", "location": "TN, IN", "description_snippet": "electrical"},
    ]
    out = _titles(filter_and_score([dict(j) for j in jobs], {"target_roles": ["investment banker"]}))
    assert "Investment Banking Analyst" in out
    assert "Security Engineer" not in out
    assert "Backend Engineer" not in out
    assert "Service Engineer" not in out


def test_ai_engineer_does_not_match_every_engineer():
    jobs = [
        {"job_title": "AI Engineer", "company": "A", "location": "Bangalore", "description_snippet": "llm"},
        {"job_title": "Security Engineer", "company": "B", "location": "Bangalore", "description_snippet": "appsec"},
    ]
    out = _titles(filter_and_score([dict(j) for j in jobs], {"target_roles": ["ai engineer"], "locations": ["bangalore"]}))
    assert "AI Engineer" in out
    assert "Security Engineer" not in out


# ── Role neighbourhood (graph) surfaces adjacent roles ────────────────────────
def test_data_scientist_surfaces_neighbourhood():
    jobs = [
        {"job_title": "Data Scientist", "company": "A", "location": "Bangalore", "description_snippet": "ml"},
        {"job_title": "Machine Learning Engineer", "company": "B", "location": "Bangalore", "description_snippet": "models"},
        {"job_title": "Fund Accountant", "company": "C", "location": "Bangalore", "description_snippet": "nav"},
    ]
    out = _titles(filter_and_score([dict(j) for j in jobs], {"target_roles": ["data scientist"], "locations": ["bangalore"]}))
    assert "Data Scientist" in out
    assert "Machine Learning Engineer" in out   # adjacency
    assert "Fund Accountant" not in out         # different family


# ── Salary parsing (Adzuna absolute-INR must not be discarded) ────────────────
def test_salary_absolute_inr_converted_to_lpa():
    assert 10 < _extract_salary_lpa("1200000-1800000") < 20   # ~15 LPA
    assert _extract_salary_lpa("30-40 LPA") == 35
    assert _extract_salary_lpa("AED 25000/month") == 0.0       # ambiguous monthly → skip


# ── Location: India-default + no false positives ──────────────────────────────
def test_india_detection():
    assert _is_india("Bangalore") is True
    assert _is_india("KA, IN") is True
    assert _is_india("Mumbai, Maharashtra") is True
    assert _is_india("Indianapolis, Indiana") is False
    assert _is_india("New York, NY") is False


def test_foreign_jobs_dropped_by_default_for_india_product():
    jobs = [
        {"job_title": "Data Scientist", "company": "A", "location": "Bangalore", "description_snippet": "ml"},
        {"job_title": "Data Scientist", "company": "B", "location": "New York, NY", "description_snippet": "ml"},
        {"job_title": "Data Scientist", "company": "C", "location": "Remote", "description_snippet": "ml"},
    ]
    # No location set — India-focused product still drops clearly-foreign non-remote.
    locs = [j["location"] for j in filter_and_score([dict(j) for j in jobs], {"target_roles": ["data scientist"]})]
    assert "Bangalore" in locs
    assert "Remote" in locs
    assert "New York, NY" not in locs


# ── Null-safety: must never crash on garbage (new-signup NULL profile etc.) ────
def test_null_profile_and_null_fields_do_not_crash():
    jobs = [
        {"job_title": None, "company": None, "location": None, "description_snippet": None,
         "salary_range": None, "posted_date": None},
        {"job_title": "Data Scientist", "location": "Bangalore"},
    ]
    prof = {"target_roles": None, "locations": None, "industries": None,
            "exclude_companies": None, "salary_floor": None, "resume_text": None}
    out = filter_and_score([dict(j) for j in jobs], prof)   # must not raise
    deduplicate_across_sources(out)                          # must not raise
    assert isinstance(out, list)


# ── Résumé drives the search (no target roles, résumé only) ───────────────────
def test_resume_drives_search():
    resume = ("Investment Banking Analyst with M&A, valuation DCF, capital markets, "
              "pitchbook, transaction advisory experience.")
    jobs = [
        {"job_title": "Investment Banking Analyst", "company": "A", "location": "Mumbai", "description_snippet": "M&A"},
        {"job_title": "Backend Engineer", "company": "B", "location": "Bangalore", "description_snippet": "apis"},
    ]
    out = _titles(filter_and_score([dict(j) for j in jobs], {"target_roles": [], "resume_text": resume}))
    assert "Investment Banking Analyst" in out
    assert "Backend Engineer" not in out


# ── Seniority: a Lead-level user ranks VP above Analyst ───────────────────────
def test_seniority_ranks_to_level():
    jobs = [
        {"job_title": "Investment Banking Analyst", "company": "A", "location": "Mumbai", "description_snippet": "investment banking M&A comps valuation"},
        {"job_title": "Vice President - Investment Banking", "company": "B", "location": "Mumbai", "description_snippet": "investment banking M&A deal execution valuation"},
    ]
    prof = {"target_roles": ["investment banker"], "seniority_level": "lead", "experience_years": 8}
    out = filter_and_score([dict(j) for j in jobs], prof)
    ranks = {j["job_title"]: j["match_score"] for j in out}
    # Both pass the role filter; the Lead-level user should rank the VP above the Analyst.
    assert ranks["Vice President - Investment Banking"] > ranks["Investment Banking Analyst"]


# ── Back office gets its own neighbourhood (not pulled into front office) ──────
def test_back_office_family():
    jobs = [
        {"job_title": "Fund Accountant", "company": "State Street", "location": "Hyderabad, India", "description_snippet": "nav"},
        {"job_title": "AML Analyst", "company": "DB", "location": "Bangalore, India", "description_snippet": "monitoring"},
        {"job_title": "Investment Banking Analyst", "company": "X", "location": "Mumbai", "description_snippet": "M&A"},
    ]
    out = _titles(filter_and_score([dict(j) for j in jobs], {"target_roles": ["fund accountant"]}))
    assert "Fund Accountant" in out
    assert "AML Analyst" in out
    assert "Investment Banking Analyst" not in out   # front office stays separate


def test_front_office_target_excludes_back_office_without_industries():
    # A role-only IB target (no industries set) must NOT pull back-office finance —
    # the sector net is gated behind industries_set. (Locks the TS/Python alignment.)
    jobs = [
        {"job_title": "Investment Banking Analyst", "company": "A", "location": "Mumbai", "description_snippet": "M&A comps"},
        {"job_title": "Fund Accountant", "company": "State Street", "location": "Hyderabad, India", "description_snippet": "nav reconciliations custody"},
        {"job_title": "KYC Analyst", "company": "DB", "location": "Bangalore, India", "description_snippet": "kyc aml onboarding"},
    ]
    out = _titles(filter_and_score([dict(j) for j in jobs], {"target_roles": ["investment banker"]}))
    assert "Investment Banking Analyst" in out
    assert "Fund Accountant" not in out
    assert "KYC Analyst" not in out
