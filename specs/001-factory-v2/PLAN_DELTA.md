# Architecture delta reconcile — 001-factory-v2 (constitution §G.1)

Template: [`docs/agent-os/PLAN_DELTA_TEMPLATE.md`](../../docs/agent-os/PLAN_DELTA_TEMPLATE.md).

**Gate:** Do not spawn implement/ops workers that depend on these locks until this checklist is complete (and `/speckit-analyze` recorded). Status: **steps 1–3 complete for D5**. Step 4 (delta P*) is **warranted and not yet run**. Phase 6a tests and rework wait for its triage. **D6**, opened by this reconcile, blocks only applying branch protection (T101) and Slice C's merge (T103).

## Meta

| Field | Value |
|-------|-------|
| Feature | `specs/001-factory-v2/` |
| Date | 2026-10-05 (governor lock after the Slice C PR review, PR-C1); reconcile authored 2026-10-05 |
| OD locks in this batch | **D5** |
| New ODs opened | **D6** (`who: human`, `open`) |
| Delta P* review | **warranted → to spawn** (appends to [`PLAN_REVIEW.md`](./PLAN_REVIEW.md)). D5 reopens the CI trust topology: which runtime holds the status-write credential, which code it runs, a new `workflow_run` trigger and a cross-workflow untrusted artifact. Plan Architecture review must exercise it, including SOTA alternatives (§G.1 step 4: "reopens topology") |

## Classification

| id | arch_impact | One-line lock |
|----|-------------|----------------|
| D5 | architecture-affecting | In CI, `main`'s gate code judges every PR and the head is only data; PR-head code never runs with status-write permission (its own tests run in a separate read-only job); gate changes take effect after merge; Slice C's own PR bootstraps via FR-037 verdict + governor approval; no `pull_request_target` with head checkout or execution. Letter fidelity |
| D6 | (open) | When the required `factory/*` checks switch on relative to Slice C's bootstrap merge — see § D6 |

Why D5 is architecture-affecting: one CI workflow becomes two runtimes with different trust (an untrusted `pull_request` producer and a trusted `workflow_run` consumer); the status-write credential moves to a job that never checks out head code; a new untrusted artifact (the evidence bundle) crosses the boundary; `red-first-proof` splits into an executing half and a judging half; the registry that selects gates changes from "whatever the checkout has" to "`main`'s"; and bootstrap sequencing now interacts with branch protection (D6).

Letter interpretations recorded (for the delta P* review to check):

- "The PR head is treated only as data: its diff, files, bus messages and tests" — the trusted job reads head tests as files and never runs them. Test **execution** happens only in the read-only workflow. Its results reach the trusted gate as an untrusted bundle the trusted code validates (plan § CI topology, Execution-derived evidence).
- "The PR's own tests still run in a separate, read-only job" — `factory-tests` in `factory-pr-evidence.yml`, with `contents: read` and no secrets. Its job check (`Factory tests`) is a GitHub check, not a `factory/*` status.
- "Judged by main's current gates" — `main`'s registry selects the gates, and `main`'s package supplies every entrypoint. The head registry is validated as data and never selects code (T-C2's head-as-input rule stands).

## Artifacts amended

- [x] `plan.md` Architecture — amendment note under Approval; Summary (3); UI clients (board in the trusted run's summary); Boundaries (two workflow rows); Topology & runtime custody (runtimes, secret custody, cattle manifests); **new § CI topology and trust boundary**; Data & persistence (ephemeral evidence artifact); Major risks (+3: execution-derived evidence, statuses posted outside CI, bootstrap window; verify-source line); Phased delivery P1 and P1b exit criteria; Constitution Check (D5/D6); Project Structure
- [x] `data-model.md` — **no change**: no persisted entity or field changes. The evidence bundle is an ephemeral CI artifact specified in `contracts/gates.md`; its Pydantic model is a CP0 frozen-interface amendment inside T097
- [x] `contracts/` — `gates.md`: header line (commit statuses from the trusted workflow) + **new § CI topology and trust boundary** (workflows table, head as data, which gates run, gate-change effect, overrides, execution-derived gates, evidence bundle, PR identity, interpolation, bootstrap, banned patterns) + Override resolution note. `cli.md`: § CI mode (`gate run --expect-head --evidence`, `gate evidence`). `hooks.md`: Invocation bootstrap (PR-C2, content-only process fix carried with the delta)
- [x] `research.md` overturned Decisions — § Topology & runtime custody (decision superseded; alternatives: single write job, `pull_request_target` + base checkout, rulesets-required workflows, hosted App bot); § Red-first CI placement; § Editor hooks fallback (PR-C2)
- [x] `tasks.md` appended (no renumber): header Open Decisions; CP2 proof; T059 superseded note; T066 amendment (→ T101); **Phase 6a T094–T103**; Dependencies; Slice C owned paths
- [x] `spec.md` — **D5** row (locked, architecture-affecting, letter); **D6** row (open); **FR-022a**; FR-037 bootstrap sentence
- [x] `acceptance.md` — row `ci.trusted_base` (`planned` until T094/T097); change-log row
- [x] `FINISH_BAR.md` — Delta addendum (D5, D6), delta inventory, delta outcome
- [x] `PR_REVIEW_SLICE_C.md` — § Triage (PR review)
- [x] `bus/orders/wo-20261004-factory-slice-c/amendment-03.yaml` — owned paths widened to the files above

## D6 — question for the governor (plain language)

**Context.** Slice C is the PR that adds the gates, so it is the one PR nothing trusted can check. You decided it merges on the independent bootstrap review plus your approval. The branch-protection setup is to happen before C merges, with no bypass for anyone, and will list every factory check by name. If those checks are required before C merges, nothing can mark them passed for C, and C cannot merge.

| Option | What happens | Services / secrets | Your steps | Cost | Trade-off |
|--------|--------------|--------------------|------------|------|-----------|
| **A. Switch the factory checks on right after C merges** (recommended) | Before C merges, everything else in branch protection is set (PR required, no bypass, code-owner review, the existing checks and the read-only test job), and the snapshot already lists every factory check by name. C merges on the bootstrap review plus your approving review. Then you add the factory checks as required | None | One extra settings change right after C merges (~5 min) | Free | For those few minutes, factory checks are not required; the orchestrator merges nothing else in that window, and the retro replays the gates over C |
| **B. Switch them on before C merges; you mark C's factory checks passed yourself** | Protection never has a gap. After reading the bootstrap review, you post a "passed" result for each of C's 25 factory checks under your own login (a short script run outside the Codespace) | None new; uses your own credential | Run the script once (~10 min) | Free | Hand-posted passes look exactly like forged ones until the agents' own GitHub identity exists. They also rule out pinning the factory checks to GitHub Actions as their only source before C merges (a hardening the delta review may recommend) |

## Remaining gaps → tasks

| Gap | Task id |
|-----|---------|
| Bootstrap merge sequence against required `factory/*` checks with bypass off (D6) | T101 `[OD:D6]` → before T066 settings are applied; T103 |
| Red-first outcomes come from a job that executes head tests; test code in the diff could tamper with the harness and forge its own outcomes (no credential reachable) | Delta P* to probe; T094 fixes the fail-closed bundle rules; plan § Major risks |
| `factory/*` contexts can still be posted outside CI by the Codespace token or the agent App (T065 asks for statuses write); required checks name contexts, not posters | Delta P* to recommend whether T101 pins the `factory/*` checks to GitHub Actions as source (would then be a governor settings choice at T101) |
| Rulesets "require workflows" availability on this personal-account repository unverified (research alternative) | Delta P* |
| Evidence-bundle model, its size-limit setting and any `GateContext` field are CP0 frozen interfaces (`api.py`, `config/`) | T097 by order amendment |
| Red-first split edits Slice B's `gates/drift/red_first.py`; validators need a repo-root argument (`scripts/validate_secrets_schema.py` is Slice A's, `scripts/validate_deploy_env.py` lab-owned) | T097, by amendment after A and B are merged into C |
| `factory-status-test` pass/fail oracle is not specified beyond "repo (unit)", I-M4 | T102 test-first + T* review |
| Accepted T-C1 workflow assertions are superseded by the new topology | T094 replaces them; T096 T* triage records it |
| CI latency: evidence run then trusted run, sequential, vs plan "full gate run < 5 min" | Measured at T103 (CP2) |
| Fork PRs get no `pull_requests` in the `workflow_run` payload, so no `factory/*` statuses | Accepted: solo same-repository workflow; required checks fail closed |

## `/speckit-analyze` result

| Field | Value |
|-------|-------|
| Date run | 2026-10-05, over spec / plan / tasks (104 tasks, 28 done) + Open Decisions + FINISH_BAR + contracts (gates, cli, hooks) + acceptance + research. `.specify/extensions.yml` absent (no hooks) |
| Outcome | **gaps** — 1 critical by rule (D6 open `who: human`, with its `[OD:D6]` task T101; blocks only the C merge), 2 high disclosed and routed to the delta P*, 4 medium filed as tasks, 4 low fixed or recorded. Coverage: FR-001..FR-037 + FR-005a / FR-011a / FR-022a (40) and SC-001..SC-013 (13) each map to ≥ 1 task (100%; FR-022a → T094, T097, T103; others unchanged from the 2026-10-03 run). Deferral-word scan of every added `specs/**` line: clean after 4 fixes (F1) |
| Notes | Findings below. No constitution MUST violated: tests precede implementation (T094–T096 before T097–T098), no implement before the §G.1 gate, no rule/process path touched |

### Findings

| ID | Category | Severity | Location(s) | Summary | Disposition |
|----|----------|----------|-------------|---------|-------------|
| G1 | Open Decisions | CRITICAL (rule) | spec D6; tasks T101, T103 | New open `who: human` row: bootstrap sequence vs required `factory/*` checks with bypass off | **Question** — § D6; `[OD:D6]` task T101; FINISH_BAR delta addendum. Does not block the delta P* review or Phase 6a tests/rework |
| H1 | Security attribute | HIGH | plan § CI topology (Execution-derived evidence); contracts/gates.md § Evidence bundle | Execution-derived evidence (red-first) is forgeable by test code in the diff | **Disclosed** — plan § Major risks; fail-closed binding rules in contract; delta P* to probe |
| H2 | Security attribute | HIGH | plan § Major risks; tasks T065, T101 | Required checks name contexts, not posters; Codespace/App tokens can post `factory/*` | **Disclosed** — routed to delta P* (pin source at T101?) |
| M1 | Underspecification | MEDIUM | tasks T097; `api.py`, `config/` (CP0 frozen) | Bundle model, size limit and plumbing touch frozen interfaces | **Filed** — T097 by amendment |
| M2 | Underspecification | MEDIUM | tasks T097; Slice A/B paths | Cross-slice edits (red-first split, validator root argument) | **Filed** — T097 after A/B merge, by amendment |
| M3 | Underspecification | MEDIUM | contracts/gates.md `factory-status-test`; tasks T102 | Gate oracle unspecified (pre-existing; exposed by PR-C3) | **Filed** — T102 test-first + T* |
| M4 | Coverage / schedule | MEDIUM | spec SC-013; tasks CP2 | Rework + D6 + delta P* push CP2; the Wave 1 time-box is measured from run events | **Recorded** — no artifact change; the board and scorecard will show it |
| F1 | Deferral words | LOW | contracts/gates.md (2 lines), research.md (webhook alternative), tasks.md T103 | Added lines carried `later`/`Deferred` without an OD id or pointer | **Fixed** — D5 id / `→ P3` / reworded |
| L1 | Ambiguity | LOW | contracts/gates.md § Evidence bundle | Size limit value not set | **Recorded** — agent-policy content set in typed config in T097 |
| L2 | Inconsistency | LOW | tasks T004 (done) | Historical "placeholder `factory-gates` job on `pull_request`" text | **Left** — completed task history; superseded by T097 (T059 note) |
| L3 | Inconsistency | LOW | plan Technical Context Performance | "full gate run < 5 min" now spans two sequential workflows | **Recorded** — measured at T103 |

### Deferral-word scan

Every `later` / `optional` / `deferred` / `TBD` / `future` / `stretch` on added `specs/001-factory-v2/**` lines is inside a code span, carries a D# id or a `→` pointer (checked with `git diff -U0 | rg` on 2026-10-05; 0 offenders after F1).

## Forbidden (honored)

- No new feature directory solely for OD fills
- No stock `/speckit-plan` setup replacing `plan.md` (amended in place)
- Human chat line: "Architecture delta reconcile done" (D5); D6 posed as a plain A/B choice
