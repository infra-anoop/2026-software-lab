"""Resolved prompt parameters (defaults when the user omits style constraints)."""

from __future__ import annotations

from pydantic import BaseModel, Field


class PromptParameters(BaseModel):
    """Template variables for role system prompts; no LLM inference — defaults + optional overrides only."""

    audience: str = Field(
        default="general",
        description="Intended readership when unstated in the user prompt.",
    )
    writing_register: str = Field(
        default="professional",
        description="e.g. professional, conversational, formal.",
    )
    length_target: str = Field(
        default="medium",
        description="Desired length band when unstated, e.g. short, medium, long.",
    )
    risk_tolerance: str = Field(
        default="balanced",
        description="Hedging vs assertive tone when unstated, e.g. conservative, balanced, bold.",
    )
    formality: str = Field(
        default="neutral",
        description="Formality level when unstated.",
    )
