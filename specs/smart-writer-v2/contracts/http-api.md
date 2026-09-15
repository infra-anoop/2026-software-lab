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

**Clarify (sync):**

```json
{
  "type": "clarify",
  "assistant_message": { "message_id": "...", "text": "..." },
  "missing_hints": ["whom", "ask"]
}
```

(`missing_hints` optional/internal — UI should prefer natural-language question text only.)

**Job accepted:**

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
  "artifact": {
    "artifact_id": "...",
    "parent_artifact_id": null,
    "producing_mode": "generate | revise",
    "body": "...",
    "citation_mode": "panel",
    "sources": []
  }
}
```

## Errors

| Code | When |
|------|------|
| 401 | Bad/missing audit secret |
| 404 | Unknown conversation/job/artifact |
| 409 | `revise` requested but no parent artifact |
| 422 | Validation |
| 429 | Rate limit |
| 503 | Secret unset / queue overloaded |

## Auto-check hooks (R4)

Contract tests should assert:

1. Successful revise job → `mode=revise` and `artifact.parent_artifact_id` non-null.
2. Successful generate/regenerate → `mode=generate` and `parent_artifact_id` null.
3. Protected routes reject wrong secret.
