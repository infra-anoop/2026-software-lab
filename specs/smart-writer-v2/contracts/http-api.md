# HTTP API contract — smart-writer-v2

Base: FastAPI app. JSON request/response unless noted.

## Public

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| GET | `/health` | none | Liveness |
| GET | `/ready` | none | Config present (e.g. OpenAI key); no upstream call |

## Protected (preview gate)

Header: `X-Audit-Secret: <SMART_WRITER_V2_AUDIT_SECRET>`  
Missing/wrong secret → `401`. Secret unset in env → `503` on protected routes (fail closed for mutating/job).

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/v1/conversations` | Create conversation → `{ conversation_id }` |
| POST | `/v1/conversations/{id}/messages` | User turn (see below) |
| GET | `/v1/conversations/{id}` | Snapshot: messages, latest artifact, internal state **redacted** (no raw secrets; slot values OK for debugging only if flag — default omit slots from client or return “filled/missing” booleans) |
| GET | `/v1/jobs/{job_id}` | Job snapshot (status/result) |
| GET | `/v1/artifacts/{artifact_id}` | ArtifactVersion + sources |

### POST `/v1/conversations/{id}/messages`

Request:

```json
{
  "text": "string (free-form)",
  "client_intent": "auto | regenerate",
  "citation_mode": null,
  "materials": [{ "uri": "https://...", "label": null }]
}
```

- `client_intent: auto` — server chooses clarify vs generate vs revise (revise if `last_artifact_id` and not regenerate).
- `client_intent: regenerate` — force **generate** path (FR-020).

Response (one of):

**Clarify (sync) — grant slots incomplete (P5):**

```json
{
  "type": "clarify",
  "assistant_message": { "message_id": "...", "text": "..." }
}
```

Natural-language questions only. Do **not** include `missing_hints` / slot ids in the default client payload (FR-021). `job_id` MUST be absent or JSON `null`. English `ask`/`whom` in questions is allowed; do **not** use structured labels (`Axis`, `intent_slots`, `why_funder`, `missing_hints`, `Whom:`). After clarify, `GET /v1/conversations/{id}` has `last_artifact_id` JSON `null` (no ArtifactVersion) — **T9/T10**.

**Job accepted** — only when grant intent slots are complete (or non-grant path):

```json
{
  "type": "job_accepted",
  "job_id": "...",
  "mode": "generate | revise",
  "parent_artifact_id": null
}
```

### GET `/v1/jobs/{job_id}` (success shape)

```json
{
  "job_id": "...",
  "status": "succeeded",
  "mode": "generate | revise",
  "humor_enabled": false,
  "elapsed_ms": 12345,
  "usage": {
    "input_tokens": 0,
    "output_tokens": 0,
    "estimated_cost_usd": null
  },
  "loop": {
    "iterations": 1,
    "aggregate_score": null,
    "stop_reason": "max_iterations | targets_met | error"
  },
  "artifact": {
    "artifact_id": "...",
    "parent_artifact_id": null,
    "producing_mode": "generate | revise",
    "body": "...",
    "citation_mode": "panel",
    "sources": [
      { "source_id": "...", "kind": "user_material | web", "bundle": "materials | web" }
    ],
    "claims": [
      { "claim_id": "...", "excerpt": "...", "source_id": "...", "status": "grounded" }
    ],
    "web_signal": "used | none_declared | disabled"
  }
}
```

`humor_enabled` is a **job-snapshot** boolean (grant default `false` unless the user enabled humor). Do **not** dump `InternalRunState` / intent slots on `GET /v1/conversations` to satisfy this field.

`elapsed_ms` and `usage` are **required keys** on terminal job snapshots for V2 finish observability (**D3**); values may be `null` only when measurement failed — prefer best-effort numbers. `loop` is required once the dual-axis scored inner loop ships (**D8** / T078+).

When `artifact.sources` is nonempty and the turn did not override `citation_mode`, `citation_mode` MUST be `panel` (F7).

Grounded claims: `source_id` MUST equal some `artifact.sources[].source_id`; `excerpt` MUST be a substring of `artifact.body`. Uncertain claims: `source_id` is JSON `null`.

## Errors

| Code | When |
|------|------|
| 401 | Bad/missing audit secret |
| 404 | Unknown conversation/job/artifact |
| 409 | `revise` without parent artifact; **or** attempt to enqueue grant write while intent slots incomplete (should have been `clarify`) |
| 422 | Validation |
| 429 | Rate limit |
| 503 | Secret unset / queue overloaded |

## Auto-check hooks (R4 / P4)

Contract tests should assert:

1. Successful revise job → `mode=revise` and `artifact.parent_artifact_id` non-null.
2. Successful generate/regenerate → `mode=generate` and `parent_artifact_id` JSON `null` (key present). When `sources` nonempty and the turn did not override citation mode → `citation_mode=panel`.
3. Protected routes reject wrong secret.
4. Successful grant artifact with org/funder claims → each such claim in `claims[]` has `status=grounded`+`source_id` that exists on `artifact.sources[]`, or `status=uncertain` with null `source_id`; `excerpt` is a substring of `body` (SC-003 shape).
5. When web enabled and no useful web hits → `web_signal=none_declared` (SC-004 shape). Not `disabled` on that fixture.
6. Grant turn with empty Whom/Ask (fixture) → `type=clarify`; `job_id` absent or JSON `null`; `GET /v1/conversations/{id}` `last_artifact_id` JSON `null` (P5 / T10). Assistant text has no structured slot/axis labels (T9). A second fixture with Who+Whom+Ask filled and Why or Evidence empty must still clarify (T11).
