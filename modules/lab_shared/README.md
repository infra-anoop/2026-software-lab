# lab-shared

Installable shared Python for lab apps. **Cattle rule:** identical infrastructure has one home here; apps keep product logic.

## Contents

| Module | Role |
|--------|------|
| `lab_shared.jobs` | In-memory HTTP job runner (`Job`, `JobRunner`, rate limiter). Not durable (architect A9). |
| `lab_shared.db` | `get_supabase_client`, `RunRepo` protocol, `NullRepo`, `SupabaseRepo` |

## How apps depend on it

From `apps/<name>/pyproject.toml`:

```toml
dependencies = [
  # ...
  "lab-shared",
]

[tool.uv.sources]
lab-shared = { path = "../../modules/lab_shared", editable = true }
```

Then regenerate the lockfile from the app directory:

```bash
cd apps/<name> && uv lock && uv sync
```

Import from the package (hard cut — no `app.db` / `app.entrypoints.jobs` shims):

```python
from lab_shared.jobs import Job, JobRunner, QueueFullError, SlidingWindowRateLimiter
from lab_shared.db.client import get_supabase_client
from lab_shared.db.null_repo import NullRepo
from lab_shared.db.repo import RunRepo
from lab_shared.db.supabase_repo import SupabaseRepo
```

App-level factories such as `get_repo()` stay in the app (product wiring).

## Nix / OCI

- **Lint / tests / CLI:** `flake.nix` assembles a mini monorepo (`apps/<id>` + `modules/lab_shared` + `db/supabase`) so the lockfile path `../../modules/lab_shared` resolves.
- **Containers:** bake under `apps/<id>` + `modules/lab_shared`, then symlink `/app` → `apps/<id>` so Railway `start_command` / verify-source can keep using `/app/.venv/...`.
