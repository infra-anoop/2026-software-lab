# Data model — smart-writer-v2

Logical model for MVP (in-memory OK). Field names are contract-facing; storage may be dict/Pydantic.

## Conversation

| Field | Type | Notes |
|-------|------|-------|
| conversation_id | string (uuid) | Stable for a chat session |
| created_at | datetime | |
| updated_at | datetime | |

## Message

| Field | Type | Notes |
|-------|------|-------|
| message_id | string | |
| conversation_id | string | |
| role | `user` \| `assistant` \| `system` | |
| text | string | Free-form user text or assistant prose/question |
| created_at | datetime | |

## ArtifactVersion

| Field | Type | Notes |
|-------|------|-------|
| artifact_id | string | This version’s id |
| conversation_id | string | |
| parent_artifact_id | string \| null | Set on **revise**; null on fresh **generate** |
| producing_mode | `generate` \| `revise` | **Required for SC-006/007** |
| body | string | Complete user-visible draft |
| citation_mode | `panel` \| `inline` \| `footnotes` \| `combo` | Default `panel` when sources exist (F7) |
| source_ids | list[string] | All sources referenced |
| claims | list[ClaimProvenance] | **P4** — claim-level provenance |
| materials_bundle_ids | list[string] | F4 materials side |
| web_bundle_ids | list[string] | F4 web side |
| web_signal | `used` \| `none_declared` \| `disabled` | SC-004 |
| created_at | datetime | |

## ClaimProvenance *(P4)*

| Field | Type | Notes |
|-------|------|-------|
| claim_id | string | |
| excerpt | string | Quote or span from `body` (org/funder-specific assertion) |
| source_id | string \| null | Set when grounded |
| status | `grounded` \| `uncertain` | `uncertain` ⇒ omit or mark in prose; null source_id |

## InternalRunState

Invisible; updated from free-form inference (FR-017). Never required as user-facing form.

| Field | Type | Notes |
|-------|------|-------|
| conversation_id | string | |
| intent_slots | object | Who, Whom, Ask, WhyFunder, Evidence — strings \| null |
| property_ranking | list[string] | Ordered closed vocabulary ids |
| humor_enabled | bool | Grant default false/off (F3) |
| web_research_enabled | bool | Default true for beachhead unless user disables |
| materials | list[MaterialRef] | User URLs/uploads |
| citation_mode_pref | enum \| null | Light override |
| last_artifact_id | string \| null | Head of revise chain |

### Intent slots (grant)

| Slot | Meaning |
|------|---------|
| who | Org / applicant |
| whom | Funder / recipient |
| ask | What is requested |
| why_funder | Fit hook |
| evidence | Org fact / pointer |

## SourceRecord

| Field | Type | Notes |
|-------|------|-------|
| source_id | string | |
| kind | `user_material` \| `web` | F4 roles |
| bundle | `materials` \| `web` | Which retrieval façade produced it |
| uri | string \| null | |
| title | string \| null | |
| excerpt | string \| null | |
| retrieved_at | datetime \| null | |

## MaterialRef

| Field | Type | Notes |
|-------|------|-------|
| material_id | string | Stable id within conversation |
| uri | string \| null | For `kind=link`; null for upload-only |
| label | string \| null | |
| kind | `link` \| `upload` | |
| mime | string \| null | Required for upload |
| byte_len | int \| null | Upload size; enforce caps at HTTP |
| content_ref | string \| null | Key into process-local upload store (**D7** in-memory); not a durable URL |

## UploadStore (process-local — D7)

| Field | Type | Notes |
|-------|------|-------|
| content_ref | string | Opaque id |
| conversation_id | string | |
| bytes | bytes | In-memory; lost on restart |
| mime | string | |
| created_at | datetime | |

## Rubric (per write job — D8)

Built from **both** F6 axes before the writer↔assessor loop. Not user-visible taxonomy.

| Field | Type | Notes |
|-------|------|-------|
| rubric_id | string | Per job |
| job_id | string | |
| axis_a_dimensions | list[object] | From grant intent substance (Who/Whom/Ask/Why/Evidence as criteria text) |
| axis_b_dimensions | list[object] | From property ranking / steering |
| weights | object \| null | Optional; redesign vs V1 allowed |

## AssessorScore (per inner turn — D8)

| Field | Type | Notes |
|-------|------|-------|
| iteration | int | 1…8 |
| dimension_scores | list[object] | id → score |
| aggregate_score | float \| null | |
| feedback | string | Feeds next writer turn |

## Job / Run

| Field | Type | Notes |
|-------|------|-------|
| job_id | string | JobRunner id |
| conversation_id | string | |
| mode | `generate` \| `revise` | **Distinguishable** (SC-006/007 auto candidate) |
| status | queued \| running \| succeeded \| failed \| timed_out | |
| input_message_id | string | User turn that triggered job |
| parent_artifact_id | string \| null | Required when mode=revise |
| result_artifact_id | string \| null | On success |
| error | string \| null | |
| elapsed_ms | int \| null | Wall time for the write job (**D3**); set on terminal status |
| usage | object \| null | Best-effort: `input_tokens`, `output_tokens`, optional `estimated_cost_usd` (**D3**) |
| loop | object \| null | Inner critique: `iterations`, `aggregate_score`, `stop_reason` (`max_iterations` \| `targets_met` \| `error`) (**D8**) |
| rubric_id | string \| null | Dual-axis rubric for this job (**D8**) |

## State transitions

```text
user message
  → infer/update InternalRunState
  → if grant && missing intent slots → assistant clarify (no ArtifactVersion)
  → else enqueue Job(mode=generate|revise)
       generate: parent_artifact_id = null
       revise:   parent_artifact_id = last_artifact_id (required)
       inner (D8): build Rubric(A+B) → write ↔ assess (≤8) → provenance
  → on success: new ArtifactVersion + assistant message with body; job.elapsed_ms / usage / loop filled (D3/D8)
  → explicit regenerate (UI control / client_intent=regenerate): mode=generate (new chain head) (D9)
```

## Validation rules

- `mode=revise` ⇒ `parent_artifact_id` is non-null and exists in conversation.
- `mode=generate` ⇒ `parent_artifact_id` is null on the new artifact.
- Writing assistant turns that are not clarify MUST include a complete `body` (FR-018).
- Do not expose intent slot / axis names in assistant clarify copy (FR-021 / **P5**).
- Grant + missing intent slots ⇒ clarify only; never enqueue generate/revise (**P5**).
