# Acceptance catalog template

Copy to `specs/<feature>/acceptance.md`. Extensible checklist of failable checks.
Charter/spec holds **stable outcome classes**; this file holds **instances** grown from test runs.

| Field | Meaning |
|-------|---------|
| id | Stable id, e.g. `beachhead.audience_fit_min` |
| class | Maps to a Success Criteria / failable class in `spec.md` |
| severity | `must` \| `should` \| `aspirational` |
| when | Preconditions (else N/A) |
| shall | Failable statement |
| how | `auto` \| `human` \| `hybrid` |

## Checks

| id | class | severity | when | shall | how |
|----|-------|----------|------|-------|-----|
| example.placeholder | SC-001 | must | … | … | hybrid |

## Change log

| Date | Change |
|------|--------|
| YYYY-MM-DD | Initial bootstrap from spec classes |
