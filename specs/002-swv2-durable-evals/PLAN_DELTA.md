# Architecture delta reconcile — 002-swv2-durable-evals (constitution §G.1)

Template: [`docs/agent-os/PLAN_DELTA_TEMPLATE.md`](../../docs/agent-os/PLAN_DELTA_TEMPLATE.md).

**Gate:** Do not spawn implement/ops workers that depend on these locks until this checklist is complete (and `/speckit-analyze` recorded). Status: **complete for D4**; D8–D10 opened by this reconcile are gated through [`FINISH_BAR.md`](./FINISH_BAR.md) § Delta addendum.

## Meta

| Field | Value |
|-------|-------|
| Feature | `specs/002-swv2-durable-evals/` |
| Date | 2026-10-03 (governor decision, recorded by the orchestrator); reconcile authored 2026-10-04 |
| OD locks in this batch | **D4** (re-lock after plan approval) |
| New ODs opened | **D8**, **D9**, **D10** (`who: human`, `open`) |
| Delta P* review | not warranted — topology, hosts, and the provider-adapter shape (PydanticAI multi-provider, per-role config) are unchanged; the delta swaps which vendor fills which role and adds one runtime secret. Re-run only if the governor asks or D9 locks as C (runtime custody change) |

## Classification

| id | arch_impact | One-line lock |
|----|-------------|----------------|
| D4 | architecture-affecting | OpenAI judges and checks source support; the writer is Anthropic; bake-off writer candidates exclude OpenAI. Judge ≠ writer family (shape lock) unchanged, letter fidelity. Superseded: Google Gemini judges, writer candidates exclude Gemini |

Why architecture-affecting: Anthropic moves into the **deployed runtime** (production + staging), not only eval CI as Gemini was; runtime secret custody gains `ANTHROPIC_API_KEY`; the runtime dependency set gains the Anthropic provider and the eval group drops the Google provider; Railway `env.required` and `/ready` change.

## Role → family map (from the code, 2026-10-04)

| Role | Code | What it does to the scored draft | Family |
|------|------|----------------------------------|--------|
| writer | `app/agents/writer.py` (`write_grant_draft`, called by `scored_loop` in generate and `scored_revise` in revise) | Authors every word of the draft the judge scores | **Anthropic** — settled by D4; `models_config` refuses an OpenAI writer id |
| judge | `evals/judge.py` (eval only) | Scores the draft per dimension | **OpenAI** — settled by D4 |
| support checker | `evals/support.py` (eval only) | Checks each cited claim against captured source text | **OpenAI** — settled by D4 (FR-013a: differs from writer) |
| assessor | `app/agents/assessor.py` (`assess_draft`, each inner turn) | Scores each turn on the internal rubric and feeds revision guidance to the writer — shapes the prose, writes none of it | **D9** (open) — product choice not settled by D4 |
| infer | `app/agents/infer.py` (`infer` node) | Slots, property ranking, search query — shapes writer input | **D9** (open) |
| extraction | `app/agents/provenance.py` (`provenance` node, after the draft is final; keeps only excerpts present in the body) + `app/agents/infer_state.py` (schema-first slot agent, not on the HTTP path today) | Maps finished claims to sources; the support checker then grades those mappings | **D9** (open) |

Interpretation recorded (letter): "the writer moves to Anthropic" = an Anthropic-only writer, so bake-off writer candidates are Anthropic models (which also satisfies "exclude OpenAI"). A non-Anthropic, non-OpenAI writer candidate would need a new governor decision and a third key.

## Artifacts amended

- [x] `plan.md` Architecture — Summary; External systems + role → family map; Secret custody; Major risks (unmeasured first writer switch; subset fit vs writer price); Phased delivery P0 / P1a / P2b exits; Technical Context deps (`pydantic-ai-slim[openai,anthropic]`); Constitution Check; Complexity Tracking; amendment note under Approval
- [x] `data-model.md` — **no change**: no entity, field, or table changes (model ids live in Settings; bake-off records and judge scores already carry model ids per spec Key Entities)
- [x] `contracts/` — `contracts/evals.md`: new § Model families; judge and support output headings → OpenAI. `contracts/http-api-delta.md`: no change (no API shape changes)
- [x] `research.md` overturned Decisions — § Search/LLM, § Evals evaluators, § Secrets, § Topology custody, locks line; new § Amendment 2026-10-03 with alternatives (Gemini judge, swapped roles, OpenRouter)
- [x] `tasks.md` appended/adjusted (no renumber): T001, T007, T011, T012, T014, T015, T019, T020, T026, T030, T033, T050, T073, T077, T082, T084, T091, T093 amended; **T105 `[OD:D8]`**, **T106 `[OD:D9]`** (Phase 4, before T030), **T107 `[OD:D10]`** (Phase 8, before T082) added; header, legend, checkpoints, dependencies, owned paths, parallel example updated
- [x] `spec.md` — D4 row re-locked with `arch_impact: architecture-affecting`, `fidelity: letter`; D8–D10 rows added; US2 #6, FR-009, FR-015, Assumptions, Status, Review locks (D4 re-lock row); US5 role list adds infer
- [x] `acceptance.md` — `eval.judge_family` shall names the families; change log row
- [x] `intent.yaml` — locks line, `open_content` (D8–D10), confirmation entry; SW-M1 role list
- [x] `quickstart.md` — step 6a (model-family checks, keys for live runs)
- [x] `FINISH_BAR.md` — Delta addendum row, delta inventory, three governor questions, outcome
- [x] `checklists/requirements.md` — Open Decisions range D1–D10

## Secret names (D4 consequences)

| Where | Before | After |
|-------|--------|-------|
| Vault (Infisical `production`, `/`) | `GEMINI_API_KEY` (new) | `ANTHROPIC_API_KEY` (new); `OPENAI_API_KEY` unchanged |
| `deploy/secrets/schema.yaml` production / staging | `OPENAI_API_KEY` | `OPENAI_API_KEY` + `ANTHROPIC_API_KEY` (both `required: true`) — T014 |
| CI (`tooling:` GitHub Actions target + repo secrets) | `OPENAI_API_KEY`, `GEMINI_API_KEY`, … | `OPENAI_API_KEY` (judge + support), `ANTHROPIC_API_KEY` (eval drafts), … — T014, T019, T077, T084 |
| Settings `ALL_ENV_NAMES` / `REQUIRED_ENV_NAMES` | `OPENAI_API_KEY` required | `ANTHROPIC_API_KEY` added to both — T007 (T106 drops `OPENAI_API_KEY` from required only if D9 = C) |
| Railway `env.required` (production, staging) | `OPENAI_API_KEY` | `OPENAI_API_KEY`, `ANTHROPIC_API_KEY` — same commit as T007 / T015 (validator demands exact equality) |

## Remaining gaps → tasks

| Gap | Task id |
|-----|---------|
| Interim Anthropic writer model (content) | T105 `[OD:D8]` → before T030 |
| Families of assessor / infer / extraction (product choice) | T106 `[OD:D9]` → before T030 and T026's role-family clause |
| Interim OpenAI judge + support models (content; the bake-off ranking rule is kept) | T107 `[OD:D10]` → before T082 |
| `ANTHROPIC_API_KEY` must reach production before any production ship containing T007 / T030 (`/ready` 503 otherwise) | T019 → T020 (dependency recorded) |
| Per-PR paired subset may not cover every tuning category within ~$1.50 at the D8 writer price | T079 dry-run; escalate to the governor if it does not fit (plan § Major risks) |
| First production writer switch (gpt-4o → D8 model) ships before the eval workflow exists, so FR-016 cannot accompany it | Disclosed in the D8 question; FR-016 applies from T084's merge |

## `/speckit-analyze` result

| Field | Value |
|-------|-------|
| Date run | 2026-10-04, over spec / plan / tasks (107 tasks) + Open Decisions + FINISH_BAR + contracts + acceptance + intent |
| Outcome | **gaps** — 4 critical by rule (open `who: human` ODs: D3 by design, D8, D9, D10 → questions in FINISH_BAR), 2 high and 4 medium fixed in place or disclosed, 3 low fixed/recorded. Coverage unchanged: FR-001..FR-022 + FR-004a / FR-013a / FR-013b (25) and SC-001..SC-014 (14) each map to ≥ 1 task (100%); every open human OD has an `[OD:D#]` task |
| Notes | See findings below |

### Findings

| ID | Category | Severity | Location(s) | Summary | Disposition |
|----|----------|----------|-------------|---------|-------------|
| G1 | Open Decisions | CRITICAL (rule) | spec D8, D9, D10 | New open `who: human` rows block the P1a packet (T030) and the P2b packet (T082) | **Question** — FINISH_BAR § Delta questions 1–3; tasks T105–T107 |
| G2 | Open Decisions | CRITICAL (rule) | spec D3 | Open by design until bake-off (governor answer A, 2026-10-03) | Unchanged — T097 |
| F1 | Inconsistency | HIGH | tasks T015, T050 vs `scripts/validate_deploy_env.py` | Pre-existing: the validator requires manifest `env.required` == `REQUIRED_ENV_NAMES` both ways, but T015/T050 listed database/Storage names as required while T007 kept `REQUIRED_ENV_NAMES` at OpenAI only — CI would fail; adding `ANTHROPIC_API_KEY` hit the same rule | **Fixed** — T007 rule (whoever changes `REQUIRED_ENV_NAMES` edits every manifest in the same commit); T015 uses `env.optional` for database names until T050; T050 moves them with `REQUIRED_ENV_NAMES` (order amendment); owned paths updated |
| F2 | Inconsistency | HIGH | tasks T014 vs `scripts/validate_secrets_schema.py` | Pre-existing: schema names must already be in Settings `ALL_ENV_NAMES`, but T014 (P0, Wave 1) could land before T007 (CP0) | **Fixed** — T014 lands after T007 (orchestrator lands T007 first as tiny glue if P0 runs earlier); dependency chain recorded |
| F3 | Underspecification | MEDIUM | tasks T007, T020, T030 | `ANTHROPIC_API_KEY` in `REQUIRED_ENV_NAMES` makes production `/ready` 503 until the key is synced | **Fixed** — no production ship containing T007/T030 before T020's production sync |
| F4 | Constitution / FR-016 | MEDIUM | plan § Major risks; spec FR-016 | The P1a ship changes the production writer model before the eval workflow exists, so FR-016's full eval run cannot accompany it | **Disclosed** — plan risk + stake in the D8 question; FR-016 applies from T084 |
| F5 | Coverage | MEDIUM | plan § Major risks; spec FR-011; tasks T079 | The D8 writer price drives whether the per-PR paired subset covers every category within ~$1.50 | **Disclosed + escalation path** — D8 question shows per-PR cost per option; T079 dry-run escalates rather than shrinking coverage |
| F6 | Underspecification | MEDIUM | tasks T033, T082 | Price table must cover the new Anthropic default and the OpenAI judge/support ids or the meter / ledger fail closed | **Fixed** — T033 (D8 row, prices re-verified with source + date), T082 (D10 rows); Evals owned paths extended for P2b |
| L1 | Fidelity (§I) | LOW | research § Amendment; tasks T091, T093 | "Writer moves to Anthropic" read as Anthropic-only writer candidates | **Recorded** as letter interpretation; widening is a new governor decision |
| L2 | Terminology | LOW | spec US5, intent SW-M1 vs plan/tasks | Role list omitted `infer` | **Fixed** |
| L3 | Staleness | LOW | `checklists/requirements.md`; tasks legend | "D1–D5" and `[OD:D3]`-only legend | **Fixed** (D1–D10; `[OD:D#]`) |

### Deferral-word scan

`specs/002-swv2-durable-evals/**` new and amended lines: every `later` / `optional` / `deferred` / `TBD` / `future` / `stretch` occurrence is inside a code span, carries a D# id, a `→` pointer, or `[governor-judged]` (checked with `rg` on 2026-10-04).

## Forbidden (honored)

- No new feature directory solely for OD fills
- No stock `/speckit-plan` setup replacing `plan.md`
- Human chat line: "Architecture delta reconcile done" (D4); D8–D10 posed as plain choices
