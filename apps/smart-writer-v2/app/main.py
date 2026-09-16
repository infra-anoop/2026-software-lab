"""CLI stub. The P1 surface is the HTTP worker, not this module."""

from __future__ import annotations


def main() -> None:
    """Print how to run the FastAPI worker."""
    print("smart-writer-v2: uv run uvicorn app.entrypoints.http:app --reload --host 0.0.0.0 --port 8080")


if __name__ == "__main__":
    main()
