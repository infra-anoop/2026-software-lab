"""D7 / T074: upload accept/reject on POST .../uploads (contract hook 8).

Red before T075. Public HTTP only — no store/graph stubs.

T54(A): this suite is shape + 422 reject only; UploadStore + materials append
are owned by T075 (not asserted here).
T57: missing file 422; unknown conversation 404; wrong/missing secret 401.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from tests.contract.grant_flow import AUTH, SECRET

# Contract defaults (http-api.md / D7).
MAX_UPLOAD_BYTES = 5 * 1024 * 1024


def _create_conversation(client: TestClient) -> str:
    response = client.post("/v1/conversations", headers=AUTH)
    assert response.status_code == 200, response.text
    body = response.json()
    assert "conversation_id" in body
    return str(body["conversation_id"])


def test_upload_accepts_text_plain_happy_path(client: TestClient) -> None:
    """Small text/plain → 200 MaterialRef kind=upload shape (hook 8)."""
    conversation_id = _create_conversation(client)
    payload = b"funder criteria: community arts grants\n"
    response = client.post(
        f"/v1/conversations/{conversation_id}/uploads",
        headers={"X-Audit-Secret": SECRET},
        files={"file": ("criteria.txt", payload, "text/plain")},
        data={"label": "criteria"},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body.get("kind") == "upload"
    assert "uri" in body and body["uri"] is None
    assert body.get("mime") == "text/plain"
    assert body.get("byte_len") == len(payload)
    assert isinstance(body.get("material_id"), str) and body["material_id"]
    assert isinstance(body.get("content_ref"), str) and body["content_ref"]
    assert body.get("label") == "criteria"


def test_upload_rejects_oversize(client: TestClient) -> None:
    """Payload larger than 5 MiB → 422.

    Pre-route red may fail as 405 (missing method); after T075, locus must be validation 422.
    """
    conversation_id = _create_conversation(client)
    oversized = b"x" * (MAX_UPLOAD_BYTES + 1)
    response = client.post(
        f"/v1/conversations/{conversation_id}/uploads",
        headers={"X-Audit-Secret": SECRET},
        files={"file": ("big.txt", oversized, "text/plain")},
    )
    assert response.status_code == 422, response.text


def test_upload_rejects_disallowed_mime(client: TestClient) -> None:
    """image/png (not PDF/text-class) → 422.

    Pre-route red may fail as 405 (missing method); after T075, locus must be validation 422.
    """
    conversation_id = _create_conversation(client)
    response = client.post(
        f"/v1/conversations/{conversation_id}/uploads",
        headers={"X-Audit-Secret": SECRET},
        files={"file": ("photo.png", b"\x89PNG\r\n", "image/png")},
    )
    assert response.status_code == 422, response.text


def test_upload_rejects_missing_file(client: TestClient) -> None:
    """No multipart file field → 422 (T57)."""
    conversation_id = _create_conversation(client)
    response = client.post(
        f"/v1/conversations/{conversation_id}/uploads",
        headers={"X-Audit-Secret": SECRET},
        data={"label": "no-file"},
    )
    assert response.status_code == 422, response.text


def test_upload_unknown_conversation_404(client: TestClient) -> None:
    """Unknown conversation id → 404 (T57)."""
    response = client.post(
        "/v1/conversations/does-not-exist/uploads",
        headers={"X-Audit-Secret": SECRET},
        files={"file": ("criteria.txt", b"x", "text/plain")},
    )
    assert response.status_code == 404, response.text


def test_upload_rejects_missing_or_wrong_secret(client: TestClient) -> None:
    """Missing or wrong X-Audit-Secret → 401 on /uploads (T57)."""
    conversation_id = _create_conversation(client)
    missing = client.post(
        f"/v1/conversations/{conversation_id}/uploads",
        files={"file": ("criteria.txt", b"x", "text/plain")},
    )
    assert missing.status_code == 401, missing.text
    wrong = client.post(
        f"/v1/conversations/{conversation_id}/uploads",
        headers={"X-Audit-Secret": "not-the-secret"},
        files={"file": ("criteria.txt", b"x", "text/plain")},
    )
    assert wrong.status_code == 401, wrong.text
