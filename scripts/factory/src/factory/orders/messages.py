"""Build, validate, and serialize bus messages the order commands write."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import UTC, datetime
from typing import Any

import yaml
from pydantic import ValidationError

from factory.bus.models import Message, parse_message
from factory.bus.store import expected_path
from factory.config.settings import Settings
from factory.orders.errors import Usage


def utc_stamp(moment: datetime) -> str:
    return moment.astimezone(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def build(data: dict[str, Any], settings: Settings) -> Message:
    try:
        return parse_message(data, autonomy_horizon_minutes=settings.autonomy_horizon_minutes)
    except ValidationError as exc:
        raise Usage(f"invalid {data.get('kind')} message: {_first_error(exc)}") from exc


def _first_error(exc: ValidationError) -> str:
    errors = exc.errors()
    if not errors:
        return str(exc)
    first = errors[0]
    where = ".".join(str(part) for part in first.get("loc", ()) if part != "kind")
    return f"{where}: {first.get('msg')}" if where else str(first.get("msg"))


def to_yaml(message: Message, *, keep_none: Iterable[str] = ()) -> bytes:
    data = message.model_dump(mode="json", by_alias=True, exclude_none=True)
    for name in keep_none:
        data.setdefault(name, None)
    if data.get("actor_verified") is False:
        del data["actor_verified"]
    return yaml.safe_dump(data, sort_keys=False, allow_unicode=True).encode()


def path_of(message: Message, settings: Settings) -> str:
    return str(expected_path(message, settings.bus_dir))
