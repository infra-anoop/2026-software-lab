# Work packets (lab overlay)

Wrappers around Spec Kit tasks and independent reviews. Default breakdown is still `tasks.md` via `/speckit-tasks`.

```text
notes/packets/
  _TEMPLATE.md          # implement/ops worker packet (default Agent mode: background)
  _WORKER_PROMPT.md     # spawn pointer for implement workers (§H)
  _REVIEW_TEMPLATE.md   # F*/R*/P*/T* spawn (required at those gates)
  <id>.md
```

- **Review packets:** required so a spawned reviewer picks up the brief from git. See `docs/agent-os/SPAWN_REVIEWER.md`. Do **not** ask the human to paste.
- **Implement/ops packets:** **default** path for non-trivial work (constitution §H). Main orchestrates; worker executes DoD. See `docs/agent-os/SPAWN_WORKER.md`. Prefer background spawn so the human chat stays free.
- **Parallelism:** `[P]` + disjoint owned paths → parallel workers; overlapping paths → serial. Human does not decide.

See constitution §D / §H and `docs/agent-os/README.md`.
