# Quickstart validation — smart-writer-v2

Runnable checks after P0/P1 exist. Commands assume repo root and Nix/`uv` lab norms.

## Prerequisites

- Spec **Approved**; this **plan** human-approved before implement.
- App scaffolded: `apps/smart-writer-v2` registered; `uv sync --locked`.
- Env: `OPENAI_API_KEY`, `SMART_WRITER_V2_AUDIT_SECRET`; optional `TAVILY_API_KEY`.

## P0 — scaffold

```bash
cd apps/smart-writer-v2 && uv sync --locked
uv run uvicorn app.entrypoints.http:app --host 0.0.0.0 --port 8080
curl -s localhost:8080/health
```

Expect: `200`. Registry contains `smart-writer-v2`.

## P1 — MVP grant vertical (hybrid)

1. Create conversation (with audit secret header).
2. POST message with org + funder links (materials) and a grant ask prompt rich enough to skip clarify **or** answer clarifies first.
3. Poll job until succeeded — artifact `producing_mode=generate`, complete body, sources panel data present or explicit empty + SC-004 declaration if web on.
4. POST feedback message (`client_intent=auto`) → job `mode=revise`, `parent_artifact_id` set.
5. POST with `client_intent=regenerate` → `mode=generate`, new chain head.

**Auto candidates (CI later):**

```bash
cd apps/smart-writer-v2 && uv run pytest tests/contract -q
```

Expect tests covering revise/generate distinguishability + preview gate (see `contracts/http-api.md`).

## Catalog pointer

Human/hybrid checks: [`acceptance.md`](./acceptance.md) (SC-001–007).

## Out of scope for this guide

Full implement code, migrations, and complete eval suites — those belong in tasks/implement.
