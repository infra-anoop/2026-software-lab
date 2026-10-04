"""Factory v2: typed append-only bus, derived board, and intent-fidelity gates."""

from pathlib import Path

__version__ = "0.1.0"

PROJECT_DIR = Path(__file__).resolve().parents[2]
"""The `scripts/factory/` uv project (holds `gates.yaml` and `schemas/`)."""
