"""A21: vault → runtime secret sync (adapters; no Infisical↔Railway monolith)."""

from __future__ import annotations

from .protocols import RuntimeTarget, VaultBackend, VaultRef
from .schema import SecretEntry, load_secret_entries
from .sync import SyncPlan, build_plan, run_apply, run_dry_run

__all__ = [
    "RuntimeTarget",
    "SecretEntry",
    "SyncPlan",
    "VaultBackend",
    "VaultRef",
    "build_plan",
    "load_secret_entries",
    "run_apply",
    "run_dry_run",
]
