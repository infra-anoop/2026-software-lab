# Slice C — carry into implementation spawn

- Resolved round 2 (2026-10-04): spawn-guard LOG-ONLY (governor); research.md hooks block updated in round-2 triage; `.cursor/hooks/factory-hook.sh` accepted.
- PR merge order: slice A adds pyjwt to pyproject/uv.lock; slice C adds [project.scripts] factory-hook line → second merger rebases, regenerate uv.lock.
- `.cursor/hooks.json` lands with slice C PR → may count as governor-approval path; check before merge.
- acceptance.md touched by A (evidence cells), B (header/schema + evidence), C (concurrency_cap row + changelog) → expect small merge conflicts.
