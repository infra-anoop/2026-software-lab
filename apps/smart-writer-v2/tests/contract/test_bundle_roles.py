"""F4 structural: materials vs web bundle ids follow SourceRecord.bundle (T053).

T29: already-green T021 landmine for list↔bundle set-equality. T056 DoD is not
“make this pass.” Bind kind + submitted URI so F4 is not two views of sources[].
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from tests.contract.grant_flow import GRANT_MATERIALS, submit_grant_and_wait


def test_bundle_ids_match_source_record_bundle(client: TestClient) -> None:
    """materials_bundle_ids / web_bundle_ids are the source_ids with that bundle."""
    _conversation_id, _accepted, job = submit_grant_and_wait(client)
    artifact = job["artifact"]
    sources = artifact["sources"]
    assert isinstance(sources, list)
    mat_ids = {row["source_id"] for row in sources if row.get("bundle") == "materials"}
    web_ids = {row["source_id"] for row in sources if row.get("bundle") == "web"}
    assert "materials_bundle_ids" in artifact
    assert "web_bundle_ids" in artifact
    assert set(artifact["materials_bundle_ids"]) == mat_ids
    assert set(artifact["web_bundle_ids"]) == web_ids
    assert len(artifact["materials_bundle_ids"]) >= 1
    expected_uri = GRANT_MATERIALS[0]["uri"]
    materials_rows = [row for row in sources if row.get("bundle") == "materials"]
    assert materials_rows
    assert all(row.get("kind") == "user_material" for row in materials_rows)
    assert any(row.get("uri") == expected_uri for row in materials_rows), materials_rows
