# Quickstart — validating factory v2

Prerequisites: `nix develop`; `cd scripts/factory && uv sync --locked`; `GITHUB_TOKEN` in env for commands touching GitHub.

## 1. Seeded drift is blocked (SC-002)

```bash
uv run --project scripts/factory pytest scripts/factory/tests/seeds -v
```

Expected: one test per seed (`undeclared_substitution`, `declared_lock_violated`, `hidden_deferral`, `not_red_first`, `test_seam`, `outside_owned_paths`, `jargon_to_governor`, `catalog_unlinked`) each asserting the gate exits `1` with the gate id in output.

## 2. Board matches reality (SC-001)

```bash
uv run --project scripts/factory pytest scripts/factory/tests/contract/test_status.py -v
factory status
```

The contract test builds a fixture repo with orders in every lifecycle state and asserts the JSON board equals the expected derivation. Live: `factory status` lists real orders; compare with GitHub PR list.

## 3. Overrides are reasoned and counted (SC-004)

```bash
factory override <order-id> --gate red-first-proof --reason ""      # exit 2
factory override <order-id> --gate red-first-proof --reason "flaky base"   # ok, board shows count 1
factory override <order-id> --gate order-blocked-on-open-human-od --reason "x"  # exit 2 (governor-only)
```

## 4. Traceability (SC-005)

```bash
factory check intent              # presence: exit 0; remove an intent's checks in a fixture → exit 1
factory check intent --coverage   # prints effective coverage %
```

## 5. Claim refuses (FR-007/008)

With 3 active orders: `factory claim <4th>` → exit 2 "cap 3 reached". Order depending on an open governor decision → exit 2 naming the decision in plain language.

## 6. Retro / bootstrap (SC-012)

```bash
factory retro --since <first-wave1-merge>^
```

Report lists every Wave 1 PR, gate results, and whether each failure has a remediation order or override.
