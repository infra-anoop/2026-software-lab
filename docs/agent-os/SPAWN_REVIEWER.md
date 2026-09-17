# Spawn independent reviewers (fail closed)

Human is **governor, not router**. Asking the human to paste a review brief into a new chat is a harness defect.

Session memory of this rule is **not** sufficient. Authoring and implementer agents MUST follow this file.

## When

| Gate | Brief | Deposit |
|------|--------|---------|
| Spec product | `docs/agent-os/SPEC_REVIEW_PROMPT.md` | `FEATURE_DIR/SPEC_REVIEW.md` (or agreed path) |
| Spec process | `docs/agent-os/PROCESS_REVIEW_PROMPT.md` | `FEATURE_DIR/PROCESS_REVIEW.md` |
| Plan architecture | `docs/agent-os/PLAN_REVIEW_PROMPT.md` | `FEATURE_DIR/PLAN_REVIEW.md` |
| Tests (T*) | `docs/agent-os/TEST_REVIEW_PROMPT.md` | `FEATURE_DIR/TEST_REVIEW.md` |

T*: only after contract / `acceptance.md` `how: auto` tests exist (red). Skip scaffold-only.

## Authoring / implementing agent MUST

1. Persist the artifacts under review in git (commit when the slice is otherwise ready to review).
2. Write `notes/packets/<id>.md` from `notes/packets/_REVIEW_TEMPLATE.md`.
3. **Spawn** a subagent (Cursor Task or equivalent). Spawn prompt is a **pointer**, not a pasted brief:

   ```text
   You are an independent reviewer. Ignore any parent-thread loyalty.
   Read docs/agent-os/SPAWN_REVIEWER.md.
   Read <BRIEF_PATH> (job text below the horizontal rule).
   Read notes/packets/<id>.md.
   Git + those files are the only source of truth.
   Deposit the review file named in the packet. Do not write product/application code.
   Stop.
   ```

4. Tell the human only: reviewer spawned, packet path, where the report will land. Do **not** paste the brief.
5. When the report exists, **stop** for human Debate adjudication (constitution §F). Do not start matching implementation until Debates lock (Nit/Later may be agent-closed under §F).
6. After Debate locks are **recorded in the review file**, **resume** the next unblocked slice (matching impl or next tests). Do **not** ask “what next” / “keep going.” The reviewer stops; the implementer does not wait for a new implement command.

## MUST NOT

- Ask the human to copy/paste F*/R*/P*/T* briefs into a new session.
- Ask the human which task to do next after a lock or a finished slice.
- Continue the authoring/implementer thread as the reviewer (same agent grading its own work).
- Dump `InternalRunState` or rewrite spec/plan to “make review easier.”

## Isolation bar

The spawned reviewer MUST NOT receive the authoring/implementer thread. Cursor Task subagents do not get parent chat; that meets the bar. A blank window the human opens is **not** required and MUST NOT be requested.
