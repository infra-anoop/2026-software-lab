"""ArtifactVersion / claim T1–T3 assemble helpers (no LLM)."""

from __future__ import annotations

from app.agents.provenance import coerce_claims
from app.models import ClaimProvenance, SourceRecord
from app.orchestrator.generate_graph import assemble_artifact, decide_web_signal


def test_assemble_generate_null_parent_and_panel() -> None:
    src = SourceRecord(
        source_id="mat_1",
        kind="user_material",
        bundle="materials",
        uri="https://example.org/criteria",
        excerpt="adult literacy",
    )
    body = "Literacy Partners asks the Ford Foundation for adult literacy funding."
    claims = coerce_claims(
        body,
        [
            ClaimProvenance(
                excerpt="Ford Foundation",
                source_id="mat_1",
                status="grounded",
            )
        ],
        [src],
    )
    artifact = assemble_artifact(
        conversation_id="c1",
        body=body,
        materials=[src],
        web=[],
        claims=claims,
        web_signal="none_declared",
        citation_mode_pref=None,
    )
    assert artifact.parent_artifact_id is None
    assert artifact.producing_mode == "generate"
    assert artifact.citation_mode == "panel"
    assert artifact.web_signal == "none_declared"
    assert artifact.claims[0].status == "grounded"
    assert artifact.claims[0].source_id == "mat_1"
    assert artifact.claims[0].excerpt in artifact.body


def test_grounded_orphan_source_becomes_uncertain() -> None:
    body = "We served 400 adults."
    claims = coerce_claims(
        body,
        [ClaimProvenance(excerpt="400 adults", source_id="missing", status="grounded")],
        [],
    )
    assert claims[0].status == "uncertain"
    assert claims[0].source_id is None
    assert claims[0].excerpt in body


def test_web_signal_not_hardcoded_none() -> None:
    assert decide_web_signal(web_research_enabled=False, web_sources=[]) == "disabled"
    hit = SourceRecord(source_id="w1", kind="web", bundle="web")
    assert decide_web_signal(web_research_enabled=True, web_sources=[hit]) == "used"
    assert decide_web_signal(web_research_enabled=True, web_sources=[]) == "none_declared"
