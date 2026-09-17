"""PydanticAI provenance node + fail-closed coercion (T1)."""

from __future__ import annotations

import json
from functools import lru_cache
from uuid import uuid4

from pydantic_ai import Agent

from app.models import ClaimProvenance, ProvenanceOutput, SourceRecord
from app.prompts.loader import load_role_prompt

PROGRAM = "grant_default"


@lru_cache(maxsize=4)
def _provenance_agent() -> Agent[None, ProvenanceOutput]:
    return Agent(
        "openai:gpt-4o",
        output_type=ProvenanceOutput,
        system_prompt=load_role_prompt(PROGRAM, "provenance"),
    )


def coerce_claims(
    body: str,
    claims: list[ClaimProvenance],
    sources: list[SourceRecord],
) -> list[ClaimProvenance]:
    """Keep only excerpts in body; grounded source_id must exist; else uncertain/drop."""
    source_ids = {s.source_id for s in sources}
    out: list[ClaimProvenance] = []
    for claim in claims:
        excerpt = (claim.excerpt or "").strip()
        if not excerpt or excerpt not in body:
            continue
        if claim.status == "grounded" and claim.source_id in source_ids:
            out.append(
                ClaimProvenance(
                    claim_id=claim.claim_id or f"cl_{uuid4().hex[:8]}",
                    excerpt=excerpt,
                    source_id=claim.source_id,
                    status="grounded",
                )
            )
            continue
        out.append(
            ClaimProvenance(
                claim_id=claim.claim_id or f"cl_{uuid4().hex[:8]}",
                excerpt=excerpt,
                source_id=None,
                status="uncertain",
            )
        )
    if not out and body.strip():
        span = body.strip()[:80]
        if span and span in body:
            out.append(
                ClaimProvenance(
                    claim_id=f"cl_{uuid4().hex[:8]}",
                    excerpt=span,
                    source_id=None,
                    status="uncertain",
                )
            )
    return out


async def attach_provenance(
    *,
    body: str,
    user_text: str,
    sources: list[SourceRecord],
) -> list[ClaimProvenance]:
    """Ask the model, then coerce to T1 locks."""
    payload = {
        "body": body,
        "user_prompt": user_text,
        "sources": [s.model_dump() for s in sources],
    }
    result = await _provenance_agent().run(json.dumps(payload, indent=2))
    return coerce_claims(body, result.output.claims, sources)
