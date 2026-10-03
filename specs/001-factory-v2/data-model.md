# Data model — 001-factory-v2

All entities are immutable YAML files under `bus/` (except config and registry), validated by Pydantic models in `factory.bus`. **No entity has a status field**: state is derived (see Lifecycle). Every message has the common envelope below.

## Common envelope

| Field | Type | Rule |
|-------|------|------|
| `schema_version` | int | `1` |
| `kind` | enum | `order` \| `amendment` \| `handoff` \| `verdict` \| `decision_request` \| `decision_lock` \| `correction` \| `override` \| `run_record` |
| `id` | str | Unique; pattern per kind (below) |
| `created` | datetime (UTC) | Set at write |
| `actor` | enum | `governor` \| `orchestrator` \| `worker` \| `reviewer` |
| `actor_model` | str? | Required for non-governor actors (e.g. `claude-opus-…`, `gpt-5.6-…`) |
| `actor_verified` | bool | Derived by `identity` adapter; always `false` under D4-C for `governor` |
| `refs` | list[str] | Ids or repo paths this message references |

Forbidden keys in any message: `status`, `state`, `done`, `progress` (FR-003, I-M2).

## WorkOrder (`kind: order`, id `wo-YYYYMMDD-<slug>`)

| Field | Type | Rule |
|-------|------|------|
| `feature` | str | Existing `specs/<feature>/` folder |
| `goal` | str | ≤ 3 sentences |
| `intents` | list[str] | Each exists in some `intent.yaml` |
| `owned_paths` | list[glob] | Non-empty; disjoint from other claimed orders' paths |
| `checks` | list[str] | Gate ids or catalog row ids; each exists |
| `locks` | list[Lock] | Named locks touched (below) |
| `size_minutes` | int | ≤ `factory.toml` `autonomy_horizon_minutes` (60) |
| `stop_conditions` | list[str] | Non-empty |
| `depends_on_decisions` | list[str] | Decision ids; issuing refused if any is open + `who: human` |
| `tasks` | list[str] | Spec Kit task ids covered (optional link to `tasks.md`) |
| `worker_runtime` | enum | `local_subagent` \| `cloud_agent` |

**Lock**: `{ id, letter_tokens: list[str], fidelity: letter|intent|waived, waiver_ref?: str }`. `letter_tokens` are the named things (tool, host, cap) the output must contain or honor. `fidelity: waived` requires `waiver_ref` to a governor decision lock.

## Amendment (`kind: amendment`, id `<order-id>.amend-NN`)

`supersedes: list[field path]` + replacement values. Same validation as the order fields it replaces. The effective order = order + amendments in order.

## Handoff (`kind: handoff`, id `<order-id>.handoff`)

| Field | Rule |
|-------|------|
| `summary` | What changed (≤ 10 lines) |
| `checks_run` | list `{gate_or_test, result}`; informational only (FR-011: self-report is not evidence) |
| `deviations` | list `{what, why, conservative_choice}`; may be empty but key required (I-B1) |
| `open_questions` | list; each classed `blocker_governor` or `non_blocking` |
| `author_model` | Required |

## Verdict (`kind: verdict`, id `<order-id>.verdict-NN`)

| Field | Rule |
|-------|------|
| `decision` | `accept` \| `reject` |
| `findings` | list `{id, severity: blocker|debate|later|nit, tag: product|process|arch, pattern_id?, text}` |
| `reviewer_model`, `reviewer_family` | Family ≠ handoff `author_model` family (FR-011) |
| `inputs` | list `{path, sha}`; every entry is a git path (no chat/transcript refs) (FR-011a) |
| `bootstrap` | bool; `true` for Wave 1 bootstrap verdicts listing `manual_equivalents` (FR-037) |

## DecisionRequest / DecisionLock (`bus/decisions/<decision-id>/`)

- **Request**: `owner: governor`, `prompt`, `options: [{label, consequences: {services?, secrets?, ops_steps?, cost?}}]` (consequences required when `arch_impact: true` — I-A10), `recommended`, `blocking: bool`, `feature`. Lint: no ids/jargon in `prompt` and `options[].label` (FR-017).
- **Lock**: `chosen`, `governor_minutes` (estimate), `notes?`. Existence of a lock closes the request.

## Correction (`kind: correction`, id `corr-YYYYMMDD-<slug>`)

`target` (order/PR/message id), `what_was_wrong`, `tag: drift|routing|smell|scope|other`, `links_to?: pattern id | correction id` (F7 repeat link), `link_confirmed?: bool` (written by a later governor lock in the batch, as a new `decision_lock`, never by editing), `proposal_ref?` (rule/check order raised).

## Override (`kind: override`, id `<order-id>.override-NN`)

`gate`, `pr`, `reason` (non-empty), `gate_class` (copied from registry). If `gate_class: governor-only` → `actor` must be `governor`, verified per D4.

## RunRecord (`kind: run_record`, id `<order-id>.run`)

`claimed_at`, `handoff_at`, `wall_minutes`, `rework_loops`, `governor_interrupts`, `governor_minutes`, `cost_usd?` (estimate flag), `overrides`, `deviations`. Combined with verdicts and corrections, this feeds the scorecard.

## Gate (registry entry, `scripts/factory/gates.yaml`)

`id`, `class: drift|governor-only`, `category: drift|spend|secrets|irreversible|governor_decision`, `intents: list`, `ci_job`, `hook_twin_of?`, `priority: P1|P2|P3`, `scope: changed_lines|repo`. Rule: `class: governor-only` ⇔ `category ∈ {spend, secrets, irreversible, governor_decision}`.

## Lifecycle (derived — never stored)

```text
issued        order file exists on main
claimed       branch wo/<order-id> exists on origin
in_review     open PR head = wo/<order-id>
accepted      latest verdict in PR head = accept AND required checks green (or overridden)
rejected      latest verdict = reject  → correction expected; new order for rework
merged        PR merged
blocked_on_governor (overlay)  depends_on_decisions has an open human decision
                               OR handoff has blocker_governor question without lock
```

Concurrency: `active = claimed ∪ in_review`; `factory claim` refuses when `|active| ≥ cap` or owned paths intersect an active order.
