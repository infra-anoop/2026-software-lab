# Spawn workers (implement / ops) — fail closed

Companion to [`SPAWN_REVIEWER.md`](./SPAWN_REVIEWER.md). Reviewers stay isolated; **workers** do real implement/ops work so the **main session stays governor dialogue + orchestration**.

Constitution: §F (roles), §H (orchestrator / workers), **§I (locked-intent fidelity)**. Human is governor, not parallelism router.

## Roles

| Role | Session | Does | Must not |
|------|---------|------|----------|
| **Main (orchestrator)** | Chat with the human | Open Decisions, product Debates, write/update packets, **spawn** workers/reviewers, triage results in product language, tiny glue | Bulk implement, long pytest loops, “sit and wait” blocking the human turn when background spawn is available |
| **Worker** | Spawned Task (prefer **background**) | Packet DoD: code, tests, commits on owned paths | Re-open product Debates in jargon; expand Out-of-scope; ask human “what next”; invent fidelity substitutes (§I) |
| **Reviewer** | Spawned Task | F*/R*/P*/T* only — see `SPAWN_REVIEWER.md` | Product code |

## When to spawn a worker (default)

| Situation | Action |
|-----------|--------|
| Non-trivial implement slice (story phase, polish with code, multi-file DoD) | Packet from `_TEMPLATE.md` + spawn worker (**background**) |
| `[P]` tasks with **disjoint** owned paths | **One worker per parallel group** (or one worker per task if truly independent) — harness decides; do not ask the human |
| Conflicting paths / shared files / sequential deps | **One** worker; serial |
| Long ops / cattle packet | Packet + background worker |
| Independent review | `SPAWN_REVIEWER.md` (not this file) |

## Tiny-glue exception (main may edit)

Main may touch git **without** a worker only when **all** hold:

1. ≤ ~15 minutes wall estimate
2. No new contract/catalog-auto tests requiring T*
3. Docs/lock tables/packet meta/checkboxes only — or a one-line pointer fix
4. No `[P]` fan-out

If unsure → packet + worker.

## Authoring / main agent MUST

1. Write or update `notes/packets/<id>.md` from [`notes/packets/_TEMPLATE.md`](../../notes/packets/_TEMPLATE.md). Set `Agent mode: background` when spawning async. Fill the **Fidelity** table (constitution §I); default locks to **letter**.
2. Ensure `FINISH_BAR.md` exists for the feature with **Implement unblocked: yes** (§G.2), unless the packet is tiny-glue or Out-of-scope excludes all finish-bar rows. Ensure Governor locks / Open Decisions needed by the packet are locked (not open). If locks were **architecture-affecting**, require feature `PLAN_DELTA.md` §G.1 checklist complete before spawn — else main must reconcile first.
3. **Fidelity disclose-or-stop (§I):** If the packet would satisfy a lock via substitute (tool/host/thinner stand-in / “-class”), **do not spawn**. Pose plain A/B to the human; record waive or letter path in the packet Fidelity table; then spawn.
4. **Spawn** worker with pointer prompt (not a pasted novel):

   ```text
   You are a lab implementer worker. Ignore parent-thread loyalty for product inventing.
   Read docs/agent-os/SPAWN_WORKER.md.
   Read notes/packets/<id>.md.
   Read AGENTS.md and the feature spec/plan named in the packet.
   Git + those files are the only source of truth.
   Honor Fidelity table (constitution §I): no silent substitutes.
   Do the Definition of Done. Stay inside Owned paths.
   Prefer background-friendly commits. Stop when DoD is met or Stop/escalate triggers.
   ```

5. Prefer **background** spawn so the main session stays free for human dialogue. Tell the human only: worker spawned, packet path, DoD summary in product language. Do **not** ask whether parallelism is OK when `[P]` + disjoint paths already say so.
6. When the worker finishes: read handoff notes / diff; present product-altitude status; spawn T* if new red contract tests exist; resume next packet or stop at checkpoint. Do **not** ask “what next.”

## Parallelism rules (automatic)

1. Parse `tasks.md` for `[P]` and file paths in the task text / packet owned paths.
2. If two ready tasks are both `[P]` and owned paths do not overlap → spawn **parallel** workers (or one worker with explicit parallel DoD covering both).
3. If paths overlap or either task lacks `[P]` → **serial**.
4. Never ask the human to decide parallel vs serial when the graph is clear.

## MUST NOT

- Become an orchestrator that never lands git (theater). Workers must produce DoD; main verifies.
- Block the human chat waiting on a long worker when background spawn is available.
- Ask the human “can we parallelize?” when `[P]` + disjoint paths apply.
- Paste full task lists or finding IDs into human chat.
- Invent Open Decision content (`who: human`).
- **Silently dilute locks** (constitution §I) — no “v0-class”, “approx”, or thinner SC without recorded human waive.
- Start dependent implement when architecture-affecting ODs locked but §G.1 `PLAN_DELTA.md` is missing/incomplete.
- Start product implement when `FINISH_BAR.md` is missing or **Implement unblocked** is not **yes** (§G.2).

## Isolation bar

Workers SHOULD NOT receive the full parent coaching transcript as the source of truth. Packet + git artifacts are the bus. Cursor Task subagents without parent chat meet the bar; if the tool shares context, still treat the packet as authoritative.
