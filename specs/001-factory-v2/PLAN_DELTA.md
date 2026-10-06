# Architecture delta reconcile — 001-factory-v2 (constitution §G.1)

Template: [`docs/agent-os/PLAN_DELTA_TEMPLATE.md`](../../docs/agent-os/PLAN_DELTA_TEMPLATE.md).

**Gate:** Do not spawn implement/ops workers that depend on these locks until this checklist is complete (and `/speckit-analyze` recorded). Status: **round 1 (D5) and round 2 (D6–D8, P* triage) steps 1–3 complete.** Step 4: the delta P* review ran (not approved; P9 and P12 blockers, P10 and P11 debates) and was triaged in § Round 2. The narrow P* confirmation (verdict-06) confirmed P9, P12, D6 and D7 Wave 1, and raised one Blocker, P19, on T104's Wave 2 shape. **The orchestrator agent-closed P19 for Wave 1 purposes** (§ Round 3); a Wave 2 P* confirmation of T104's design is required before T104 is implemented. **Phase 6a Wave 1 red tests are unblocked.** No Open Decision is open.

## Meta

| Field | Value |
|-------|-------|
| Feature | `specs/001-factory-v2/` |
| Date | 2026-10-05 (governor lock after the Slice C PR review, PR-C1); reconcile authored 2026-10-05 |
| OD locks in this batch | **D5** (round 1); **D6**, **D7**, **D8** (round 2, after the delta P*) |
| New ODs opened | D6 opened in round 1 and locked in round 2; D7, D8 created locked in round 2 |
| Delta P* review | **run** — [`PLAN_REVIEW.md`](./PLAN_REVIEW.md) § Delta review — D5 (verdict-05: do not approve yet). Warranted because D5 reopens the CI trust topology: which runtime holds the status-write credential, which code it runs, a new `workflow_run` trigger and a cross-workflow untrusted artifact. Triaged in § Triage (delta P*). **Narrow P* confirmation** of round 2 next (P9, P12 contract text; D6 sequence; D7 Wave 1 wording and Wave 2 sandbox shape vs D5) |

## Classification

| id | arch_impact | One-line lock |
|----|-------------|----------------|
| D5 | architecture-affecting | In CI, `main`'s gate code judges every PR and the head is only data; PR-head code never runs with status-write permission (its own tests run in a separate read-only job); gate changes take effect after merge; Slice C's own PR bootstraps via FR-037 verdict + governor approval; no `pull_request_target` with head checkout or execution. Letter fidelity |
| D6 | architecture-affecting | **Probe, then pin**: C merges on bootstrap review + governor approval; merges freeze; a non-merging probe PR obtains trusted `factory/*` statuses; branch protection requires every `factory/*` context with GitHub Actions pinned as expected source; the live rule is verified; then merges reopen. Letter (closes P11) |
| D7 | architecture-affecting | Red-first strength: Wave 1 CI red-first is **self-reported**, said plainly in the status description and contracts; FR-012's "proven" is amended for Wave 1 so that the T* reviewer's re-run is the proof of record. Wave 2: a **sealed trusted run** (credential-free sandbox, `persist-credentials: false`, separate user or container, read-only head tree, parent-owned outcome recording). Letter (closes P10) |
| D8 | architecture-affecting | The agents' GitHub App gets **no `statuses: write`**; only CI posts `factory/*` statuses. Letter (closes P* question 3) |

Why D6–D8 are architecture-affecting:
- **D6** changes the activation sequence of the trust root and the P1 exit (CP2).
- **D7** amends a requirement's proof standard and adds a sandboxed execution stage to the trusted runtime in Wave 2.
- **D8** changes an identity's permission scope (D4 custody).

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

## D6 — question for the governor (plain language) — **resolved 2026-10-05**

Locked as option A, refined by the delta P* (P11): "right after C merges" becomes merge freeze → non-merging probe PR → required and source-pinned → live rule verified → merges reopen. Option B was rejected because hand-posted passes destroy source provenance. The original question is kept below as history.

**Context.** Slice C is the PR that adds the gates, so it is the one PR nothing trusted can check. You decided it merges on the independent bootstrap review plus your approval. The branch-protection setup is to happen before C merges, with no bypass for anyone, and will list every factory check by name. If those checks are required before C merges, nothing can mark them passed for C, and C cannot merge.

| Option | What happens | Services / secrets | Your steps | Cost | Trade-off |
|--------|--------------|--------------------|------------|------|-----------|
| **A. Switch the factory checks on right after C merges** (recommended) | Before C merges, everything else in branch protection is set (PR required, no bypass, code-owner review, the existing checks and the read-only test job), and the snapshot already lists every factory check by name. C merges on the bootstrap review plus your approving review. Then you add the factory checks as required | None | One extra settings change right after C merges (~5 min) | Free | For those few minutes, factory checks are not required; the orchestrator merges nothing else in that window, and the retro replays the gates over C |
| **B. Switch them on before C merges; you mark C's factory checks passed yourself** | Protection never has a gap. After reading the bootstrap review, you post a "passed" result for each of C's 25 factory checks under your own login (a short script run outside the Codespace) | None new; uses your own credential | Run the script once (~10 min) | Free | Hand-posted passes look exactly like forged ones until the agents' own GitHub identity exists. They also rule out pinning the factory checks to GitHub Actions as their only source before C merges (a hardening the delta review may recommend) |

## Remaining gaps → tasks

| Gap | Task id |
|-----|---------|
| ~~Bootstrap merge sequence against required `factory/*` checks with bypass off (D6)~~ | **Closed round 2** — D6 locked (probe, then pin); T101 (snapshot + live rule without `factory/*`), T103 (freeze → probe → pin → verify → reopen) |
| ~~Red-first outcomes come from a job that executes head tests; test code in the diff could forge its own outcomes~~ | **Closed round 2** — D7: Wave 1 self-reported, stated in the status, T* re-run is the proof of record (T094); Wave 2 sealed trusted run (T104) |
| ~~`factory/*` contexts can still be posted outside CI by the Codespace token or the agent App; required checks name contexts, not posters~~ | **Closed round 2** — P9 source pinning (snapshot records the app id, the gate asserts it: T094/T097; live: T103) + D8 (T065) |
| ~~Rulesets "require workflows" availability on this personal-account repository unverified~~ | **Closed round 2** — P13: research marks it unverified and not claimed |
| Evidence-bundle model, its size-limit setting and any `GateContext` field are CP0 frozen interfaces (`api.py`, `config/`) | T097 by order amendment |
| Red-first split edits Slice B's `gates/drift/red_first.py`; validators need a repo-root argument (`scripts/validate_secrets_schema.py` is Slice A's, `scripts/validate_deploy_env.py` lab-owned) | T097, by amendment after A and B are merged into C |
| `factory-status-test` pass/fail oracle is not specified beyond "repo (unit)", I-M4 | T102 test-first + T* review |
| Accepted T-C1 workflow assertions are superseded by the new topology | T094 replaces them; T096 T* triage records it |
| CI latency: evidence run then trusted run, sequential, vs plan "full gate run < 5 min" | Measured at T103 (CP2) |
| Fork PRs get no `pull_requests` in the `workflow_run` payload, so no `factory/*` statuses | Accepted: solo same-repository workflow; required checks fail closed |

## `/speckit-analyze` result (round 1, superseded by § Round 2)

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

## Round 2 — delta P* triage (2026-10-05)

Input: [`PLAN_REVIEW.md`](./PLAN_REVIEW.md) § Delta review — D5 (verdict-05, "do not approve yet"); triage recorded in `PLAN_REVIEW.md` § Triage (delta P*).

### Locks and agent decisions

| Item | Kind | Decision | Closes |
|------|------|----------|--------|
| D6 | governor lock, architecture-affecting | Probe, then pin (sequence in the spec row, plan § CI topology Bootstrap, contracts/gates.md § Bootstrap, T101/T103, CP2) | P11, round-1 G1 |
| D7 | governor lock, architecture-affecting | Red-first self-reported in Wave 1 (status prefix `self-reported:`, T* re-run is the proof of record, FR-012 amended); sealed trusted run in Wave 2 (T104, catalog `ci.redfirst_sealed`, check scheduling P2 row) | P10, round-1 H1 |
| D8 | governor lock, architecture-affecting | Agents' App: no `statuses: write` (T065, plan § Governor identity); only CI posts `factory/*` | P* question 3 |
| P9 | agent (Blocker adopted as suggested) | Every required `factory/*` context pinned to the GitHub Actions integration; snapshot records the app id per context; `branch-protection-require-pr` asserts it; no `statuses: write` for non-CI identities the factory controls. Catalog `ci.status_source_pinned` | P9, round-1 H2 |
| P12 | agent (Blocker adopted as suggested) | Evidence downloaded only from the exact triggering `workflow_run.id`, same repository, exact name; zero or several matches rejected; fresh runner; no cache restore or save in the trusted workflow. Contract-tested in T094, built in T097 | P12 |
| P13 | strength kept | Research: ruleset-required workflows unverified and not claimed for this personal repository; hosted App kept as the cleaner P3 alternative | P13 |
| P14 | strength kept | D5 letter bans preserved verbatim; provenance, cache and source checks added beside them | P14 |

### Artifacts amended (round 2)

- [x] `spec.md` — D6 row locked; D7, D8 rows (locked, architecture-affecting, letter); FR-012 Wave 1 amendment; FR-022a (only CI posts, source pinned); FR-037 D6 sequence; Check scheduling P2 row (+ sealed red-first run, D7)
- [x] `plan.md` — Approval round-2 note; Secret custody (D8, P9); CI topology table (status source, `self-reported:`); rules: Execution-derived evidence (D7 Wave 1 / Wave 2), Artifact provenance and clean privileged environment (P12), Status source (P9, D8), Bootstrap (D6 five steps), Banned (+ caches, artifact selection); Governor identity (App has no `statuses: write`); Major risks (red-first self-reported; sealed run vs D5; statuses outside CI closed; bootstrap freeze); Phased delivery P1 exit (D6 sequence, P12 tests) and P2 (sealed run); Constitution Check
- [x] `data-model.md` — **no change** (the snapshot's per-context app id is a field of the ops snapshot file, specified in `contracts/gates.md`; no bus entity changes)
- [x] `contracts/gates.md` — heading; trusted workflow row (fresh runner, no cache, posts as GitHub Actions, `self-reported:`); new § Red-first strength (D7), § Artifact provenance (P12), § Privileged environment (P12), § Status source (P9, D8); § Bootstrap (D6 steps); § Banned (+ cache, artifact); P1 registry `branch-protection-require-pr` scope (app id). `contracts/cli.md` § CI mode (`--evidence` exactly one bundle; `self-reported:`). `contracts/hooks.md` unchanged
- [x] `research.md` — Red-first CI placement (D7 strength, rejected alternatives); Topology alternatives (rulesets unverified and not claimed; hosted App kept as the P3 migration option)
- [x] `tasks.md` — header Open Decisions (D5–D8, none open); CP2 row; Phase 6a gate (narrow P* confirmation); T094 (+ provenance, cache, `self-reported:`, source pinning); T097 (+ same); T101 (live rule without `factory/*`; snapshot with pinned target); T103 (five-step D6 order); checkpoint; T065 (no `statuses: write`); T066 note; Dependencies; **T104** appended in Phase 13 (`[OD:D7]`, sealed run, test first)
- [x] `acceptance.md` — rows `ci.status_source_pinned`, `ci.redfirst_sealed`; change-log row
- [x] `FINISH_BAR.md` — Delta addendum round 2; inventory D6–D8; outcome (no open rows; next gate narrow P*)
- [x] `PLAN_REVIEW.md` — § Triage (delta P*) appended; reviewer text untouched
- [x] `bus/orders/wo-20261004-factory-slice-c/amendment-04.yaml` — owned paths + `PLAN_REVIEW.md` and the orchestrator's delta-review packet

### Remaining gaps (round 2) → tasks

| Gap | Task id |
|-----|---------|
| Wave 2 sealed run puts head execution on the runner that holds the status token; D5's "no head code with status-write permission" holds only if the sandbox truly cannot reach it | T104 tests (no token, no `ACTIONS_*`, no runner dirs, separate user or container); narrow P* to confirm the shape is compatible with D5 |
| Source pinning assumes GitHub attributes `GITHUB_TOKEN` commit statuses to the GitHub Actions integration as their source | T103 step 4 verifies it live on the probe PR. If GitHub does not attribute them, the trusted job must post check runs instead (`checks: write`), which needs a delta amendment, and the freeze holds meanwhile |
| The D6 merge freeze is procedural (orchestrator holds merges); nothing mechanical blocks a merge between C's merge and verification | T103 records start and end; post-mortem audits merge timestamps in the window |
| The agents' App keeps `checks: write` (T065); it could create check runs named `factory/*` | Neutralized by P9 pinning (another source cannot satisfy the rule); asserted by `ci.status_source_pinned` |
| Round-1 gaps still open: CP0 frozen interfaces (bundle model, size limit), cross-slice edits (red-first split, validator root argument), `factory-status-test` oracle, superseded T-C1 assertions, CI latency, fork PRs | Unchanged: T097, T097, T102, T094/T096, T103, accepted |

### `/speckit-analyze` result (round 2)

| Field | Value |
|-------|-------|
| Date run | 2026-10-05, over spec / plan / tasks (105 tasks, 28 done) + Open Decisions (D1–D8) + FINISH_BAR + contracts (gates, cli, hooks) + acceptance + research. `.specify/extensions.yml` absent (no hooks) |
| Outcome | **pass with recorded gaps**: 0 critical (no open `who: human` row; D6 closed), 1 high disclosed and routed to the narrow P*, 4 medium (2 new, filed above; 2 carried from round 1), lows recorded. Coverage: FR-001..FR-037 + FR-005a / FR-011a / FR-022a (40) and SC-001..SC-013 (13) each map to ≥ 1 task (100%). FR-012 → T040/T042 + T094 (Wave 1) + T104 (Wave 2); FR-022a → T094, T097, T101, T103, T065. Deferral-word scan of every added `specs/**` line: 0 offenders (Wave 2 lines carry D7) |
| Notes | No constitution MUST violated: tests precede implementation (T094–T096 before T097–T098; T104 test first); no implement before §G.1 step 4 confirmation; no rule/process path touched; every architecture-affecting lock reconciled in place |

| ID | Category | Severity | Location(s) | Summary | Disposition |
|----|----------|----------|-------------|---------|-------------|
| H3 | Lock consistency / security | HIGH | spec D5 vs D7 (Wave 2); plan § Major risks; T104 | The Wave 2 sealed run executes head code inside the status-writing job; consistent with D5 only if no credential is reachable from the sandbox | **Disclosed** — D7 letter kept; T104 must prove it by test; narrow P* to confirm |
| M5 | Ambiguity | MEDIUM | contracts/gates.md § Status source; T103 | Whether commit statuses (not check runs) carry the GitHub Actions source for pinning | **Filed** — verified live at T103 step 4; fallback is a delta amendment |
| M6 | Underspecification | MEDIUM | T103 | The merge freeze is procedural | **Recorded** — T103 + post-mortem audit |
| M1–M4 | carried | MEDIUM | round 1 | as round 1 (M4 schedule pressure grows with round 2) | Unchanged |
| L4 | Inconsistency | LOW | tasks T065 | The App keeps `checks: write`, so same-named check runs are possible | **Recorded** — neutralized by P9 pinning |
| L5 | Consistency | LOW | acceptance `seed.not_red_first` | The seed stays "PR blocked"; in Wave 1 that rests on self-reported outcomes | **Recorded** — gate-level seed unaffected; D7 states the strength |

## Round 3 — narrow P* confirmation triage (2026-10-05)

Input: [`PLAN_REVIEW.md`](./PLAN_REVIEW.md) § Confirmation (round 2) (verdict-06, "do not approve architecture yet"); triage in `PLAN_REVIEW.md` § Triage (confirmation).

### Decision (orchestrator, arch): P19 adopted verbatim

P19 resolution, adopted verbatim into T104, `plan.md` and here: "move the sealed runner and runner-owned outcome capture to a separate job with no status-write permission, then have the privileged publisher validate that exact job/run result without executing head code." And: "Keep the sealed parent-owned result, but run the child in a separate job with no status-write permission; let the status-writing job consume only the parent-recorded result as hostile data."

- **Consistent with D7's intent.** The run stays sealed, credential-free, with parent-owned outcomes.
- **Stricter than the same-job shape, so it does not dilute a lock (§I).** Every property D7 names is kept. D7's row says "the trusted job runs head tests"; the governor's text is left as written, and a dated note in the row points to this placement, which also keeps D5's letter ("PR-head code never runs with status-write permission").
- **Wave 2 only.** T104 is Wave 2 (P2), and no Wave 1 task depends on it. **A Wave 2 P* confirmation of T104's design is required before T104 is implemented** (recorded in T104). That makes this the agent-closure of P19 for Wave 1 purposes.

### Artifacts amended (round 3)

- [x] `tasks.md` — T104: P19 shape (verbatim), Wave 2 P* gate before implement, two new red tests (sealed job has no status-write permission; the publisher runs no head code and fails closed on a missing, foreign or mismatched result)
- [x] `plan.md` — § CI topology, Execution-derived evidence (Wave 2 bullet); Major risks (sealed run closed in shape by P19)
- [x] `contracts/gates.md` — § Red-first strength, Wave 2 bullet (separate job; publisher data-only)
- [x] `spec.md` — D7 row: dated placement note only (governor text unchanged)
- [x] `acceptance.md` — `ci.redfirst_sealed` threshold adds "job with no status-write permission" and "the status-writing job runs no head code"
- [x] `PLAN_REVIEW.md` — § Triage (confirmation) appended; reviewer text untouched
- [x] `bus/orders/wo-20261004-factory-slice-c/amendment-05.yaml` — owned paths for the Phase 6a red tests and bootstrap messages

### Closures

| Finding | Disposition |
|---------|-------------|
| P15 (P9), P16 (P12), P17 (D6), P18 (D7 Wave 1) | Confirmed; nothing to change |
| P19 | Agent-closed for Wave 1 (above); Wave 2 P* confirmation gates T104 |
| P20 | Accepted as recorded (round-2 residuals M5, L4; fork PRs) |
| Round-2 H3 (sealed run inside the status-writing job vs D5) | **Closed** by P19: the sealed run leaves that job |

### `/speckit-analyze` (round 3)

**Not re-run:** coverage is unchanged. No FR, SC or task was added or removed; T104 keeps its FR-012 / SC-002 mapping and its catalog row. The round-2 result stands, minus H3 (closed above): 0 critical, 0 high, medium M1–M6 as filed.

## Round 4 — governor decisions on `main` protection (2026-10-06)

Verbatim text: `tasks.md` T101 and `bus/orders/wo-20261004-factory-slice-c/amendment-07.yaml`.

| Item | Kind | Decision |
|------|------|----------|
| Mechanism | governor lock, architecture-affecting (ops surface) | A repository ruleset, not classic branch protection. The Codespace token can read rulesets (200) but not classic protection (403), so T103's read-back goes through `GET /repos/{o}/{r}/rulesets/{id}`. Snapshot and gate move to the ruleset shape: target `main`, empty bypass list, rules `pull_request`, `required_status_checks` (every `{context, integration_id}` pinned to GitHub Actions, P9), `non_fast_forward`, `deletion` |
| Code-owner review | governor-approved fidelity deviation (§I) | Deferred until the factory's App authors PRs (T065); T101 turns on PR required, required checks, no bypass. `.github/CODEOWNERS` added now. The gate requires code-owner review exactly when `identity.mode = "verified"` (agent's choice of form: T065 state, no new config) |

- **Not a re-plan.** The D5/D6/D8 topology, P9 pinning and the probe-then-pin order are unchanged; only the GitHub settings surface and the snapshot schema change.
- **Accepted tests amended by governor decision.** The `branch-protection-require-pr` tests in `scripts/factory/tests/unit/gates/test_registry_checks.py` keep their intents in the new shape. Tests added: the new rules (`non_fast_forward`, `deletion`, active ruleset on `refs/heads/main`), code-owner review on and off by identity mode, and the committed snapshot.
- **Downstream.** T066a (lifecycle reads the branch's required checks) should read them from `GET /repos/{o}/{r}/rules/branches/main`, not the classic endpoint (403). Slice A owns T066a; recorded here, not changed.
- **`/speckit-analyze`:** not re-run. No FR, SC or task was added or removed; FR-031's governor approval is delayed (fidelity deviation above), not dropped.

## Forbidden (honored)

- No new feature directory solely for OD fills
- No stock `/speckit-plan` setup replacing `plan.md` (amended in place)
- Human chat line: "Architecture delta reconcile done" (D5); D6 posed as a plain A/B choice; round 2: "Architecture delta reconcile done" (D6–D8)
