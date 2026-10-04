"""Bus message models (stub: names only; constraints land in the next commit)."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from pydantic import BaseModel, ConfigDict

MESSAGE_KINDS = (
    "order",
    "amendment",
    "handoff",
    "verdict",
    "decision_request",
    "decision_lock",
    "correction",
    "override",
    "claim",
    "release",
    "run_complete",
)


class Envelope(BaseModel):
    model_config = ConfigDict(extra="allow")

    kind: str


KIND_MODELS: dict[str, type[Envelope]] = {
    kind: type(f"Stub_{kind}", (Envelope,), {}) for kind in MESSAGE_KINDS
}


def parse_message(data: Mapping[str, Any], *, autonomy_horizon_minutes: int | None = None) -> Any:
    return KIND_MODELS[str(data["kind"])].model_validate(dict(data))
