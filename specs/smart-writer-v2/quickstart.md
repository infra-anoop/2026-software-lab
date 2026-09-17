# Quickstart validation — smart-writer-v2

Runnable checks after P0/P1 exist. Commands assume repo root and Nix/`uv` lab norms.

App README (local + restart semantics): [`apps/smart-writer-v2/README.md`](../../apps/smart-writer-v2/README.md).

## Prerequisites

- Spec **Approved**; this **plan** human-approved before implement.
- App scaffolded: `apps/smart-writer-v2` registered; `uv sync --locked`.
- Env: `OPENAI_API_KEY`, `SMART_WRITER_V2_AUDIT_SECRET`; optional `TAVILY_API_KEY`. Copy `apps/smart-writer-v2/.env.example` → `.env` (gitignored).

## In-memory / restart

MVP storage is **process-local** (conversations, run state, jobs). Restarting uvicorn or the Railway replica **loses** jobs and chat history. Replicas do not share memory — production replica count stays **1** (`notes/architect-backlog.md` A9). Durability is plan P3.

## P0 — scaffold

```bash
cd apps/smart-writer-v2 && uv sync --locked
uv run uvicorn app.entrypoints.http:app --host 0.0.0.0 --port 8080
curl -s localhost:8080/health
```

Expect: `200`. Registry contains `smart-writer-v2`. `/ready` is 200 only when `OPENAI_API_KEY` is set (presence check; no upstream call).

### Local UI (optional)

Same audit secret on the Next **server** env (never `NEXT_PUBLIC_*`). Default worker URL `http://127.0.0.1:8080`.

```bash
cd apps/smart-writer-v2/web
SMART_WRITER_V2_AUDIT_SECRET=… SMART_WRITER_V2_WORKER_URL=http://127.0.0.1:8080 npm run dev
```

Open the Next origin. Node is required (`nix develop` if missing).

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

## Railway (worker `/health`)

Lab cattle — not Spec Kit. One-app bootstrap (no lab-wide `v*` tag): [`notes/packets/2026-09-17-swv2-railway-bootstrap.md`](../../notes/packets/2026-09-17-swv2-railway-bootstrap.md). Config: `deploy/railway/production/smart-writer-v2.yml`. Smoke is `GET /health`.

## Out of scope for this guide

Full implement code, migrations, complete eval suites, and Vercel UI cattle (T067).
