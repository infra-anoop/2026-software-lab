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
| POST | `/v1/conversations/{id}/uploads` | Multipart file upload → `MaterialRef` `kind=upload` (D7; see below) |
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
- `materials` on this route remain **link** pointers (`uri` required). File bytes use the dedicated upload route below (**D7**).

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

### POST `/v1/conversations/{id}/uploads` (D7)

Multipart form (`multipart/form-data`), not JSON:

| Field | Required | Notes |
|-------|----------|-------|
| `file` | yes | Upload bytes |
| `label` | no | Display label |

**Storage:** process-local in-memory `UploadStore` (`data-model.md`). Restart loses bytes (same residual as conversations). No object store.

**Defaults (sensible limits — D7):**

| Limit | Default |
|-------|---------|
| Max `byte_len` | **5 MiB** (`5 * 1024 * 1024`) |
| Allowed MIME (PDF / text-class) | `application/pdf`, `text/plain`, `text/markdown`, `text/csv`, `application/json` |

MIME is taken from the multipart `Content-Type` of `file` (fallback: sniff from filename extension only when Content-Type is missing/`application/octet-stream`). Reject otherwise.

Success `200`:

```json
{
  "material_id": "...",
  "kind": "upload",
  "mime": "text/plain",
  "byte_len": 123,
  "content_ref": "...",
  "label": null,
  "uri": null
}
```

The material is appended to the conversation’s `InternalRunState.materials` and is available to later generate turns. `content_ref` is an opaque key into the process-local store — not a durable URL.

| Code | When |
|------|------|
| 401 / 503 | Same preview-gate rules as other protected routes |
| 404 | Unknown conversation |
| 422 | Missing `file`; oversize; disallowed MIME |

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
  "rubric_id": "...",
  "loop": {
    "iterations": 2,
    "max_iterations": 8,
    "aggregate_score": 18.0,
    "stop_reason": "max_iterations | targets_met | error",
    "axis_a_dimension_count": 3,
    "axis_b_dimension_count": 2,
    "scores": [
      {
        "iteration": 1,
        "dimension_scores": [
          { "id": "axis_a.whom_fit", "score": 3 },
          { "id": "axis_b.warm", "score": 4 }
        ],
        "aggregate_score": 14.0,
        "feedback": "Strengthen funder fit before next draft."
      }
    ]
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

`elapsed_ms` and `usage` are **required keys** on terminal job snapshots for V2 finish observability (**D3**); values may be `null` only when measurement failed — prefer best-effort numbers.

**Dual-axis scored inner loop (**D8** / FR-022):** On every **succeeded** generate or revise job, `rubric_id` and `loop` are **required** (non-null). Capability must **not** be thinner than V1’s scored writer↔assessor loop: one-shot write without scores, stub/`null` `aggregate_score`, empty `scores[]`, or omitting `stop_reason` are contract failures.

| `loop` field | Rules |
|--------------|--------|
| `iterations` | int in `1…max_iterations` (inner writer↔assess cycles completed) |
| `max_iterations` | int; equals Settings inner max (locked default **8**, **D2**) |
| `aggregate_score` | number (not JSON `null`) — final aggregate after last assess |
| `stop_reason` | exactly one of `max_iterations` \| `targets_met` \| `error` |
| `axis_a_dimension_count` | int ≥ 1 — rubric dimensions from grant intent substance |
| `axis_b_dimension_count` | int ≥ 1 — rubric dimensions from property ranking / steering |
| `scores` | nonempty list of per-turn AssessorScore objects (`iteration`, `dimension_scores`, `aggregate_score`, `feedback`); `len(scores) == iterations`; each `iteration` in `1…8` |

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
7. Succeeded generate/revise job → `rubric_id` non-null; `loop` present with `iterations` in `1…loop.max_iterations`, `loop.max_iterations` ≤ **8** and equal to Settings inner max, nonempty `scores` (length = `iterations`) with per-turn `dimension_scores`, numeric `aggregate_score`, `stop_reason` ∈ {`max_iterations`,`targets_met`,`error`}, and `axis_a_dimension_count` ≥ 1 and `axis_b_dimension_count` ≥ 1 (**D8** / FR-022).
8. Upload happy path → `200` with `kind=upload`, `uri` JSON `null`, nonempty `material_id` / `content_ref`, `mime` in the allowed set, `byte_len` matching payload size. Oversize or disallowed MIME → `422` (**D7**).
