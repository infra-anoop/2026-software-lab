# 2026-software-lab
A monorepo to work on 2026 hacks, POCs and experiments

Cattle-First Dev & Deploy Cheat Sheet (Codespaces + Cursor + Nix + uv + GitHub Actions + Railway)
Guiding Principle

Nothing important lives only in a running container.
Everything that matters is declared, versioned, and rebuildable from repo state.

The Layers (from outermost → innermost)
Layer 0 — Source of Truth: Git repo

Everything reproducible is declared in the repo (or in secret stores).
If it’s not in Git (or securely in GitHub/Railway secrets), it’s not part of the cattle system.

Design → Build → Test → Deploy mapping

Design: docs/ADRs/diagrams/specs live here

Build/Test: build recipes and CI definitions live here

Deploy: deployment manifests live here

Gotchas

“It works on my container” is a red flag. Make it declarative.

Avoid hand-tweaking $HOME as the source of truth.

Layer 1 — Compute & Runtime: GitHub Codespaces

Codespaces is your cattle compute:

A VM + persistent workspace volume at /workspaces

Your repo checkout + .git state persist across rebuilds

Primary operations

Restart: refresh session/environment injection (often enough for secrets)

Rebuild Container: reapply .devcontainer definition (for toolchain changes)

Delete Codespace: nuke the whole VM + workspace volume (last resort)

Gotchas

Rebuild resets the environment, not your git branch state in /workspaces.

Don’t confuse Codespace (resource) with container (implementation detail).

Layer 2 — Machine Spec: .devcontainer/ (operated by GitHub)

This is your “OS image recipe” for the dev environment.

Your statement (correct):

Instructions to build the container are in .devcontainer and are operated by GitHub.

What belongs here

Base image selection

Devcontainer features (sshd, docker-in-docker, nix, node, etc.)

Editor extensions/settings (for VS Code family, including Cursor)

postCreateCommand for one-time bootstrapping

Optional: postStartCommand for every-start actions (use sparingly)

Gotchas to avoid

Don’t put secrets in devcontainer config.

Don’t put long, brittle installs in postCreateCommand unless pinned/checked.

Avoid “Reopen in Container” in Cursor when you are already in Codespaces (can create split-brain environments).

Layer 3 — System Packages: flake.nix (operated by Nix)

Your statement (correct):
2) All non-Python packages are in flake.nix and operated by Nix.

What belongs here

CLI tools you want identical everywhere: git, jq, ripgrep, fd, node, etc.

Toolchains if needed

System-level deps your Python packages may require (openssl headers, etc., if you go that route)

Best practice

Prefer nix develop (dev shell) to make tools available consistently

Pin flake inputs so tool versions don’t drift (flake.lock is part of cattle)

Gotchas

Don’t rely on apt-get for durable installs (it drifts).

Keep Nix as the “system dependency truth,” not $HOME/.local.

Layer 4 — Python Runtime & Dependencies: pyproject.toml + uv (+ uv.lock)

Your statement (correct):
3) All Python packages are in pyproject.toml and operated by uv.

What belongs here

Python deps pinned via uv.lock

Tooling config (formatters/linters/test runners)

Script entrypoints

Best practice

Commit uv.lock (this is your reproducibility anchor)

Prefer a project venv (.venv) created by uv

Use uv sync --locked everywhere (local + CI)

Gotchas

pip install ad-hoc inside the container = pet behavior

If you install something manually, add it to pyproject.toml and re-lock

Layer 5 — Editor Behavior & Guardrails: .cursorrules (operated by Cursor)

This is your “design-time constraints and conventions” layer for how Cursor assists you.

What belongs here

Repo-specific rules: coding style, project layout conventions

Safety rails: “don’t write secrets”, “don’t run destructive commands”, etc.

Workflow discipline: “use uv”, “don’t pip install”, “don’t reopen in container”, etc.

How it fits design → build → test → deploy

Primarily Design (how you author code) and Build/Test (conventions to keep reproducibility)

It’s not a build system, but it prevents drift

Gotchas

.cursorrules is only as effective as the editor honoring it

Treat it as guardrails, not enforcement—enforcement belongs in CI

Layer 6 — Secrets & Runtime Config: GitHub Secrets / Codespaces Secrets / Railway Env Vars

Never in repo. Never in .env for public repos.

Store API keys in GitHub → Secrets (Codespaces secrets; Actions secrets; org-level if needed)

Store deploy-time secrets in Railway environment variables (or your deploy platform equivalent)

Consume as environment variables in code (os.getenv())

Operational rule

Secrets changed → restart codespace (usually)

Build recipe changed → rebuild container

Gotchas

.env in .gitignore is still on disk; fine for private/local, but you’ve correctly chosen higher assurance

Don’t print secrets; avoid logging full env

Layer 7 — Automation & Policy: .github/ (GitHub Actions + more)

You were right to call this out. This directory is often the center of cattle CI/CD.

What’s commonly here

.github/workflows/*.yml → GitHub Actions pipelines (build/test/deploy)

.github/dependabot.yml → dependency update policy

.github/CODEOWNERS → ownership rules (review enforcement)

Issue/PR templates, labels, etc. (process hygiene)

Design → Build → Test → Deploy mapping

Build: dependency install, build steps, artifact creation

Test: unit/integration tests, lint, type-check, formatting checks

Deploy: deploy jobs (optional; some teams deploy outside GitHub Actions)

Best practice (for your stack)

Use uv sync --locked in CI

Ensure CI’s Python version is pinned (match devcontainer)

If using Nix in CI, pin via flake.lock

Gotchas

CI must not “float”: avoid unpinned versions of Python/actions/tools

“Works in Codespaces, fails in CI” usually means missing lock usage or OS deps not declared

Layer 8 — Deployment Manifests: apps/research-auditor/railway.toml (Railway config)

You’re also right here: railway.toml is typically Railway’s service configuration for how to run/deploy that app.

What belongs here (when you use it)

Service definition for that app (start command, build command, paths, variables linkage, etc.)

Repo-to-service mapping patterns (varies by Railway setup)

Your observation (likely correct):
If you are not using Railway for build, railway.toml may be optional or minimally used—but it depends on how you deployed the service.

How to think about it

If you deploy to Railway and want reproducible deploy behavior, keep railway.toml as cattle

If you deploy some other way (or manually configured in Railway UI), railway.toml might be redundant—but that’s pet-like unless you intentionally accept it

Gotchas

“Configured in Railway UI only” = pet drift risk (harder to reproduce)

Prefer declaring deploy behavior in railway.toml if Railway is the target platform

Your “Cattle Rules” Checklist (printable)
Must-haves

✅ .devcontainer/ defines environment (GitHub builds it)

✅ flake.nix + flake.lock pin system tools (Nix provides them)

✅ pyproject.toml + uv.lock pin python deps (uv provides them)

✅ .github/workflows/*.yml defines build/test/deploy automation (CI/CD as cattle)

✅ .cursorrules defines editor guardrails (prevents accidental drift)

✅ Secrets live in GitHub/Railway secret stores, never in repo

✅ Deployment manifest (railway.toml) exists if Railway is your deploy target (avoid UI-only drift)

Allowed “pet” zones (small, controlled)

Caches: uv/pip cache, Nix store cache, node cache

Editor state: extensions cache, language server cache

Everything else should be declarative.

Golden Commands (muscle memory)
Environment identity
ls -la /workspaces/.codespaces >/dev/null && echo "codespaces context"
cd /workspaces/2026-software-lab
git branch --show-current

Nix
nix develop
# or if you have a specific flake output:
nix develop .#dev

Python with uv
uv sync --locked
uv run python -c "import os; print('OPENAI_API_KEY', 'SET' if os.getenv('OPENAI_API_KEY') else 'MISSING')"

CI confidence (what you want your Actions to effectively do)
uv sync --locked
uv run pytest

When things change (the canonical reactions)

Secrets changed (GitHub/Railway) → restart codespace / restart service (usually)

.devcontainer changed → rebuild container

flake.nix / flake.lock changed → nix develop again (or rebuild if container-level features changed)

pyproject.toml changed → uv lock then uv sync --locked

.github/workflows/*.yml changed → validate locally first, then let CI enforce

railway.toml changed → redeploy (or trigger Railway deploy), confirm env vars still correct

Gotchas to Avoid (the big ones)

Cursor “Reopen in Container” while in Codespaces
→ can create split-brain (two containers, different home/tooling).
In Codespaces, rebuild via Codespaces: Rebuild Container, not editor devcontainer attach.

Installing stuff “just this once” into $HOME
→ feels fast, becomes non-reproducible debt.

Unpinned deps
→ if it isn’t in a lockfile (uv.lock, flake.lock), it will drift.

CI drift

use pinned Python

use uv sync --locked

avoid floating action versions and OS deps

Deploy drift (Railway UI-only config)

if Railway is your deploy target, prefer railway.toml + env vars to keep deploy cattle

If you want it fool-proof: one “Bootstrap Contract”

A single command that always brings you to ready state, e.g.:

nix develop -c bash -lc "uv sync --locked && uv run python -m your_project.sanity_check"


Then your whole chain becomes: design → declare → rebuild → bootstrap → test → deploy.
