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

## Delta review — D5 (2026-10-05)

### A. Executive verdict

`Do not approve architecture yet`

The two-workflow split is the right realization of D5: `workflow_run` lets the privileged half run the default branch's code, and the plan keeps PR-head execution away from `statuses: write`. The approval gap is now narrower but still material: required `factory/*` contexts are not pinned to their expected GitHub Actions source, and the artifact contract does not bind download provenance or prohibit an untrusted workflow's cache from entering the privileged run. Red-first also remains a real Architecture Debate because schema/SHA validation proves which PR supplied a claim, not that head test code did not forge the claimed outcomes. Phasing is otherwise ordered, but CP2 and D6 need the source-pinned activation sequence.

### B. Findings table

| ID | Severity | Lens | Plan locus | Finding | Suggested resolution (for human) |
|----|----------|------|------------|---------|----------------------------------|
| P9 | Blocker | Topology & trust boundary [arch] | `plan.md` Major risks; `tasks.md` T101; `contracts/gates.md` PR identity and status target | Branch protection requires context names but does not require the GitHub Actions App as their expected source, so the Codespace token or future agent App can satisfy the same `factory/*` checks outside the trusted workflow; that defeats D5's claim that `main`'s judge controls merge authority. | Require every `factory/*` context with the GitHub Actions integration as expected source, record the integration/app id in the branch-protection snapshot, and remove `statuses: write` from non-CI identities unless another documented use needs it. |
| P10 | Debate | Data & contracts / proof integrity [product] | `plan.md` Execution-derived evidence and Major risks; `contracts/gates.md` Evidence bundle; FR-012 | Binding an untrusted JSON bundle to a head SHA and test-file list prevents mix-ups, not fabrication: head test code can tamper with an in-process harness or emit invented red→green outcomes, so the current artifact is self-attestation rather than FR-012's “proven” result. | Choose (A) a runner-owned isolation boundary where head code cannot write the harness or bundle and the parent records process outcomes, or (B) explicitly weaken red-first to reviewable advisory evidence and amend the “proof” requirement; I recommend A. |
| P11 | Debate | Bootstrap / phased delivery [arch] | `PLAN_DELTA.md` D6; `tasks.md` T101/T103; P1 exit | D6 option A is safer, but source pinning normally becomes operational only after the expected app has produced a check/status; “right after C merges” therefore needs a no-other-merges bootstrap probe before the checks become required, while option B's hand-posted passes destroy source provenance. | Lock A as: merge C on bootstrap review, open a non-merging probe to obtain trusted statuses, pin and require every factory context to GitHub Actions, verify the live rule, then permit any other merge. |
| P12 | Blocker | Workflow boundary [arch] | `contracts/gates.md` workflows/evidence; `tasks.md` T094/T097 | The privileged consumer is not required to download `factory-evidence` from the exact triggering `workflow_run.id`, and no rule forbids restoring caches writable by the untrusted workflow. GitHub's `workflow_run` pattern is safe only when artifacts are treated as hostile and privileged execution cannot ingest attacker-poisoned state. | Contract-test exact run-id/repository/name provenance, reject zero or multiple matching artifacts, use a fresh privileged environment, and prohibit restore of any cache the PR workflow can populate. |
| P13 | Nit | Learning / SOTA fit [arch] | `research.md` Topology & runtime custody | Strength: the delta compares the single privileged PR job, `pull_request_target`, ruleset-required workflows, and a hosted App; `workflow_run` plus a hostile-data artifact is the mainstream GitHub pattern for a privileged follow-up, while a hosted App is cleaner but disproportionate for P1 and required-workflow availability is not established for this personal repository. | Keep the Actions split for P1 after P9/P12 hardening; retain the hosted App service as the P3 migration option and do not claim ruleset-required workflows are available until verified. |
| P14 | Nit | Spec lock fidelity [arch] | `plan.md` CI topology; `contracts/gates.md` Head as data; T094 | Strength: the amendment preserves all three letter locks—no PR-head execution with status-write, gate changes take effect only after merge, and no `pull_request_target` plus head checkout/execute—and gives contract tests concrete banned forms. | Preserve these bans verbatim while adding source and artifact-provenance checks. |

### C. Adversarial positions

#### 1. Position: remove execution-derived artifacts from the trusted verdict path

Do not let a privileged status publisher convert a PR-authored outcome document into `red-first-proof=success`. Run the head's ordinary tests as a read-only required job, but keep red-first human-reviewed until there is a runner-owned containment boundary: immutable base harness, head test tree mounted read-only, isolated child/container, no shared writable cache, and bundle serialization performed only by the parent. This narrows the first release and avoids calling self-attestation proof.

**What would have to be true for the plan's stance to be right anyway:** bundle creation must be outside head-code control, exact artifact provenance must be established, and deliberate environment-sensitive tests must remain visible enough for review to catch.

#### 2. Position: use a hosted Check Run App instead of privileged Actions

A GitHub App webhook worker can fetch PR objects as data, run trusted gate code on an independently deployed revision, and publish app-owned checks without giving the repository's untrusted workflow any path toward the credential. It also gives branch protection an unambiguous source and avoids `workflow_run` artifact/cache hazards. That is the cleaner managed trust boundary.

**What would have to be true for the plan's stance to be right anyway:** Actions source pinning must be enforced, artifact provenance/cache isolation must be contract-tested, and the operating cost of a hosted service must exceed the residual risk at this solo-repository scale.

### D. Independence / tasks readiness

Not yet. A cold agent can implement the two-workflow topology and D5's head-as-data rules, and `research.md` does not leave the main stack fork chat-shaped. It would still have to invent how the artifact is selected, whether caches cross the boundary, how red-first outcomes are isolated from head code, and how source pinning fits the first post-C run. After P9/P12 are made contractual and P10/D6 are locked, T094–T103 are taskable without chat archaeology.

### E. Edit list (Architecture-first)

- **Topology & runtime custody** — require GitHub Actions as the expected source for every `factory/*` required context.
- **Contracts / gate status target** — include expected integration/app id in the branch-protection snapshot and drift assertion.
- **Contracts / evidence bundle** — bind download to the exact triggering workflow run and require exactly one named artifact.
- **Contracts / privileged environment** — ban restoration of caches writable by the untrusted workflow.
- **Architecture / execution-derived evidence** — lock the containment boundary or explicitly weaken the red-first claim.
- **Tasks T094/T097** — test exact artifact provenance, cache isolation, and source pinning before implementation.
- **Tasks T101/T103 / CP2** — encode merge C → trusted probe → source-pin/require → verify → reopen merges.
- **Research** — mark ruleset-required-workflow availability unverified for this personal repository; preserve hosted App as the cleaner P3 alternative.

### F. Questions for the human

1. For red-first, do you require runner-owned isolation (recommended), or accept that its result is reviewable self-attestation rather than proof?
2. Do you lock D6 to the post-C probe and source-pinned activation sequence in P11?
3. May the future agent App lose `statuses: write` unless a separate approved use is demonstrated?

## Triage (delta P*)

Recorded 2026-10-05 by the Slice C worker on the orchestrator's instruction, against verdict-05 ("do not approve yet"). Product- and architecture-Debates and the human questions were adjudicated by the governor; the Blockers were adopted by the orchestrator as the reviewer suggested. Reconciled in place per constitution §G.1, with the record in [`PLAN_DELTA.md`](./PLAN_DELTA.md) § Round 2.

| ID | Disposition | Adjudicator | Resolution | Where |
|----|-------------|-------------|------------|-------|
| P9 | accept (Blocker) | orchestrator — adopted as suggested | Every required `factory/*` context names the GitHub Actions integration as its expected source. The branch-protection snapshot records the integration/app id per context, and `branch-protection-require-pr` asserts it. Non-CI identities the factory controls get no `statuses: write`; the Codespace user token can still post, but cannot satisfy a pinned rule | spec FR-022a; plan § CI topology (Status source), Secret custody; `contracts/gates.md` § Status source, P1 registry row; T094, T097, T101, T103; catalog `ci.status_source_pinned` |
| P10 | resolved — **governor lock D7** | governor 2026-10-05 | **Wave 1:** CI red-first is self-reported evidence; every `red-first-proof` status description starts `self-reported:`, and the contracts say so. FR-012's "proven" is amended for Wave 1: the independent T* reviewer's re-run is the proof of record. **Wave 2:** a sealed trusted run (no credentials, `persist-credentials: false`, separate user or container, read-only head tree, parent-owned outcome recording) | spec D7, FR-012, Check scheduling P2; plan § CI topology (Execution-derived evidence), Major risks, P2 exit; `contracts/gates.md` § Red-first strength; `research.md` § Red-first; T094, T104; catalog `ci.redfirst_sealed` |
| P11 | resolved — **governor lock D6** | governor 2026-10-05 | Probe, then pin, as the reviewer framed it: C merges on its bootstrap review plus governor approval; merges freeze; a non-merging probe PR obtains trusted `factory/*` statuses; branch protection then requires every `factory/*` context with GitHub Actions pinned; the live rule is verified; only then do other merges reopen | spec D6, FR-037; plan § CI topology (Bootstrap), P1 exit; `contracts/gates.md` § Bootstrap; T101, T103, CP2 |
| P12 | accept (Blocker) | orchestrator — adopted as suggested | The trusted job downloads `factory-evidence` only from the exact triggering `workflow_run.id`, from this repository (run and head repository both checked), by exact name, into a fresh directory; zero or multiple matches are rejected. It runs on a fresh runner and never restores or saves a cache (`setup-uv` `enable-cache: false`, no `actions/cache`, no `setup-python` cache) | plan § CI topology (Artifact provenance), Banned; `contracts/gates.md` § Artifact provenance, § Privileged environment, § Banned; `contracts/cli.md` § CI mode; T094, T097 |
| P13 | noted — strength kept | orchestrator | Research marks ruleset-required workflows unverified and not claimed for this personal repository; the hosted App stays the cleaner P3 migration option | `research.md` § Topology & runtime custody |
| P14 | noted — strength kept | orchestrator | D5's letter bans are preserved verbatim; provenance, cache and source checks sit beside them | `contracts/gates.md` § Banned; T094 |
| Q1 | answered by D7 | governor | Wave 1 accepts reviewable self-attestation, labelled as such; Wave 2 builds runner-owned isolation | as P10 |
| Q2 | answered by D6 | governor | Yes, the post-C probe and source-pinned activation sequence | as P11 |
| Q3 | answered by **D8** | governor 2026-10-05 | Yes: the agents' App gets no `statuses: write`; only CI posts `factory/*` statuses | spec D8; plan § Governor identity; T065 |

**Disclosed for the narrow confirmation:** D7's Wave 2 sealed run executes head tests inside the status-writing job. It is consistent with D5 only if no credential is reachable from the sandbox, which T104 must prove by test (PLAN_DELTA § Round 2, H3). Pinning assumes GitHub attributes `GITHUB_TOKEN` commit statuses to the GitHub Actions integration; T103 step 4 verifies this live (M5).

**Next:** narrow P* confirmation of this round (P9 and P12 contract text, the D6 sequence, and the D7 wording and Wave 2 shape against D5). Then red tests T094–T095 and the T* review (T096).
