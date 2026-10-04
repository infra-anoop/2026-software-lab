# Data model — 001-factory-v2

All entities are immutable YAML files under `bus/` (except config and registry), validated by Pydantic models in `factory.bus`. **No entity has a status field**: state is derived (see Lifecycle). Every message has the common envelope below.

## Common envelope

| Field | Type | Rule |
|-------|------|------|
| `schema_version` | int | `1` |
| `kind` | enum | `order` \| `amendment` \| `handoff` \| `verdict` \| `decision_request` \| `decision_lock` \| `correction` \| `override` \| `claim` \| `release` \| `run_complete` |
| `id` | str | Unique; pattern per kind (below) |
| `created` | datetime (UTC) | Set at write |
| `actor` | enum | `governor` \| `orchestrator` \| `worker` \| `reviewer` |
| `actor_model` | str? | Required for non-governor actors (e.g. `claude-opus-…`, `gpt-5.6-…`) |
| `actor_verified` | bool | Derived by `identity` adapter; `false` for `governor` until identity mode is `verified` (GitHub App live, D4-A) |
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

**Lock**: `{ id, letter_tokens: list[str], fidelity: letter|intent|waived, waiver_ref?: str, substitutes?: list[str] }`. `letter_tokens` are the named things (tool, host, cap) the output must contain or honor; `fidelity: letter` requires a non-empty `letter_tokens`. `substitutes` are known alternatives (e.g. another host) that must not appear in the added code; none may repeat a letter token. `fidelity: waived` requires `waiver_ref` to a governor decision lock.

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

## Run events (append-only; replace a mutable run record — review P1)

Measurements are separate immutable events on the order's branch; the scorecard aggregates them on read.

| Kind | Id | Written by | Fields |
|------|----|-----------|--------|
| `claim` | `<order-id>.claim` | worker via `factory claim` | `claimed_at`, `worker_runtime`, `actor_model` |
| `release` | `<order-id>.release` | orchestrator | `reason` (`abandoned` \| `superseded` \| `blocked`); frees capacity |
| `run_complete` | `<order-id>.run-complete` | worker in the handoff commit | `wall_minutes`, `governor_interrupts`, `cost_usd?` (estimate flag), `deviations_count` |

Rework loops, overrides, and first-pass acceptance are derived from verdicts and overrides (never self-reported). Governor minutes come from decision locks.

## Gate (registry entry, `scripts/factory/gates.yaml`)

`id`, `class: drift|governor-only`, `category: drift|spend|secrets|irreversible|governor_decision`, `intents: list`, `ci_job`, `hook_twin_of?`, `priority: P1|P2|P3`, `scope: changed_lines|repo|pr`, `entrypoint: "module:function"`. Rule: `class: governor-only` ⇔ `category ∈ {spend, secrets, irreversible, governor_decision}`.

## Lifecycle (derived — never stored)

Two PR kinds reach protected `main` (review P2):

- **Work PR**: branch `wo/<order-id>`. The order is the branch's **first commit**, pushed by `factory order issue` (issuance never pushes to `main`). Claim, amendments, handoff, run events, verdicts, and overrides are later commits on the same branch. One order = one branch = one PR (FR-005); the order reaches `main` when the work merges.
- **Bus PR**: branch `bus/<date>-<slug>`, containing only `bus/decisions/`, `bus/corrections/`, `bus/postmortems/` files. Schema gates only; the orchestrator merges on green. A governor lock counts as **verified** when the governor's own identity approves that PR (requires D4 option A).

```text
issued        origin has wo/<order-id> whose first commit adds bus/orders/<order-id>/order.yaml; no claim event
claimed       claim event on the branch; no release event
in_review     open PR with head wo/<order-id>
accepted      latest verdict = accept AND required checks green (or overridden)
rejected      latest verdict = reject → correction expected; new order for rework
merged        PR merged
released      release event on the branch, OR PR closed unmerged (excluded from active)
stale (overlay)                claimed, no PR, and no commit for > 3 × size_minutes → flagged on the board;
                               still counts toward the cap until released (conservative)
blocked_on_governor (overlay)  depends_on_decisions has an open human decision
                               OR handoff has a blocker_governor question without a lock
ready queue   issued ∧ ¬claimed ∧ ¬blocked_on_governor
```

**Claim atomicity:** the claim commit is a fast-forward push to `wo/<order-id>`, so two concurrent claims of the same order cannot both succeed (git rejects the non-fast-forward). **Cap:** `active = (claimed ∪ in_review) − released`; `factory claim` refuses at `|active| ≥ cap` or when owned paths intersect an active order. The CI twin replays claim events in timestamp order and blocks the PR whose claim exceeded the cap (closes the read-then-push race between different orders).
