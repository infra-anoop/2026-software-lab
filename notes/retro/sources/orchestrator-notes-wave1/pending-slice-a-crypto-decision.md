# Slice A — JWT signing dependency (orchestrator decision, 2026-10-04)

Decision: implementation signs GitHub App JWT (RS256) with `pyjwt[crypto]` (pulls `cryptography`).
Rejected: shelling out to `openssl` CLI (runtime binary dependency, hand-rolled JWT encoding, fragile in hooks/CI).
Non-sibling alternative weighed (FR-026 / I-A9): `githubkit` full GitHub SDK with built-in App auth — rejected: replaces our thin httpx adapter, larger surface.

When spawning the Slice A implementation worker, instruct it to:
- write `bus/orders/wo-20261004-factory-slice-a/amendment-02.yaml` widening owned paths to
  `scripts/factory/pyproject.toml`, `scripts/factory/uv.lock`, `specs/001-factory-v2/research.md` (new row), `specs/001-factory-v2/plan.md` (Primary Dependencies line only);
- `uv add 'pyjwt[crypto]>=2.9,<3'` in scripts/factory, commit uv.lock;
- add research.md decision row with the alternatives above.
Tell the governor (plain language) — vetoable, not blocking.
