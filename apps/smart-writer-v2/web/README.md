# Smart Writer V2 — Next.js UI (v0 design)

**D5 re-lock (2026-09-21):** Production = **same Railway service** as FastAPI (`smart-writer-v2`), UI served **same-origin**. Spend gate = **V1-style** shared preview secret (user types it; browser sends `X-Audit-Secret`).

**Superseded:** Railway service `smart-writer-v2-ui`, BFF-held silent secret, “browser never sees audit secret.”

Implement packet: `notes/packets/2026-09-21-swv2-d5-one-service-ui.md` (T069).

## Design

Vercel v0 export integrated here (shell + Settings + chips + draft pane). Keep that look; change transport/custody only.

## Target API calls (after T069)

| From | To |
|------|-----|
| Browser | Same-origin `/v1/...` with header `X-Audit-Secret` |
| Secret UX | Password field + `sessionStorage` (mirror V1) |

Remove or stop using `app/api/proxy/[...path]/route.ts` once same-origin wiring lands.

## Settings (D4 / T065)

Header **Settings** holds chat preferences. First preference: **citation format**
(`panel` | `inline` | `footnotes` | `combo`). Default is **sources panel**.

## Local (dev)

```bash
# Terminal A — API
cd apps/smart-writer-v2 && uv run uvicorn app.entrypoints.http:app --reload --port 8080

# Terminal B — UI (until FastAPI serves the build)
cd apps/smart-writer-v2/web && npm run dev
```

Needs Node (`nix develop` if missing).
