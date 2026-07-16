"""
Structural guards for the ingestion registry + connectors (no network).

These catch malformed registry entries (the kind that silently break a source)
without hitting any live API — CI stays fast and offline-safe. Live verification
of each endpoint is done manually when adding it.
"""
from ingest import registry
from ingest.connectors import oracle, smartrecruiters, workday


def test_workday_registry_shape():
    assert registry.WORKDAY, "WORKDAY registry is empty"
    for row in registry.WORKDAY:
        assert len(row) == 4, f"WORKDAY entry must be (tenant, wd, site, display): {row}"
        assert all(isinstance(x, str) and x for x in row), f"empty field in {row}"


def test_oracle_registry_shape():
    assert registry.ORACLE, "ORACLE registry is empty"
    for row in registry.ORACLE:
        assert len(row) == 3, f"ORACLE entry must be (host, site, display): {row}"
        host, site, disp = row
        assert host.endswith("oraclecloud.com"), f"suspicious ORC host: {host}"
        assert site.startswith("CX_"), f"ORC site should be CX_*: {site}"


def test_smartrecruiters_registry_shape():
    for row in registry.SMARTRECRUITERS:
        assert len(row) == 2, f"SR entry must be (company_id, display): {row}"
        assert all(isinstance(x, str) and x for x in row)


def test_connectors_are_callable():
    assert callable(oracle.fetch_company)
    assert callable(smartrecruiters.fetch_company)
    assert callable(workday.fetch_company)


# ── Workable / BambooHR / harvested-Workday (added 2026-07-15) ─────────────────

def test_workable_registry_shape():
    assert registry.WORKABLE, "WORKABLE registry is empty"
    for row in registry.WORKABLE:
        assert len(row) == 2, f"WORKABLE entry must be (slug, display): {row}"
        assert all(isinstance(x, str) and x for x in row)


def test_bamboohr_registry_shape():
    assert registry.BAMBOOHR, "BAMBOOHR registry is empty"
    for row in registry.BAMBOOHR:
        assert len(row) == 2, f"BAMBOOHR entry must be (slug, display): {row}"
        assert all(isinstance(x, str) and x for x in row)


def test_all_workday_merges_and_dedupes():
    merged = registry.all_workday()
    assert len(merged) >= len(registry.WORKDAY)
    tenants = [t for t, _, _, _ in merged]
    assert len(tenants) == len(set(tenants)), "duplicate tenant after merge"
    for row in merged:
        assert len(row) == 4 and all(isinstance(x, str) and x for x in row)


def test_new_connectors_are_callable():
    from ingest.connectors import workable, bamboohr
    assert callable(workable.fetch_board)
    assert callable(bamboohr.fetch_company)


def test_unit_domain_new_labels():
    assert registry.unit_domain("workable", registry.WORKABLE[0][0]) == "tech"
    assert registry.unit_domain("workable", "some-harvested-slug") == "general"
    assert registry.unit_domain("bamboohr", registry.BAMBOOHR[0][0]) == "tech"
    assert registry.unit_domain("bamboohr", "some-harvested-slug") == "general"


# ── Phenom / Eightfold (added 2026-07-15, enterprise ATS expansion) ────────────

def test_phenom_registry_shape():
    assert registry.PHENOM, "PHENOM registry is empty"
    for row in registry.PHENOM:
        assert len(row) == 3, f"PHENOM entry must be (host, locale_path, display): {row}"
        host, locale, _ = row
        assert "." in host and not host.startswith("http"), f"host must be bare domain: {host}"
        assert locale.startswith("/") and not locale.endswith("/"), f"locale must be /xx/yy: {locale}"


def test_eightfold_registry_shape():
    for row in registry.EIGHTFOLD:
        assert len(row) == 3, f"EIGHTFOLD entry must be (tenant, domain, display): {row}"
        assert all(isinstance(x, str) and x for x in row)


def test_enterprise_connectors_are_callable():
    from ingest.connectors import phenom, eightfold
    assert callable(phenom.fetch_site)
    assert callable(eightfold.fetch_company)


def test_unit_domain_enterprise_labels():
    assert registry.unit_domain("phenom", "careers.mastercard.com") == "finance"
    assert registry.unit_domain("phenom", "careers.services.global.ntt") == "tech"
    assert registry.unit_domain("eightfold", "paypal") == "tech"


def test_kula_registry_shape():
    assert registry.KULA, "KULA registry is empty"
    for row in registry.KULA:
        assert len(row) == 2, f"KULA entry must be (slug, display): {row}"
        assert all(isinstance(x, str) and x for x in row)


def test_kula_connector_callable():
    from ingest.connectors import kula
    assert callable(kula.fetch_company)


# ── Company normalization (added 2026-07-16) ───────────────────────────────────

def test_canonical_company():
    from ingest.normalize import canonical_company as cc
    assert cc("Cashfree Payments India Private Limited") == "Cashfree Payments"
    assert cc("Acme Technologies Pvt. Ltd.") == "Acme Technologies"
    assert cc("Foo, Inc.") == "Foo"
    assert cc("BoschGroup") == "Bosch Group"
    assert cc("Nagarro1") == "Nagarro"
    # brands must NOT be clipped mid-word or over-stripped
    assert cc("Cisco") == "Cisco"
    assert cc("Air India") == "Air India"
    assert cc("Unacademy") == "Unacademy"
    assert cc("") == ""


def test_sfcsb_registry_shape():
    assert registry.SFCSB, "SFCSB registry is empty"
    for row in registry.SFCSB:
        assert len(row) == 2, f"SFCSB entry must be (host, display): {row}"
        host, _ = row
        assert "." in host and not host.startswith("http")


def test_sfcsb_connector_callable():
    from ingest.connectors import sf_csb
    assert callable(sf_csb.fetch_site)
