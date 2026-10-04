# Contract — HTTP API delta (002)

Baseline: [`../../smart-writer-v2/contracts/http-api.md`](../../smart-writer-v2/contracts/http-api.md). Preview audit secret rules unchanged.

## Ownership cookie

- Any `/v1/*` request without a valid `swv2_owner` cookie gets one issued (`Set-Cookie: swv2_owner=<random 256-bit, base64url>; HttpOnly; Secure; SameSite=Lax; Path=/; Max-Age=31536000`). `Secure` is off only when Settings `SMART_WRITER_V2_COOKIE_INSECURE_DEV=true`.
- Conversation routes resolve `owner_id` from the cookie. Another owner's conversation → **404** (not 403; existence is not disclosed).

## New / changed routes

| Route | Change |
|-------|--------|
| `GET /v1/conversations` | **New.** Owner's conversations: `[{conversation_id, title?, updated_at, last_used_at, expires_at}]`, newest first. Does not touch retention. |
| `GET /v1/conversations/{id}` | Adds `last_used_at`, `expires_at`. Touches retention. |
| `POST /v1/conversations/{id}/messages`, uploads, job enqueue | Touch retention (unchanged shapes). |
| `GET /v1/jobs/{id}` | `status` may be `failed` with `fail_reason: "interrupted_retry"` after restart; adds `cost_usd`. Job snapshot `loop` shape unchanged (baseline D8). Resolves the owner through the job's conversation; another owner's job → **404** (same rule as conversations, FR-003). |

`fail_reason` values: `interrupted_retry` | `spend_ceiling` | `spend_unpriced` | `conversation_deleted` (data-model § Use, § Job execution; plan § Spend ceiling).

## Spend stop

A job that would exceed the per-draft ceiling ends `failed` with `fail_reason: "spend_ceiling"` and `error` naming the ceiling; no partial artifact is saved as a new version.
