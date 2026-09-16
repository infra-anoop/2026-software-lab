"""Grant artifact claim provenance (hook 4; catalog claim.provenance structural)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from tests.contract.grant_flow import submit_grant_and_wait


def test_grant_claims_are_grounded_or_uncertain(client: TestClient) -> None:
    """Grounded source_id resolves in sources[]; excerpt is a substring of body."""
    _conversation_id, _accepted, job = submit_grant_and_wait(client)
    artifact = job["artifact"]
    body = artifact["body"]
    assert isinstance(body, str)
    sources = artifact["sources"]
    assert isinstance(sources, list)
    source_ids = {row["source_id"] for row in sources}
    claims = artifact["claims"]
    assert isinstance(claims, list)
    assert len(claims) >= 1, "this fixture includes materials beyond the prompt; claims[] must not be empty"
    for claim in claims:
        status = claim["status"]
        source_id = claim.get("source_id")
        excerpt = claim.get("excerpt")
        assert isinstance(excerpt, str) and excerpt.strip() != "", claim
        assert excerpt in body, claim
        assert status in {"grounded", "uncertain"}, claim
        if status == "grounded":
            assert isinstance(source_id, str) and source_id.strip() != "", claim
            assert source_id in source_ids, claim
        else:
            assert source_id is None, claim
