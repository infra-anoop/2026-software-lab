"""Vercel RuntimeTarget stub (A21 boundary; implement later)."""

from __future__ import annotations

from typing import Mapping

from .protocols import UpsertResult


class VercelRuntimeTarget:
    """Placeholder so Vercel is a new adapter, not a rewrite."""

    @property
    def label(self) -> str:
        return "vercel (not implemented)"

    def resolve_footprint(self) -> None:
        raise NotImplementedError("Vercel RuntimeTarget is not implemented in A21")

    def upsert_variables(self, variables: Mapping[str, str]) -> UpsertResult:
        raise NotImplementedError("Vercel RuntimeTarget is not implemented in A21")
