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
