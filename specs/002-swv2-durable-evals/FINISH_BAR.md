# Finish-bar lock batch — 002-swv2-durable-evals (constitution §G.2)

## Meta

| Field | Value |
|-------|-------|
| Feature | `specs/002-swv2-durable-evals/` |
| Date | 2026-10-04 |
| `/speckit-analyze` run | 2026-10-04 over spec / plan / tasks (104 tasks). **1 critical** (D3 open, by design — see below), 2 high, 9 medium, 4 low. Coverage: FR-001..FR-022 plus FR-004a / FR-013a / FR-013b (25) and SC-001..SC-014 (14) each map to ≥ 1 task (100%). Remediated in place: test seams named fully (generate, revise, assessor) in research + quickstart + T022; per-env login grants now include `CREATE` on its own schemas (tables are created under it) and per-pool `search_path`; migrations stay schema-qualified via an `{{app_schema}}` token rendered per env; production migrations run inside the service (custody unchanged) with a staging-first check + governor approval; CI custody adds `TAVILY_API_KEY` + `LOGFIRE_TOKEN` (needed by nightly web cases and Logfire eval results); `lab_shared.db` → `lab_shared.db.pool` (existing package); Postgres tests moved to `tests/pg/` (Nix integration check has no database); stale sweep order / "nightly full ×3" / table count fixed; job-route 404 isolation and full `fail_reason` list added to the HTTP contract; latency measurement placed with the Evals nightly harness; role → agent mapping recorded; deferral words fixed across the feature dir. Raised to the orchestrator as product questions, not edited: model-change PRs run the full set, which may exceed the $2 per-PR cap (today it waits on the governor's spend gate); the nightly eval run has no stated spend cap; the bake-off candidate list and spend are approved at T094 |
| §G.2 reading | §G.2 step 2 puts **every** `who: human` + `status: open` Open Decision in the inventory, with no exception for a `before` point in a subsequent phase, and step 5 forbids implement/ops workers while any inventory row is unresolved. Step 3 allows only **lock** or **true-waive** to resolve a row; "open by design" is neither. So D3 makes **Implement unblocked = no** for the feature. The only constitutional path for work before D3 locks is the §G.2 narrow exception: "a packet whose Out-of-scope explicitly excludes all unfinished finish-bar rows". Every lane packet in tasks T012 carries that exclusion (no task sets the real ceiling or switches production to bake-off models before T097), so P0–P2 packets qualify **if the governor keeps D3 open** (option A below). The P3 packet tasks T097–T098 cannot run until D3 locks |
| Batch status | in_progress |

## Inventory

| id / source | Product question (governor altitude) | arch_impact (on lock) | Outcome |
|-------------|--------------------------------------|------------------------|---------|
| **D3** | What may one draft cost at most (≤ $3 hard limit already locked)? Designed to be set after the bake-off measures real costs | content-only (expected: Settings default; spend meter already in the architecture) | **open** — resolved by T097 `[OD:D3]` after the bake-off; governor question below |
| Plan P3 "Bake-off (Wave 3)" | Is the bake-off inside this feature's finish? | n/a | in finish bar — SC-011 and catalog rows `models.*` are `must`; sequenced in Wave 3 (tasks Phase 9), not parked |
| Spec Aspirational "measured prompt pass in Wave 3" | — | n/a | not finish bar (aspirational; spec Out of scope excludes prompt work beyond it) |
| Spec F7 / F8 (`Later` → plan) | Latency workload; nightly-regression owner and time bound | n/a | locked by plan review P8 (contracts/evals § Nightly; 2 working days) → tasks T075, T083–T086 |
| Plan risk "splitting `scored_loop` is a post-mortem candidate" | — | n/a | non-goal this version (plan § Major risks) — not finish bar |
| Research "recorded HTTP (`pytest-recording`) kept for a single nightly smoke" | — | n/a | not finish bar: no SC or catalog row depends on it, and the nightly real-provider tuning run (T083) is the live-provider check. No task emitted |
| Catalog `eval.blinded_review` / `quality.governor_agrees` at post-mortem | — | n/a | in finish bar at sprint close (T103–T104); timing is the shall itself, not a deferral |

Other governor touchpoints that are approvals, not open content: golden-set review (T080), calibration ratings (T088), bake-off candidate list + spend approval (T094), bake-off lock (T096), P0 account/vault steps (T018–T021).

## Governor question (one, plain language)

> **Smart Writer per-draft spending cap.** The $3 hard maximum is already locked. The real working cap was meant to wait until the model bake-off shows what drafts actually cost. Choose:
> **(A)** Keep it open as designed. All building work goes ahead except switching production to the new models, and you're asked for the number once the bake-off reports costs. *Stake: one more decision at the end of the sprint; until then, any draft may spend up to $3.*
> **(B)** Set the working cap to $3 now. Any post-bake-off tightening becomes a new decision. *Stake: nothing waits on you; the cap won't reflect measured costs unless you reopen it.*
>
> Agent recommendation: **A** (matches the original intent: the cap is set from evidence).

On **A**: record "governor keeps D3 open (date)" in Batch outcome; P0–P2 packets run under the narrow exception; **Implement unblocked** stays **no** for D3-dependent work (T097–T098) until T097 locks it, then a delta row flips it to **yes**.
On **B**: lock D3 = `3.00` USD (content-only), set Batch status done and **Implement unblocked = yes**; tasks T097 becomes a delta decision after the bake-off.

## Batch outcome

| Field | Value |
|-------|-------|
| All inventory rows locked or true-waived? | no (D3 open) |
| Next gate | governor answer above; no §G.1 expected (D3 is content-only) |
| **Implement unblocked** | **no** — §G.2 narrow exception available for packets whose Out-of-scope excludes D3 (all T012 packets except P3), once the governor answers A |

## Delta addendum (re-entry only)

| Date | New rows | Re-lock done? |
|------|----------|---------------|
| | | |
