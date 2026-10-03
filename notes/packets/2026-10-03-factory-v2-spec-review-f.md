# Review packet — 001 Factory v2 spec, product review (F*)

## Meta

| Field | Value |
|-------|-------|
| Packet id | `2026-10-03-factory-v2-spec-review-f` |
| Gate | F* |
| Brief | `docs/agent-os/SPEC_REVIEW_PROMPT.md` |
| Feature dir | `specs/001-factory-v2/` |
| Agent mode | spawned-reviewer (model family: GPT — spec D3) |

## Context to read first

- `docs/agent-os/SPAWN_REVIEWER.md`
- `docs/agent-os/SPEC_REVIEW_PROMPT.md` (job text below the horizontal rule; `SPEC_PATH` = `specs/001-factory-v2/spec.md`)
- `specs/001-factory-v2/intent.yaml` — governor intent (source of truth for intent; spec cites ids)
- `notes/sprints/2026-10-sprint-02.md` — sprint charter
- `AGENTS.md`, `.specify/memory/constitution.md` (v1.9.0; this feature moves it to 2.0)

## Product framing for this review

For this feature **the software factory is the product** and the **governor (human lab owner) is its user**. Judge value to the governor: does this spec make long unattended agent runs stay on intent, keep the governor at decision altitude, and avoid becoming paperwork or ceremony? Smart Writer V2 is only the workload.

Attack especially: the P1/P2/P3 check scheduling (right cut for a 3-day Wave 1?), whether seeded-violation fixtures are a real falsifier for "machines catch drift", whether the religion-mining loop (US7) is real or aspirational, and any intent in `intent.yaml` the spec silently thinned (constitution §I).

## Artifacts under review

- `specs/001-factory-v2/spec.md`
- `specs/001-factory-v2/acceptance.md`
- `specs/001-factory-v2/intent.yaml`

## Owned paths (may edit)

- `specs/001-factory-v2/SPEC_REVIEW.md` (create)

## Forbidden paths (do not edit)

- `spec.md`, `intent.yaml`, `acceptance.md`, any code, `deploy/secrets/`

## Definition of Done

- [ ] `specs/001-factory-v2/SPEC_REVIEW.md` deposited in the brief's strict format (A–F)
- [ ] ≥6 findings, ≥2 Debates, ≥1 strength; IDs prefixed F
- [ ] Each Debate tagged product or process
- [ ] Stop — do not edit the spec

## Governor locks already closed (do not re-open)

| Lock | Value |
|------|-------|
| Framing | Factory is the product; SNR = intent fidelity over autonomy time |
| D1 | P3 checks out of this version (sprint 03) |
| D2 | Mutation threshold 70% on changed lines |
| D3 | GPT family reviews by default |
| Intent conflicts | Resolved in `intent.yaml` `conflicts:` |

## Stop / escalate if

- Spec or intent file missing
- Brief and packet disagree on deposit path
