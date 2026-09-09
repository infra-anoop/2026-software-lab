"""Orchestrate dry-run / apply sync (never log secret values)."""

from __future__ import annotations

from dataclasses import dataclass

from .protocols import RuntimeTarget, UpsertResult, VaultBackend
from .schema import SecretEntry, assert_names_in_schema


@dataclass(frozen=True)
class SyncPlan:
    app_id: str
    environment: str
    target_label: str
    names: tuple[str, ...]
    required_names: tuple[str, ...]


def build_plan(
    *,
    app_id: str,
    environment: str,
    entries: list[SecretEntry],
    target: RuntimeTarget,
) -> SyncPlan:
    return SyncPlan(
        app_id=app_id,
        environment=environment,
        target_label=target.label,
        names=tuple(e.name for e in entries),
        required_names=tuple(e.name for e in entries if e.required),
    )


def run_dry_run(plan: SyncPlan) -> list[str]:
    """Return printable lines (names only)."""
    lines = [
        f"app_id={plan.app_id}",
        f"environment={plan.environment}",
        f"target={plan.target_label}",
        f"secrets ({len(plan.names)}):",
    ]
    for name in plan.names:
        flag = "required" if name in plan.required_names else "optional"
        lines.append(f"  - {name} ({flag})")
    return lines


def run_apply(
    *,
    entries: list[SecretEntry],
    vault: VaultBackend,
    target: RuntimeTarget,
) -> UpsertResult:
    """Fetch from vault and upsert onto target. Values never printed."""
    assert_names_in_schema({e.name for e in entries}, entries)
    target.resolve_footprint()

    refs = [e.vault_ref for e in entries]
    # Map vault key → value; then map schema name → value via vault_ref.key
    by_key = vault.get_secrets(refs)
    variables: dict[str, str] = {}
    missing_required: list[str] = []
    skipped_optional: list[str] = []

    for entry in entries:
        key = entry.vault_ref["key"]
        if key not in by_key or by_key[key] == "":
            if entry.required:
                missing_required.append(entry.name)
            else:
                skipped_optional.append(entry.name)
            continue
        variables[entry.name] = by_key[key]

    if missing_required:
        raise ValueError(f"required secrets missing from vault: {missing_required}")

    if not variables:
        raise ValueError("no secrets to upsert (all missing or empty)")

    result = target.upsert_variables(variables)
    # Attach skipped as noop-style names without values
    noop = list(result.get("noop", []))
    for name in skipped_optional:
        if name not in noop:
            noop.append(name)
    return {"upserted": list(result["upserted"]), "noop": noop}
