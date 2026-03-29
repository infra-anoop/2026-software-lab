"""Merge decoder output with designer craft rows and normalize weights (design §7.5)."""

from __future__ import annotations

import json
import os
from typing import Any

import logfire

from app.agents.craft_values import build_craft_template, default_craft_keys
from app.agents.models import (
    DEFAULT_CRAFT_WEIGHT_MASS,
    ComposedValues,
    DecodedValues,
    ValueDefinition,
)


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None or not str(raw).strip():
        return default
    return str(raw).strip().lower() in ("1", "true", "yes", "on")


def _env_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None or not str(raw).strip():
        return default
    try:
        return float(str(raw).strip())
    except ValueError:
        return default


def _parse_value_weights_json() -> dict[str, float]:
    raw = os.getenv("SMART_WRITER_VALUE_WEIGHTS")
    if raw is None or not str(raw).strip():
        return {}
    try:
        data: Any = json.loads(raw)
    except json.JSONDecodeError:
        logfire.warning("SMART_WRITER_VALUE_WEIGHTS invalid JSON; ignoring overrides")
        return {}
    if not isinstance(data, dict):
        return {}
    out: dict[str, float] = {}
    for k, v in data.items():
        if isinstance(k, str) and isinstance(v, (int, float)) and float(v) > 0:
            out[k] = min(10.0, float(v))
    return out


def _craft_keys_from_env() -> list[str] | None:
    raw = os.getenv("SMART_WRITER_CRAFT_KEYS")
    if raw is None or not str(raw).strip():
        return None
    parts = [p.strip() for p in raw.split(",") if p.strip()]
    return parts if parts else None


def _apply_raw_overrides(values: list[ValueDefinition], overrides: dict[str, float]) -> None:
    for v in values:
        if v.value_id in overrides:
            v.raw_weight = overrides[v.value_id]


def compose_values(
    decoded_raw: DecodedValues,
    *,
    library_domain_rows: list[ValueDefinition] | None = None,
    craft_enabled: bool | None = None,
    craft_keys: list[str] | None = None,
    craft_weight_mass: float | None = None,
    raw_weight_overrides: dict[str, float] | None = None,
) -> ComposedValues:
    """Inject craft rows, optional library rows, then task-derived decoder rows; assign ``weight`` per §7.5.

    **Merge order:** ``craft`` (if any) → ``library_domain_rows`` (``library_canonical``) →
    ``decoded_raw.values`` (``task_derived``). Library rows are **not** part of ``DecodedValues``;
    they are injected here (design §6).

    When ``craft_enabled`` is None, reads ``SMART_WRITER_CRAFT_ENABLED`` (default on).
    When ``craft_weight_mass`` is None, reads ``SMART_WRITER_CRAFT_WEIGHT_MASS``.
    """
    if craft_enabled is None:
        craft_enabled = _env_bool("SMART_WRITER_CRAFT_ENABLED", True)
    alpha = (
        float(craft_weight_mass)
        if craft_weight_mass is not None
        else _env_float("SMART_WRITER_CRAFT_WEIGHT_MASS", DEFAULT_CRAFT_WEIGHT_MASS)
    )
    alpha = max(1e-9, min(1.0 - 1e-9, alpha))

    keys = craft_keys if craft_keys is not None else _craft_keys_from_env()
    if keys is None:
        keys = default_craft_keys()

    merged_overrides = dict(_parse_value_weights_json())
    if raw_weight_overrides:
        merged_overrides.update(raw_weight_overrides)

    craft_rows: list[ValueDefinition] = []
    if craft_enabled:
        for ck in keys:
            try:
                t = build_craft_template(ck)
            except KeyError:
                logfire.warning("Unknown craft key in SMART_WRITER_CRAFT_KEYS; skipping", craft_key=ck)
                continue
            craft_rows.append(
                ValueDefinition(
                    value_id=t.value_id,
                    name=t.name,
                    description=t.description,
                    raw_weight=t.default_raw_weight,
                    craft_key=t.craft_key,
                )
            )

    task_derived_rows: list[ValueDefinition] = []
    for v in decoded_raw.values:
        task_derived_rows.append(
            ValueDefinition(
                value_id=v.value_id,
                name=v.name,
                description=v.description,
                raw_weight=v.raw_weight,
                canonical_id=v.canonical_id,
            )
        )

    lib_rows: list[ValueDefinition] = []
    if library_domain_rows:
        for v in library_domain_rows:
            if v.canonical_id is None:
                raise ValueError("library_domain_rows must be library_canonical rows (canonical_id set).")
            lib_rows.append(v)

    # Domain pool: library first, then task-derived (stable sort for rubrics / assessors).
    domain_rows: list[ValueDefinition] = lib_rows + task_derived_rows

    _apply_raw_overrides(craft_rows, merged_overrides)
    _apply_raw_overrides(domain_rows, merged_overrides)

    k_list = craft_rows
    d_list = domain_rows
    sum_c = sum(x.raw_weight for x in k_list)
    sum_d = sum(x.raw_weight for x in d_list)

    if sum_d <= 0:
        raise ValueError("Domain raw weights must sum to a positive value.")

    if not k_list:
        # Craft off or empty: domain only, weights sum to 1.
        for x in d_list:
            x.weight = x.raw_weight / sum_d
        ordered = list(d_list)
        return ComposedValues(values=ordered)

    # Both groups non-empty: two-stage normalization (§7.5).
    c_norm = [x.raw_weight / sum_c for x in k_list]
    d_norm = [x.raw_weight / sum_d for x in d_list]
    for i, x in enumerate(k_list):
        x.weight = alpha * c_norm[i]
    for i, x in enumerate(d_list):
        x.weight = (1.0 - alpha) * d_norm[i]

    ordered = k_list + d_list
    return ComposedValues(values=ordered)
