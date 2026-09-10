# Work packets

Executable units on the **artifact bus**. Agents (session or background) pick up a packet instead of receiving pasted chat.

```text
notes/packets/
  _TEMPLATE.md
  <id>.md
```

## Rules

1. Packet must point at an approved spec/plan (or explicitly say “tiny fix — no spec”).
2. Owned / forbidden paths are hard boundaries.
3. DoD must be machine-checkable (named tests / commands).
4. Status updates happen in the packet file + PR — not only in chat.

See `docs/agent-os/README.md` and skill `sdd-packet` / `sdd-implement`.
