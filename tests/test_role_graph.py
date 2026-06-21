"""Tests for the role-family graph + seniority logic (utils/role_graph.py)."""
from utils.role_graph import (
    expand_roles, normalize_role, roles_from_text, sectors_for,
    job_level, user_level, level_fit,
)


def test_aliases_resolve():
    assert normalize_role("ib") == "investment banker"
    assert normalize_role("ds") == "data scientist"
    assert normalize_role("ml") == "machine learning engineer"
    assert normalize_role("kyc") == "kyc analyst"


def test_expand_includes_neighbourhood_with_decay():
    e = expand_roles(["data scientist"])
    assert e["data scientist"] == 1.0
    assert "machine learning engineer" in e
    assert e["machine learning engineer"] < 1.0          # decayed neighbour


def test_expand_finance_front_office():
    e = expand_roles(["investment banker"])
    assert e["investment banker"] == 1.0
    assert "mergers and acquisitions" in e
    assert "equity research analyst" in e


def test_resume_role_detection():
    txt = "Investment Banking Analyst, M&A, capital markets, valuation, pitchbook."
    roles = roles_from_text(txt)
    assert "investment banking analyst" in roles or "investment banker" in roles
    assert "mergers and acquisitions" in roles


def test_finance_sector_auto_activates_but_tech_does_not():
    assert "finance" in sectors_for(["investment banker"], [])
    assert "tech" not in sectors_for(["data scientist"], [])   # titles carry tech


def test_job_and_user_level():
    assert job_level("Investment Banking Analyst") == 1
    assert job_level("Associate - Deal Advisory") == 2
    assert job_level("Vice President - M&A") == 4
    assert job_level("Managing Director") == 5
    assert user_level({"seniority_level": "lead"}) == 4
    assert user_level({"experience_years": 8}) == 3          # years fallback
    assert user_level({}) is None


def test_level_fit_penalises_overqualified_more():
    # user = lead (4); analyst (1) is further-down, VP (4) is exact.
    assert level_fit(4, 4) > level_fit(4, 1)
    # overqualified (job below) penalised harder than a stretch up of same gap
    assert level_fit(4, 2) < level_fit(2, 4)
