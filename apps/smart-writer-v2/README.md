# Smart Writer V2 (worker + Vercel BFF)

HTTP worker: `uv run uvicorn app.entrypoints.http:app --reload --host 0.0.0.0 --port 8080`

The Next.js BFF at `web/app/api/proxy/[...path]/route.ts` reads `SMART_WRITER_V2_AUDIT_SECRET` from **server** env only. Do not add `NEXT_PUBLIC_*` for that secret. Set `SMART_WRITER_V2_WORKER_URL` (default `http://127.0.0.1:8080`) on the BFF host.
