# Independent plan review — Factory v2

## A. Executive verdict

`Do not approve architecture yet`

The plan explores the stack unusually well and makes the git-bus choice explicit, but three execution contracts are not buildable together as written: protected `main` has no valid order-issuance path, a run record is both append-only and incrementally updated, and an offline Cursor hook is expected to enforce a cross-runtime concurrency cap. The git-derived lifecycle and governor identity remain legitimate Architecture Debates rather than reasons to default back to familiar tooling. Phasing is directionally ordered, but P1 should not begin until the contract contradictions are resolved.

## B. Findings table

| ID | Severity | Lens | Plan locus | Finding | Suggested resolution (for human) |
|----|----------|------|------------|---------|----------------------------------|
| P1 | Blocker | Data & contracts [arch] | `plan.md` Data & persistence; `contracts/cli.md` `claim`/`handoff`; `data-model.md` RunRecord | `factory claim` writes `run.yaml` with `claimed_at`, while handoff must later add `handoff_at`, duration, cost, and other final measurements. The bus invariant forbids modifying any existing message, so the declared run record cannot reach its own schema without violating append-only storage. | Choose an append-only run event sequence (claim event plus completion/measurement event), or explicitly remove run records from the immutable-message invariant and define controlled replacement/versioning. |
| P2 | Blocker | Boundaries / topology [arch] | `contracts/messages.md` order “on main”; `contracts/cli.md` `order new`; FR-005; topology branch protection | A worker may claim only after its order exists on protected `main`, but the plan defines no branch/PR that gets a newly scaffolded order there. Direct push conflicts with protected `main`; a separate issuance PR conflicts with “one work order → one branch → one PR”; putting the order on the worker PR means it was never issued before claim. | Lock an issuance topology: e.g. orders land through a dedicated governed queue PR not counted as the work PR, or an authenticated bot/App may append orders to protected `main`. Reconcile FR-005 and lifecycle evidence accordingly. |
| P3 | Blocker | Enforceability [arch] | `plan.md` Orchestration; `contracts/hooks.md` spawn guard; Technical Context hook target; mixed local/cloud runtime | The `subagentStart` hook must run offline in under 300 ms, yet authoritative active work is derived from origin branches and GitHub PRs. It also does not govern direct cloud-agent starts. Its CI twin can detect a violation only after spawning, so the architecture cannot satisfy “spawning is refused beyond 3” across the declared mixed runtimes. | Separate advisory local guard from authoritative admission. Name one launch broker/lease mechanism all runtimes must use, or narrow the product claim to claim/merge refusal and record the fidelity change. |
| P4 | Debate | Lifecycle & bus choice [arch] | `research.md` Jobs/Data store; `data-model.md` Lifecycle; `factory status` | Typed git messages are reviewable and avoid a second mutable status store, but branch existence is an incomplete durable lease: abandoned branches, closed-unmerged PRs, force-deleted refs, and concurrent claims have no cancellation/expiry/reconciliation contract. “Derive everything on read” therefore risks permanent phantom capacity and ambiguous ready state. | Choose between (A) retaining git with append-only release/abandon/reconcile events and atomic claim rules, or (B) using a tracker/workflow lease as the authoritative queue while keeping git messages as the audit log. |
| P5 | Debate | Spec lock fidelity / identity [product] | `plan.md` Governor identity; spec D4; P1 registry governor-only gates | Recorded-only identity is honestly disclosed, but P1 still names governor-only checks and override rejection as live while any agent can assert `actor: governor` under the shared account. That is a visible interim substitute for enforcement, not merely an implementation detail. | Choose whether P1 explicitly ships these checks as audit-only and marks the affected acceptance/effective coverage unmet, or lock GitHub App/signature identity before any governor-only gate is advertised as enforcing. |
| P6 | Debate | Gate architecture [arch] | `research.md` Red-first proof; `plan.md` risks; SC-002 | Overlaying head tests on base code is a strong observable proof, but counting any collection/import error as “red” lets malformed tests or missing setup satisfy red-first without demonstrating the intended behavior. The later head pass does not prove the base failure was semantically relevant. | Choose (A) require an assertion/test failure tied to collected node ids, with explicit exceptions for intentional new-module imports, or (B) accept collection-red as a weaker signal and name a second gate/reviewer that catches the gap. |
| P7 | Later | Phased delivery [arch] | P1 three parallel slices | P1’s direction is sound, but Slice B depends on the gate runner/registry in Slice C and all slices depend on P0 schemas and fixtures. “Disjoint paths” alone does not make their integration contracts independent, and the roughly twenty P1 gates plus board/metrics/GitHub adapter make the three-day target fragile. | In tasks, freeze executable interfaces and shared fixtures at P0, identify integration checkpoints, and keep the five-day maximum distinct from the three-day target. |
| P8 | Nit | Learning / SOTA fit [arch] | `research.md` all required block rows | Strength: every material block, including no-UI host, orchestration, bus, reviewers, secrets, and topology, names non-sibling managed/OSS alternatives and gives fit-based reasons. The plan meets the authoring-gate exploration bar rather than treating sibling reuse as research. | Preserve these decision rows; update only the rows whose decisions change during P1–P6 adjudication. |

## C. Adversarial positions

### 1. Position: kill the append-only YAML bus as the operational queue

Keep git messages as the immutable audit trail, but make GitHub Issues/Projects or a small lease service authoritative for claim, cancellation, and concurrency. The plan already depends on GitHub for branches, PRs, checks, identity, and required-check enforcement, so “git only” does not actually provide an offline control plane. A managed queue supplies atomic claims, notifications, abandonment, and queryable active state without deriving leases from stale refs. The YAML bus can still preserve intent, verdicts, and decisions in reviewable form.

**What would have to be true for the plan’s stance to be right anyway:** claims must be atomic enough at three workers, abandoned work must reconcile deterministically, and order issuance must work under protected `main` without adding an incoherent second PR.

### 2. Position: the architecture under-teaches managed execution

The research names Cursor SDK, hosted coding agents, Temporal, and Inngest, then leaves execution as humans/agents invoking a CLI plus editor hooks. That preserves today’s mixed workflow but does not mechanically guarantee entry through `factory claim`, isolation, cap enforcement, or real-time blocker routing. A thin managed launch broker—potentially Cursor SDK behind the same order contract—would teach the missing custody boundary while leaving the linear lifecycle intact. The current design risks spending more code on detecting bypasses after the fact than on making the supported path unavoidable.

**What would have to be true for the plan’s stance to be right anyway:** every actual local and cloud launch path must demonstrably pass through one enforceable claim boundary, and bypass telemetry must show the lightweight path is reliable.

## D. Independence / tasks readiness

No. A cold agent can generate tasks for schemas, most gates, adapters, and the board, and `research.md` does not leave the major stack forks chat-shaped. It cannot safely task the issuance path, run-record lifecycle, or cross-runtime admission control without inventing behavior that changes locked shalls. The human should adjudicate the bus/lifecycle, identity, and red-first forks after those blockers are made concrete; then the plan and contracts need in-place reconciliation before `/speckit-tasks`.

## E. Edit list (Architecture-first)

- **Architecture / Orchestration** — define the protected-main order issuance and claim sequence.
- **Data & persistence** — split run measurements into immutable events or exempt/version the run aggregate.
- **Topology & runtime custody** — name the authoritative admission point shared by local and cloud workers.
- **Lifecycle** — add abandonment, closed-unmerged, stale-ref, and claim-race semantics.
- **Governor identity** — state exactly which P1 checks are audit-only and which are enforced before D4.
- **Research / Jobs** — compare a managed launch broker, not only a future workflow engine.
- **Research / Red-first** — define qualifying base failures and intentional import exceptions.
- **Contracts / CLI and messages** — align command effects with the resolved issuance and run-event model.
- **Phased delivery / P0** — make the frozen cross-slice interfaces and integration fixture explicit.

## F. Questions for the human

1. Should order issuance use a separate governed queue PR, or may a bot append orders directly to protected `main`?
2. Is the worker cap required to prevent launch itself across local and cloud runtimes, or is authoritative claim/merge refusal sufficient?
3. Should git remain the authoritative work lease after adding abandon/reconcile events, or should a managed tracker own leases while git remains the audit log?
4. May P1 expose governor-only actions as visibly audit-only, or must distinct identity exist before those checks count as live?
5. Must red-first prove a collected test/assertion failure, or may collection/import failure count for this version?
