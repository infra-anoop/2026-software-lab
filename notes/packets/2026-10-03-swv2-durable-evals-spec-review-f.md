# Review packet — 002 Smart Writer V2 durable state + measured quality, product review (F*)

## Meta

| Field | Value |
|-------|-------|
| Packet id | `2026-10-03-swv2-durable-evals-spec-review-f` |
| Gate | F* |
| Brief | `docs/agent-os/SPEC_REVIEW_PROMPT.md` |
| Feature dir | `specs/002-swv2-durable-evals/` |
| Agent mode | spawned-reviewer (model family: GPT — factory spec D3) |

## Context to read first

- `docs/agent-os/SPAWN_REVIEWER.md`
- `docs/agent-os/SPEC_REVIEW_PROMPT.md` (job text below the horizontal rule; `SPEC_PATH` = `specs/002-swv2-durable-evals/spec.md`)
- `specs/002-swv2-durable-evals/intent.yaml` — governor intent for this delta
- `specs/smart-writer-v2/spec.md` — frozen v2.0 baseline this spec is a delta against
- `specs/001-factory-v2/intent.yaml` — factory rules that govern how this work is done
- `notes/sprints/2026-10-sprint-02.md`, `notes/architect-backlog.md` (A27, A28)
- Current app for factual grounding only: `apps/smart-writer-v2/` (do not review code quality)

## Product framing for this review

This is a **delta** spec. Judge whether durable state + measured quality make Smart Writer V2 a better product and a trustworthy test bed for the factory. Attack especially: whether the eval design (synthetic golden set, four judge dimensions, program-officer persona, noise-band gate, calibration threshold) could optimize the wrong thing (governor's top pre-mortem risk); whether excluding grounding from the judge is safe; whether 30-day retention plus browser-key ownership is coherent for real grant work; and whether anything in the baseline was silently thinned.

## Artifacts under review

- `specs/002-swv2-durable-evals/spec.md`, `acceptance.md`, `intent.yaml`

## Owned paths (may edit)

- `specs/002-swv2-durable-evals/SPEC_REVIEW.md` (create)

## Forbidden paths (do not edit)

- Everything else, including spec, intent, acceptance, code, `deploy/secrets/`

## Definition of Done

- [ ] `specs/002-swv2-durable-evals/SPEC_REVIEW.md` deposited in the brief's strict format (A–F)
- [ ] ≥6 findings, ≥2 Debates, ≥1 strength; IDs prefixed F; Debates tagged product or process
- [ ] Stop — do not edit the spec

## Governor locks already closed (do not re-open)

| Lock | Value |
|------|-------|
| Durable state | A27: Postgres + object storage + pipeline-step checkpointing; per-browser key |
| Migrations | A28: versioned migrations |
| Judge dimensions | funder fit, persuasive narrative, evidence of impact, organizational voice |
| Reader persona | busy foundation program officer |
| Survives restart | conversations + versions + uploads; jobs resume-or-fail |
| Retention | 30 days since last use |
| Key loss | acceptable until accounts |
| Spend | $3 hard outer limit per draft; real ceiling from measurement (D3) |
| Latency | ≈10 min |
| Model rule | best value (margin = D2) |
| Eval gate | block beyond measured noise; overridable with reason |

## Stop / escalate if

- Spec, intent, or baseline missing
