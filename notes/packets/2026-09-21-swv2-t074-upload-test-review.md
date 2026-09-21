# Review packet — T074 upload contract tests (D7)

## Meta

| Field | Value |
|-------|-------|
| Packet id | `2026-09-21-swv2-t074-upload-test-review` |
| Status | ready |
| Gate | T* |
| Brief | `docs/agent-os/TEST_REVIEW_PROMPT.md` |
| Feature dir | `specs/smart-writer-v2/` |
| Commit | d42e4021a3e08ab8d47f764e915470d17bc654a2* |
| Agent mode | spawned-reviewer |

## Context to read first

- `docs/agent-os/SPAWN_REVIEWER.md`
- `docs/agent-os/TEST_REVIEW_PROMPT.md` (job text below the horizontal rule)
- `specs/smart-writer-v2/spec.md` — **D7** locked (uploads in finish; in-memory; sensible size/MIME)
- `specs/smart-writer-v2/plan.md` + `PLAN_DELTA.md` (uploads)
- `specs/smart-writer-v2/contracts/http-api.md` — `POST .../uploads` + **hook 8**
- `specs/smart-writer-v2/data-model.md` — `MaterialRef` `kind=upload`, `UploadStore`
- `specs/smart-writer-v2/acceptance.md` (upload rows if any; do not fake human/hybrid)
- Prior finding IDs in `TEST_REVIEW.md` — **continue at T54** (do not reuse T1–T53)

## Artifacts under review

- Paths:
  - `apps/smart-writer-v2/tests/contract/test_upload_materials.py` (**new**, red)
  - `specs/smart-writer-v2/contracts/http-api.md` (upload route + defaults — read for lock fidelity)
  - `apps/smart-writer-v2/web/README.md` (upload section — docs only)
- Pytest (at review commit; re-run under app `.venv` / `uv` to confirm):

| Test | Result | Fail locus (reported) |
|------|--------|------------------------|
| `test_upload_accepts_text_plain_happy_path` | FAIL | `405 Method Not Allowed` (assert 200) |
| `test_upload_rejects_oversize` | FAIL | `405` (assert 422) |
| `test_upload_rejects_disallowed_mime` | FAIL | `405` (assert 422) |

All three fail because `POST /v1/conversations/{id}/uploads` is not implemented yet (no matching product code). Negative tests currently fail on missing route rather than MIME/size validation — note in findings if that weakens red-first honesty until the route exists.

## Owned paths (may edit)

- `specs/smart-writer-v2/TEST_REVIEW.md` (**append** a new T074 / D7 uploads section; do not wipe prior locks)

## Forbidden paths (do not edit)

- Application / product implementation (`apps/smart-writer-v2/app/`, matching T075–T076)
- Spec / plan body (review only)
- `deploy/secrets/`
- Greening or rewriting the red tests (except naming gaps in the review findings)

## Definition of Done

- [ ] Review deposited at `specs/smart-writer-v2/TEST_REVIEW.md` (append)
- [ ] Findings use **T54+**; ≥1 Debate and ≥1 strength; min 4 findings
- [ ] Tag Debates **product** vs **process** per brief
- [ ] Stop — do not implement; human adjudicates product Debates / Blockers

## Out of scope

- Matching product implementation (T075–T076)
- Object store / S3
- Asking the human to paste this packet or the brief

## Governor locks required

| Lock | Value or `await Debate` |
|------|-------------------------|
| D7 | **locked** — uploads in finish; in-memory bytes; sensible size/MIME; no object store |
| D5 | V1-style secret; same-origin UI (header asserted in tests) |
| Prior T1–T53 | stay locked / accepted as already recorded |

## Fidelity (constitution §I)

| Lock | letter \| intent | Notes |
|------|------------------|-------|
| D7 | letter | Attack thinner stand-ins (docs-only “upload”, link-only theater, durable blob swap) |

## Stop / escalate if

- Artifacts under review missing at the named commit
- Tempted to implement the upload route to “help” the review — stop
