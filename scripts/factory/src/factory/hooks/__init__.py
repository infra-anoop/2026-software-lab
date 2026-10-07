"""Cursor hooks (contracts/hooks.md): advisory editor mirrors of CI gates.

Modules here import only the standard library and PyYAML, so the `factory-hook` console
script stays inside the 300 ms budget: no pydantic models, no Typer app, no other
slices' packages.
"""
