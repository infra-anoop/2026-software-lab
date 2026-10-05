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

- **Decision:** **D4 locked (2026-10-03): option A.** Agents act as a GitHub App; the governor approves as themselves. App key names live in the secrets schema; tokens are 1-hour installation tokens. Before the App is live (Wave 1), the CLI uses `GITHUB_TOKEN` and governor-only actions are recorded with `actor: governor`, labelled **unverified** on the board, and audited at post-mortem.
- **Rationale:** Honest about what is enforceable; does not invent an identity scheme without the governor.
- **Options for D4** (concrete consequences in plan Architecture):
  - **A. Separate agent identity: a GitHub App** (managed, SOTA pattern for bots). Agents push and open PRs as the App; the governor's own account approves. CODEOWNERS plus required review then work, because the author is no longer the approver.
  - **B. Governor-signed decisions.** Governor-only messages carry a signature from a key agents cannot reach (hardware or passphrase-protected SSH signing on the governor's own machine); gates verify against `allowed_signers`. Codespaces auto-signing would have to stay off.
  - **C. Recorded-only** (status quo): the gate trusts `actor: governor`; post-mortem audits. Cheapest; not enforcement.

## Block: Topology & runtime custody

- **Decision (amended 2026-10-05 — spec D5, trusted-base CI; supersedes "one `factory-gates.yml` on `pull_request`"):** No servers. Runtimes: (1) the `factory` CLI in the Codespace (orchestrator, workers, hooks); (2) two GitHub Actions workflows. The **untrusted** `factory-pr-evidence.yml` runs on `pull_request` with `contents: read` only: the head's own factory tests, plus red-first execution that writes an evidence artifact. The **trusted** `factory-gates.yml` runs on `workflow_run` (so GitHub takes the workflow file from `main`). It checks out `main`, runs only `main`'s factory code over the head as git data and the artifact as untrusted data, and is the only job with `statuses: write`. Required checks are set by branch protection (ops HITL, T066; bootstrap sequencing D6). No browser, no BFF, no spend secret. Custody: `GITHUB_TOKEN` (Codespace for local, Actions-provided for CI); under D4-A, the App private key lives in Infisical and mints short-lived installation tokens for agents. Full rules: plan § CI topology and trust boundary.
- **Rationale:** Matches cattle: everything is declared in git (`factory.toml`, both workflows, `.cursor/hooks.json`, `CODEOWNERS`). `factory/*` statuses decide merges, so the code that writes them must not be code the PR controls (PR review PR-C1). `workflow_run` gives "judged by `main`'s gates; new gates take effect after merge" by construction.
- **Pattern source:** `.github/workflows/verify-source.yml` (PR pipeline shape). The split of an untrusted `pull_request` producer and a privileged `workflow_run` consumer is GitHub Security Lab's documented pattern for privileged follow-up work on PRs.
- **Alternatives considered:**
  - **One `pull_request` job holding `statuses: write`** (the superseded P1 design): simplest, but executes head code (`uv sync`, `factory gate run` from the head) with the write token; a PR can forge every `factory/*` status. Rejected by D5.
  - **`pull_request_target` with a base checkout, head fetched as data:** one workflow, runs base code with write permission. Rejected: one added `ref:` or `uv sync` of the head reopens the token to PR code, and D5 bans `pull_request_target` combined with head checkout or execution. `workflow_run` keeps the privileged half free of any PR checkout by design.
  - **Repository rulesets "require workflows to pass"** (managed; a workflow pinned to a ref in a trusted repo is forced onto every PR): enforces the trusted ref without `workflow_run`. Not adopted: it targets organization-level rulesets, and its availability on this personal-account repository is **unverified, so it is not claimed** (delta P* P13). It also does not remove the need to keep status writes away from head code.
  - **GitHub App webhook service** (non-sibling, hosted: a bot such as Probot receives PR events, runs trusted gate code on its own host and posts statuses as the App): the cleanest trust boundary, since PR code never shares a machine with the credential. But it is a deployable service with its own secret custody and uptime. **Deferred → P3** (plan § Phased delivery) as the cleaner migration option (delta P* P13); Actions `workflow_run` covers P1 once hardened with source pinning (P9) and artifact provenance plus cache isolation (P12).

---

## Other forks (feature-specific)

### Lint engine for architecture and drift patterns

- **Decision:** **Semgrep CE** rules (OSS, YAML rules in git, `--baseline-commit` gives changed-lines-only for free) for: test seams/key sniffing (I-A8), getenv outside config (I-A3), vendor imports outside adapters (I-A4), `Agent(` without `output_type` (I-A2), and generic identifiers via `metavariable-regex` (I-A7). **import-linter** contracts for layers (I-A1). **ruff** stays as the formatter/linter (`flake8-tidy-imports` banned-api duplicates the getenv rule cheaply). A custom Python check covers the lab_shared consumer declarations (I-A5).
- **Alternatives considered:** a hand-written AST visitor pack (no new tool, but every rule is code we must test, and changed-lines logic is reinvented); **ast-grep** (OSS, fast, good structural matching, weaker diff-baseline support); **CodeQL** (managed, powerful, heavy for a solo repo).

### Red-first proof (FR-012)

- **Decision:** A CI job. Collect test node ids on head; diff against base collection to get new and changed tests; check out base app code with head test files overlaid; run those tests. Each must **fail with a real test failure** (assertion or raised exception inside the test body, per collected node id). A collection or import error counts as red **only** when the missing name is a module or symbol the PR itself adds; any other base error is reported as "base broken", not red (locked 2026-10-03, review P6). Then run them on head, where they must pass. A PR with no new or changed tests passes this gate (other gates cover untested code). Implemented in `factory gate red-first`. **CI placement (D5, 2026-10-05):** the test execution runs in the read-only `factory-pr-evidence.yml` with `main`'s harness and writes an evidence bundle. The trusted `red-first-proof` gate judges from that bundle as data and fails closed when it is missing, malformed, bound to another SHA, or inconsistent with the diff's test files (contract: `contracts/gates.md` § CI topology and trust boundary). **Strength (D7, 2026-10-05):**
  - **Wave 1:** that result is self-reported, and its status says so. The independent T* reviewer's re-run is FR-012's proof of record.
  - **Wave 2:** a sealed trusted run (credential-free sandbox, separate user or container, read-only head tree, parent-recorded outcomes) replaces the bundle (T104).
  - **Rejected alternatives (delta P* P10):** calling the bundle "proof" (it is self-attestation), and dropping red-first from CI until the sandbox exists (loses the Wave 1 drift signal the seed suite relies on).
- **Alternatives considered:** **TDD-Guard** (OSS hook for Claude Code that blocks implementation edits without a failing test) as an in-session convenience. A Cursor `afterFileEdit` equivalent is not adopted this version (post-mortem candidate); CI stays authoritative. Commit-order heuristics (tests committed before code) are rejected as gameable.

### Mutation testing on changed lines (FR-019, P2 — Wave 2 Models lane)

- **Decision:** **mutmut 3** restricted to changed files, with results filtered to mutants on changed lines; threshold 70% (D2).
- **Alternatives considered:** **cosmic-ray** (OSS, more config, distributed); **Stryker-style diff mutation** does not exist for Python; **mutatest** (unmaintained).

### Intent traceability (FR-023)

- **Decision:** A custom `factory check intent` over `specs/*/intent.yaml` plus the gate registry and acceptance catalogs. Presence is a 100% invariant; effective coverage is computed from check status (exists and passing in the latest run) or `human` mappings.
- **Alternatives considered:** **Doorstop** (OSS requirements-traceability tool in git), **Sphinx-needs** (OSS), and the **OpenSpec/Kiro** requirement-to-task linkage. Doorstop is the closest fit, but it models requirements documents, not check status or effective coverage. Its item format is a reasonable future export.

### Editor hooks (FR-022)

- **Decision:** `.cursor/hooks.json` calls `.cursor/hooks/factory-hook.sh <name>`. The wrapper runs the project venv's lightweight `factory-hook` console script (`factory.hooks.entry:main`: no Typer app, no other slices' modules) and falls back to `uv run --project scripts/factory factory hook <name>` only when the venv is missing, because uv's own startup exceeds the 300 ms budget (amendment `wo-20261004-factory-slice-c.amend-01`). When neither the venv nor an ambient `uv` exists (a fresh worktree; this repository provides `uv` through Nix), the wrapper runs the same fallback inside the repository's Nix environment (`nix develop <repo root> -c uv run …`). If that bootstrap fails too, it prints the event's quiet fail-open JSON itself (PR review PR-C2, 2026-10-05). The hooks are `subagentStart` → `spawn-guard`, which is log-only: it allows every launch, and its advisory for an unclaimed or over-cap launch lands only in the Hooks output channel, because Cursor shows hook messages only on denial (governor 2026-10-04, `amend-02`). `beforeShellExecution` → `shell-guard` blocks direct writes to `main`, system-path writes, `pip install`, `gh workflow run` and force-push. `postToolUse` with an anchored `Write|Delete` matcher → `owned-path-warn`, an owned-path warning in `additional_context`. `stop` → `decision-in-chat` returns `followup_message`. Each hook id maps to a CI gate id in the registry; `factory check hooks` fails if any hook lacks a twin. Authoritative enforcement stays in `factory claim` and CI.
- **Alternatives considered:** **pre-commit** framework hooks (OSS, tool-agnostic, run at commit). Adopted for the cheap checks (schema validation, bus immutability) as a second local layer, since CI is the authority. **Claude Code / Codex hook systems** are not used now; the CI twin keeps any tool honest (I-G5).

### CLI framework

- **Decision:** Typer (on Click).
- **Alternatives considered:** argparse (stdlib, no dependency, verbose); Cyclopts (modern, smaller community).
