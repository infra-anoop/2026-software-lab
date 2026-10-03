# Research — 001-factory-v2

Shape: [`docs/agent-os/research-template.md`](../../docs/agent-os/research-template.md). Gates: [`PLAN_AUTHORING_GATES.md`](../../docs/agent-os/PLAN_AUTHORING_GATES.md), [`STACK_POSTURE.md`](../../docs/agent-os/STACK_POSTURE.md).

The factory is developer tooling: a Python CLI + CI gates + editor hooks over git and GitHub. It has no browser UI and no protected HTTP API, so UI-host and BFF rows are answered as "not applicable, because…" rather than left blank.

Environment facts that constrain choices (verified 2026-10-03): the `gh` CLI is not installed; `GITHUB_TOKEN` in the Codespace reaches the REST API (200 on `/pulls`); **agents and the governor commit and call the API as the same GitHub account** (`infra_anoop`); no `CODEOWNERS`; no branch protection; Cursor hooks support `subagentStart` (can deny), `beforeShellExecution`, `afterFileEdit`, `preToolUse`, `stop`.

---

## Block: UI client (the board)

- **Decision:** `factory status` CLI printing a markdown board (in flight / blocked / waiting on governor / overrides), plus the same markdown written to the GitHub Actions job summary of the gates workflow on every PR. Nothing is committed (SC-008).
- **Rationale:** I-X5 (not a dashboard product) and I-M4 (one board). Markdown renders in the terminal, chat, and GitHub. Deriving on read means no stored state to drift.
- **Pattern source:** none (sprint-01 had no board).
- **Alternatives considered:**
  - **GitHub Projects (v2) board** (managed): native kanban and the governor already lives in GitHub. Rejected for P1 because it is a second store whose state must be synced (drift risk, bookkeeping) and its field updates are mutable. **Deferred to P3** as a read-only mirror if the governor wants a web view.
  - **Textual TUI** (OSS): richer interaction, but adds a dependency for no failable outcome.
  - **Backstage / internal developer portal** (OSS/managed): explicitly an anti-goal (I-X1 enterprise ceremony).

## Block: UI host / deploy

- **Decision:** Not applicable. There is no hosted UI: the board runs locally and in CI job summaries.
- **Rationale:** No browser surface, so no host or secret-custody question.
- **Pattern source:** —
- **Alternatives considered:** Vercel/Netlify static board page — **Deferred to P3**, together with the Projects mirror; nothing in sprint 02 depends on it.

## Block: API / application service (factory core)

- **Decision:** One Python 3.12 package `factory` in its own uv project at `scripts/factory/` (own `pyproject.toml` + `uv.lock`), exposing a Typer CLI (`factory ...`) and a library API that hooks and CI call. Pydantic v2 models are the single source for message schemas; JSON Schema is generated from them for non-Python consumers. Repo specifics (bus dir, app roots, rule paths, worker cap, autonomy horizon, reviewer families) come from `factory.toml` at the repo root (FR-036; portability proof itself is P3).
- **Rationale:** Schema-first (I-A2) and typed config (I-A3) apply to the factory itself. A standalone uv project keeps its locks separate from the PEP 723 ops scripts and makes later extraction into its own repo mechanical.
- **Pattern source:** `scripts/*.py` PEP 723 style (rejected for the factory: too many shared modules for single-file scripts).
- **Alternatives considered:**
  - **`modules/lab_factory`** (shared library under the lab rule): wrong layer, since lab_shared is runtime code for apps and the factory is repo tooling.
  - **Separate repo / published package** (OSS distribution): the real portability end-state, but **deferred to P3** with the fixture-repo test (D1 waived).
  - **Off-the-shelf agent workflow kits**: **OpenSpec** (spec deltas + archive), **Kiro** (spec → tasks inside the IDE), **BMAD-method** (role-agent workflow), **Spec Kit extensions** (`.specify/extensions.yml` hooks). These bring authoring flow, but none implements derived lifecycle, override accounting, red-first proof, or intent traceability. Spec Kit stays the base (charter lock). The overlays become code here, and Spec Kit `extensions.yml` hooks call `factory` so the base stays swappable.

## Block: Jobs / orchestration (work lifecycle + agent execution)

- **Decision (P1 lock — linear derived state machine, no workflow engine):** lifecycle `issued → claimed → in_review → accepted | rejected → merged`, with `blocked_on_governor` as an overlay. It is computed on read from: branch `wo/<order-id>` whose first commit is the order (issued); claim event on that branch (claimed); open PR from that branch (in_review); latest verdict message in the PR (accepted/rejected); PR merged (merged); release event or closed-unmerged PR (released); order references an open `who: human` decision, or an unanswered decision request exists (blocked_on_governor). Full rules incl. stale and claim atomicity: [`data-model.md`](./data-model.md) § Lifecycle (revised after review P2/P4). Agent execution stays **mixed** (charter lock): Cursor in-session background subagents (Task) and Cursor cloud agents for long runs, all entering through `factory claim <order>`, which enforces the cap (3), owned-path disjointness, and open-decision refusal.
  - **Migrate trigger:** move to a durable workflow engine only if (a) runs need automatic retries/timeouts across hours, (b) more than one repo shares one queue, or (c) claims race in practice (two claims for one order observed).
- **Rationale:** State is already in git and GitHub; a second engine would be a second source of truth (FR-003). Linear is enough for one governor and ≤3 workers.
- **Pattern source:** sprint-01 `notes/packets/` + `SPAWN_WORKER.md` (replaced; packets stay as history).
- **Alternatives considered:**
  - **GitHub Copilot coding agent / Cursor Background Agents via GitHub Issues** (managed): assign issue → agent opens PR. Strong for "walk away", but the order would live in an issue (mutable, outside git) and the agent identity issue (below) still applies. **Considered as an execution backend** behind `factory claim` later; not P1.
  - **Cursor SDK programmatic runner** (managed): spawn agents from code with an order payload, so routing becomes fully mechanical. Not adopted this version (no spec requirement depends on it); post-mortem candidate as an execution backend behind `factory claim`, since the bus contract is the same.
  - **Temporal / Inngest** (OSS / managed durable workflows): the SOTA for long-running orchestration, but overkill at this scale. The migrate trigger above names when it would become justified.
  - **Beads** (OSS git-native issue tracker for agents: JSONL in git, dependency-aware `ready` queue): closest prior art. Rejected for P1 because it stores mutable status records (tool-maintained, but still a status store that must agree with PR reality) and adds a daemon/cache. Its dependency-aware "ready" query is borrowed as a board section.

## Block: Data store (the bus)

- **Decision:** Plain typed YAML message files in git under `bus/`, **append-only** (CI rejects modification or deletion of existing bus files), validated against the Pydantic schemas. Layout: `bus/orders/<order-id>/` holds the order (first commit of `wo/<order-id>`), amendments, run events (`claim`, `release`, `run-complete`), handoff, verdicts and overrides, all on the order's branch, so they merge with the work. `bus/decisions/`, `bus/corrections/` and `bus/postmortems/` travel in schema-gated *bus PRs*. See [`contracts/messages.md`](./contracts/messages.md). **No message has a status field** (schema forbids it).
- **Rationale:** Git is already the bus (AGENTS.md). PR-atomic messages mean a handoff and its code merge together. Diffs are reviewable, it works offline, and it is portable. Immutability makes SC-008 (no bookkeeping commits) true by construction.
- **Pattern source:** `notes/packets/` (mutable markdown with free-text Status, which is exactly what this replaces).
- **Alternatives considered:**
  - **GitHub Issues + labels + comments** (managed): native notifications and UI; rejected because state lives outside git, labels are mutable status, and it is not atomic with the PR.
  - **Beads** (see Jobs): mutable status records.
  - **Linear** (managed SaaS tracker with a good API and agent integrations): best-in-class UX, but adds a vendor, a secret, and a sync. Rejected as the bus; possible P3 mirror.
  - **SQLite / Postgres event store** (OSS): real append-only semantics and queries, but a store outside git needs sync, and the bus would stop being reviewable in PRs.

## Block: Search / retrieval / LLM (reviewers, judges)

- **Decision:** Independent reviewers are spawned from git artifacts only (FR-011a) with a **GPT-family** model (D3) through the Cursor subagent model selector. Each verdict records `reviewer_model`, `reviewer_family`, and `inputs[]` (paths and SHAs). The reviewer rubric is the versioned pattern catalog `factory/rubrics/patterns.yaml` (P2). Bugbot runs as an additional, non-authoritative PR reviewer (ops HITL).
- **Rationale:** Cross-family review is the cheapest guard against shared blind spots. Artifact-only inputs make isolation checkable.
- **Pattern source:** `SPAWN_REVIEWER.md`.
- **Alternatives considered:**
  - **CodeRabbit / Greptile** (managed AI PR reviewers): always-on, with no spawn step. They cannot be given an intent-id rubric plus artifact-only isolation as cleanly, and they add vendors. Bugbot covers the always-on slot.
  - **OpenAI Codex `/review` or a Claude Code headless review in CI** (managed, CI-driven): would make review a CI job rather than a spawn. Not adopted this version (needs a provider key in CI, a spend → governor-only category); post-mortem candidate behind the same verdict schema.

## Block: Secrets / identity (preview-gate equivalent)

- **Decision:** No new vault secrets for P1. The CLI uses `GITHUB_TOKEN` from the environment (Codespace or Actions). **Governor identity is an open architecture decision (spec D4)** because, today, agents and the governor are indistinguishable to git and GitHub. Without a distinct identity, "only the governor may override" (FR-020) and "governor approval for rule changes" (FR-031) cannot be enforced, only recorded. Until D4 locks, governor-only actions are recorded with `actor: governor` and audited at post-mortem. The board labels them **unverified**.
- **Rationale:** Honest about what is enforceable; does not invent an identity scheme without the governor.
- **Options for D4** (concrete consequences in plan Architecture):
  - **A. Separate agent identity: a GitHub App** (managed, SOTA pattern for bots). Agents push and open PRs as the App; the governor's own account approves. CODEOWNERS plus required review then work, because the author is no longer the approver.
  - **B. Governor-signed decisions.** Governor-only messages carry a signature from a key agents cannot reach (hardware or passphrase-protected SSH signing on the governor's own machine); gates verify against `allowed_signers`. Codespaces auto-signing would have to stay off.
  - **C. Recorded-only** (status quo): the gate trusts `actor: governor`; post-mortem audits. Cheapest; not enforcement.

## Block: Topology & runtime custody

- **Decision:** No servers. Runtimes: (1) the `factory` CLI in the Codespace (orchestrator, workers, hooks); (2) GitHub Actions workflow `factory-gates.yml` on `pull_request`, with required checks set by branch protection (ops HITL). No browser, no BFF, no spend secret. Custody: `GITHUB_TOKEN` (Codespace for local, Actions-provided for CI); under D4-A, the App private key lives in Infisical and mints short-lived installation tokens for agents.
- **Rationale:** Matches cattle: everything is declared in git (`factory.toml`, the workflow, `.cursor/hooks.json`, `CODEOWNERS`).
- **Pattern source:** `.github/workflows/verify-source.yml` (gates join the PR pipeline the same way).
- **Alternatives considered:** **GitHub App webhook service** (a hosted bot reacting to PR events, e.g. Probot on a managed host): richer real-time behavior, but a deployable service to run. **Deferred to P3**; Actions covers P1.

---

## Other forks (feature-specific)

### Lint engine for architecture and drift patterns

- **Decision:** **Semgrep CE** rules (OSS, YAML rules in git, `--baseline-commit` gives changed-lines-only for free) for: test seams/key sniffing (I-A8), getenv outside config (I-A3), vendor imports outside adapters (I-A4), `Agent(` without `output_type` (I-A2), and generic identifiers via `metavariable-regex` (I-A7). **import-linter** contracts for layers (I-A1). **ruff** stays as the formatter/linter (`flake8-tidy-imports` banned-api duplicates the getenv rule cheaply). A custom Python check covers the lab_shared consumer declarations (I-A5).
- **Alternatives considered:** a hand-written AST visitor pack (no new tool, but every rule is code we must test, and changed-lines logic is reinvented); **ast-grep** (OSS, fast, good structural matching, weaker diff-baseline support); **CodeQL** (managed, powerful, heavy for a solo repo).

### Red-first proof (FR-012)

- **Decision:** A CI job. Collect test node ids on head; diff against base collection to get new and changed tests; check out base app code with head test files overlaid; run those tests, which must fail (collection or import errors count as red); then run them on head, which must pass. A PR with no new or changed tests passes this gate (other gates cover untested code). Implemented in `factory gate red-first`.
- **Alternatives considered:** **TDD-Guard** (OSS hook for Claude Code that blocks implementation edits without a failing test) as an in-session convenience. A Cursor `afterFileEdit` equivalent is not adopted this version (post-mortem candidate); CI stays authoritative. Commit-order heuristics (tests committed before code) are rejected as gameable.

### Mutation testing on changed lines (FR-019, P2 — Wave 2 Models lane)

- **Decision:** **mutmut 3** restricted to changed files, with results filtered to mutants on changed lines; threshold 70% (D2).
- **Alternatives considered:** **cosmic-ray** (OSS, more config, distributed); **Stryker-style diff mutation** does not exist for Python; **mutatest** (unmaintained).

### Intent traceability (FR-023)

- **Decision:** A custom `factory check intent` over `specs/*/intent.yaml` plus the gate registry and acceptance catalogs. Presence is a 100% invariant; effective coverage is computed from check status (exists and passing in the latest run) or `human` mappings.
- **Alternatives considered:** **Doorstop** (OSS requirements-traceability tool in git), **Sphinx-needs** (OSS), and the **OpenSpec/Kiro** requirement-to-task linkage. Doorstop is the closest fit, but it models requirements documents, not check status or effective coverage. Its item format is a reasonable future export.

### Editor hooks (FR-022)

- **Decision:** `.cursor/hooks.json` calls `factory hook <name>`: `subagentStart` (refuses spawn without a claimed order or beyond the cap), `beforeShellExecution` (blocks system-path writes, `pip install`, `gh workflow run`, force-push), and `afterFileEdit` (owned-path warning). Each hook id maps to a CI gate id in the registry; `factory check hooks` fails if any hook lacks a twin.
- **Alternatives considered:** **pre-commit** framework hooks (OSS, tool-agnostic, run at commit). Adopted for the cheap checks (schema validation, bus immutability) as a second local layer, since CI is the authority. **Claude Code / Codex hook systems** are not used now; the CI twin keeps any tool honest (I-G5).

### CLI framework

- **Decision:** Typer (on Click).
- **Alternatives considered:** argparse (stdlib, no dependency, verbose); Cyclopts (modern, smaller community).
