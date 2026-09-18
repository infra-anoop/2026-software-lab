# Smart Writer V2 — Next.js UI + BFF

Vercel hosts this App Router app (plan P1 topology). The FastAPI job worker runs on Railway.
Browser talks **only** to same-origin Next routes; the BFF attaches the preview secret.

## Cattle-declared env names (server only)

Set these on the Vercel project (or local `.env.local`). **Never** prefix with `NEXT_PUBLIC_`.

| Name | Where used | Notes |
|------|------------|--------|
| `SMART_WRITER_V2_AUDIT_SECRET` | `app/api/proxy/[...path]/route.ts` | Same shared secret as the Railway worker preview gate. Server-only; unset → BFF returns 503. |
| `SMART_WRITER_V2_WORKER_URL` | same BFF route | Base URL of the FastAPI worker (no trailing slash). Local default in code: `http://127.0.0.1:8080`. Production example: Railway public URL for service `smart-writer-v2`. |

Worker secret **name** is also in `deploy/secrets/schema.yaml` (Infisical → Railway). Vercel upsert is a separate fat ops packet (A21 `target_vercel` still stubbed) — this README is the thin git pointer (T067).

## Local

```bash
# Terminal A — worker
cd apps/smart-writer-v2 && uv sync --locked
# set SMART_WRITER_V2_AUDIT_SECRET + OPENAI_API_KEY in app `.env`
uv run uvicorn app.entrypoints.http:app --reload --host 0.0.0.0 --port 8080

# Terminal B — UI
cd apps/smart-writer-v2/web
# .env.local: SMART_WRITER_V2_AUDIT_SECRET=<same> SMART_WRITER_V2_WORKER_URL=http://127.0.0.1:8080
npm install && npm run dev
```

## Out of scope here

- Provisioning a Vercel project or Infisical→Vercel sync (fat ops packet).
- Implementing `scripts/secrets_sync/target_vercel.py` (A21 adapter work).
