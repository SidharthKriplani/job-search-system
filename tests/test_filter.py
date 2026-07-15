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
    res = filter_and_score([dict(j) for j in jobs], {"target_roles": ["fund accountant"]})
    out = [j["job_title"] for j in res]
    assert "Fund Accountant" in out
    assert "AML Analyst" in out
    # Finance is connected, so IB may also appear (cross-linked) — but the exact
    # back-office target ranks above the cross-office IB role.
    score = {j["job_title"]: j["match_score"] for j in res}
    assert score["Fund Accountant"] > score.get("Investment Banking Analyst", 0)


def test_finance_is_one_connected_space():
    # Finance front/middle/back office are adjacent careers — an investment-banking
    # target should ALSO surface back/middle-office finance (ranked lower), not show
    # an empty feed. This is the "stop forcing front-vs-back on the user" fix.
    jobs = [
        {"job_title": "Investment Banking Analyst", "company": "A", "location": "Mumbai", "description_snippet": "M&A comps"},
        {"job_title": "Fund Accountant", "company": "State Street", "location": "Hyderabad, India", "description_snippet": "nav"},
        {"job_title": "KYC Analyst", "company": "DB", "location": "Bangalore, India", "description_snippet": "kyc aml"},
        {"job_title": "Backend Engineer", "company": "Z", "location": "Bangalore", "description_snippet": "apis"},
    ]
    out = filter_and_score([dict(j) for j in jobs], {"target_roles": ["investment banker"]})
    titles = [j["job_title"] for j in out]
    assert "Investment Banking Analyst" in titles
    assert "Fund Accountant" in titles     # cross-linked finance now included
    assert "KYC Analyst" in titles
    assert "Backend Engineer" not in titles  # still not finance
    # but the exact-role IB match ranks above the cross-office ones
    score = {j["job_title"]: j["match_score"] for j in out}
    assert score["Investment Banking Analyst"] > score["Fund Accountant"]


def test_stale_jobs_dropped_by_max_age():
    # The product promise is RECENT jobs: postings older than MAX_JOB_AGE_DAYS
    # (default 90) are dropped up front; undated jobs are kept (neutral recency).
    from datetime import date, timedelta
    fresh = (date.today() - timedelta(days=5)).isoformat()
    stale = (date.today() - timedelta(days=200)).isoformat()
    jobs = [
        {"job_title": "Investment Banking Analyst", "company": "A", "location": "Mumbai",
         "description_snippet": "M&A", "posted_date": fresh},
        {"job_title": "Investment Banking Analyst", "company": "B", "location": "Mumbai",
         "description_snippet": "M&A", "posted_date": stale},
        {"job_title": "Investment Banking Analyst", "company": "C", "location": "Mumbai",
         "description_snippet": "M&A", "posted_date": None},
    ]
    out = filter_and_score([dict(j) for j in jobs], {"target_roles": ["investment banker"]})
    companies = {j["company"] for j in out}
    assert "A" in companies          # fresh kept
    assert "B" not in companies      # stale dropped
    assert "C" in companies          # undated kept
