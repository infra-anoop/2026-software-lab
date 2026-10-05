"""Slice B drift gates (tasks.md T042-T048; contracts/gates.md § P1 registry).

Each module exposes the registry entrypoints named in `scripts/factory/gates.yaml`.
Gates read the repository through git at `GateContext.base_sha` / `head_sha` and the
bus snapshot; they never read the checkout and never write to the repository.
"""
