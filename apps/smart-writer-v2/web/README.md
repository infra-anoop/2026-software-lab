# Smart Writer V2 — Next.js UI (v0 design)

**D5 re-lock (2026-09-21):** Production = **same Railway service** as FastAPI (`smart-writer-v2`), UI served **same-origin**. Spend gate = **V1-style** shared preview secret (user types it; browser sends `X-Audit-Secret`).

**Superseded:** Railway service `smart-writer-v2-ui`, BFF-held silent secret, “browser never sees audit secret,” and `web/app/api/proxy`.

Packet: `notes/packets/2026-09-21-swv2-d5-one-service-ui.md` (T069).

## Design

Vercel v0 export integrated here (shell + Settings + chips + draft pane). Keep that look; transport is same-origin `/v1` only.

## API calls

| From | To |
|------|-----|
| Browser | Same-origin `/v1/...` with header `X-Audit-Secret` |
| Secret UX | Settings password field + `sessionStorage` (mirror V1) |

No Next Route Handlers for custody. `output: "export"` → static files under `../app/static/ui` for FastAPI.

## Settings (D4 / T065)

Header **Settings** holds chat preferences and the **preview gate secret**. Citation format:
(`panel` | `inline` | `footnotes` | `combo`). Default is **sources panel**.

## File uploads (D7 / T073–T076)

Chat may attach a file via `POST /v1/conversations/{id}/uploads` (multipart `file` + optional `label`) with the same `X-Audit-Secret` header as other `/v1` calls — **same-origin, no BFF**.

| Limit | Default |
|-------|---------|
| Max size | **5 MiB** |
| Allowed MIME | `application/pdf`, `text/plain`, `text/markdown`, `text/csv`, `application/json` |

Bytes live **in-memory on the worker** (`UploadStore`). A process restart drops uploads (same residual as conversations). No object store in this version.

## Build into FastAPI

```bash
# Needs Node 22+ (nix-shell -p nodejs_22 if not on PATH)
cd apps/smart-writer-v2/web
npm ci
npm run build:fastapi   # next build (static export) → ../app/static/ui
```

Then one process:

```bash
cd apps/smart-writer-v2
uv run uvicorn app.entrypoints.http:app --reload --port 8080
# http://127.0.0.1:8080/
```

## Dev hot-reload (optional)

```bash
cd apps/smart-writer-v2/web && npm run dev
```

Pointing `npm run dev` at a separate origin still requires a typed secret in Settings; do not restore the BFF proxy.
