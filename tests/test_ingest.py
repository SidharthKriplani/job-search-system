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
