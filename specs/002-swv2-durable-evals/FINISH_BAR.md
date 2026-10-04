# Finish-bar lock batch — 002-swv2-durable-evals (constitution §G.2)

## Meta

| Field | Value |
|-------|-------|
| Feature | `specs/002-swv2-durable-evals/` |
| Date | 2026-10-04 |
| `/speckit-analyze` run | 2026-10-04 over spec / plan / tasks (104 tasks). **1 critical** (D3 open, by design — see below), 2 high, 9 medium, 4 low. Coverage: FR-001..FR-022 plus FR-004a / FR-013a / FR-013b (25) and SC-001..SC-014 (14) each map to ≥ 1 task (100%). Remediated in place: test seams named fully (generate, revise, assessor) in research + quickstart + T022; per-env login grants now include `CREATE` on its own schemas (tables are created under it) and per-pool `search_path`; migrations stay schema-qualified via an `{{app_schema}}` token rendered per env; production migrations run inside the service (custody unchanged) with a staging-first check + governor approval; CI custody adds `TAVILY_API_KEY` + `LOGFIRE_TOKEN` (needed by nightly web cases and Logfire eval results); `lab_shared.db` → `lab_shared.db.pool` (existing package); Postgres tests moved to `tests/pg/` (Nix integration check has no database); stale sweep order / "nightly full ×3" / table count fixed; job-route 404 isolation and full `fail_reason` list added to the HTTP contract; latency measurement placed with the Evals nightly harness; role → agent mapping recorded; deferral words fixed across the feature dir. Raised to the orchestrator as product questions, not edited: model-change PRs run the full set, which may exceed the $2 per-PR cap (today it waits on the governor's spend gate); the nightly eval run has no stated spend cap; the bake-off candidate list and spend are approved at T094 |
| §G.2 reading | §G.2 step 2 puts **every** `who: human` + `status: open` Open Decision in the inventory, with no exception for a `before` point in a subsequent phase, and step 5 forbids implement/ops workers while any inventory row is unresolved. Step 3 allows only **lock** or **true-waive** to resolve a row; "open by design" is neither. So D3 makes **Implement unblocked = no** for the feature. The only constitutional path for work before D3 locks is the §G.2 narrow exception: "a packet whose Out-of-scope explicitly excludes all unfinished finish-bar rows". Every lane packet in tasks T012 carries that exclusion (no task sets the real ceiling or switches production to bake-off models before T097), so P0–P2 packets qualify **if the governor keeps D3 open** (option A below). The P3 packet tasks T097–T098 cannot run until D3 locks |
| Batch status | done (D3 intentionally open; D6/D7 locked). **Delta 2026-10-03 open** — D4 re-lock reconciled; D8, D9, D10 await the governor (§ Delta addendum) |

## Inventory

| id / source | Product question (governor altitude) | arch_impact (on lock) | Outcome |
|-------------|--------------------------------------|------------------------|---------|
| **D3** | What may one draft cost at most (≤ $3 hard limit already locked)? Designed to be set after the bake-off measures real costs | content-only (expected: Settings default; spend meter already in the architecture) | **open** — resolved by T097 `[OD:D3]` after the bake-off; governor question below |
| **D6** | Budget for a model-change PR's full eval run | content-only | **locked** 2026-10-03 — $10, then governor approval |
| **D7** | Nightly eval spend cap | content-only | **locked** 2026-10-03 — $5; skip + board flag when over |
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
| Governor answer | **A** (2026-10-03): D3 stays open until the bake-off reports costs |
| **Implement unblocked** | **no** for D3-dependent work (T097–T098). P0–P2 packets run under the §G.2 narrow exception — each packet's Out-of-scope excludes D3. **Superseded in part by the delta below (2026-10-03)** |

## Delta addendum (re-entry only)

| Date | New rows | Re-lock done? |
|------|----------|---------------|
| 2026-10-03 | **D4 re-lock** (OpenAI judges, Anthropic writes — `architecture-affecting`; §G.1 reconcile + analyze done → [`PLAN_DELTA.md`](./PLAN_DELTA.md)). New open `who: human` rows **D8** (interim Anthropic writer model), **D9** (which other roles stay off OpenAI), **D10** (interim OpenAI judge + support models) — tasks T105 / T106 / T107 | **no** — D8, D9, D10 await the governor (questions below) |

### Delta 2026-10-03 — inventory

| id / source | Product question (governor altitude) | arch_impact (on lock) | Outcome |
|-------------|--------------------------------------|------------------------|---------|
| **D4** | Which family judges? | architecture-affecting | **re-locked** 2026-10-03 — OpenAI judges + checks support; Anthropic writes; §G.1 done (PLAN_DELTA) |
| **D8** | Which Anthropic model writes drafts until the bake-off? | content-only expected (Settings default + price row) | **open** → T105 before T030 |
| **D9** | Must the assessor (and infer / extraction) also stay off the judge's family? | A/B content-only; C architecture-affecting (OpenAI key leaves the runtime) | **open** → T106 before T030 |
| **D10** | Which OpenAI models judge and check citations until the bake-off? | content-only expected (eval Settings default + price rows) | **open** → T107 before T082 |

### Delta 2026-10-03 — governor questions (plain language)

Cost estimates below are rough, from today's prompt sizes: about 10k input and 2k output tokens per writer turn, 3 inner writer↔assessor turns typical and 8 at most, other roles on today's `gpt-4o` (≈ $0.08 per draft typical, ≈ $0.17 at most). List prices as known at authoring (Anthropic $/M tokens in/out: Haiku 4.5 1/5, Sonnet 4.5 3/15, Opus 4.5 5/25; OpenAI: `gpt-4o` 2.5/10, `gpt-5` 1.25/10, `gpt-5-mini` 0.25/2, `gpt-4.1` 2/8, `gpt-4.1-mini` 0.4/1.6); T105/T107 re-verify ids and prices before posing. Today's per-draft cost with `gpt-4o` writing: ≈ $0.22 typical, ≈ $0.53 at most. Per-PR figures are drafting only (judging adds ≈ $0.25–0.40 per paired run); reservation figures assume a 4k-token writer output cap.

> **1. Which Anthropic model writes drafts until the bake-off picks one?** (D8) The judge is now OpenAI, so drafts must come from Anthropic before the quality baseline is recorded. Production drafts switch to this model when the models work ships — before the eval gate exists, so that one switch is not measured; the eval baseline is then recorded on it. It also writes for any role you move off OpenAI in question 2.
> **(A) Claude Haiku 4.5** (`anthropic:claude-haiku-4-5`) — ≈ $0.14 per draft typical, ≈ $0.33 at most (about 0.65× today). A per-PR paired check over all four scenario types (8 drafts) ≈ $1.1, inside the ~$1.50 sizing. *Stake: cheapest and fastest; grant prose may read thinner than today's until the bake-off.*
> **(B) Claude Sonnet 4.5** (`anthropic:claude-sonnet-4-5`) — ≈ $0.26 typical, ≈ $0.65 at most (about 1.2× today). Per-PR paired check over all four types ≈ $2.1. *Stake: quality at or above today's; the per-PR check is at the $2 per-PR cap, so if the golden-set dry run cannot fit every scenario type in ~$1.50 you get one more budget question.*
> **(C) Claude Opus 4.5** (`anthropic:claude-opus-4-5`) — ≈ $0.38 typical, ≈ $0.97 at most (about 1.8× today). Per-PR paired check ≈ $3.0. *Stake: strongest writer; over the per-PR cap unless the check covers fewer scenario types.*
>
> All three stay far under the $3 per-draft hard limit, including the meter's worst-case pre-call reservation (≈ $0.19 per Sonnet call, ≈ $0.32 per Opus 4.5 call). Older Opus pricing ($15/$75) was not offered: with the reservation it would stop long revision loops at $3.
> Agent recommendation: **B** — it keeps production quality at or above today's for the sprint, and the bake-off can still pick Haiku if it is not distinguishable; the per-PR budget fit is checked by the golden-set dry run, not assumed.

> **2. Must the in-loop reviewer also stay off the judge's family?** (D9) The writer writes every word; three other model roles do not: the **assessor** scores each draft turn and tells the writer what to fix; **infer** reads the request (who / ask / search query); **extraction** maps finished claims to their sources.
> **(A) Only the writer is off OpenAI.** Assessor, infer, extraction stay on `gpt-4o` until the bake-off, which may pick any family for them. *Stake: the OpenAI assessor coaches every draft toward what an OpenAI reader likes, and the OpenAI judge then scores it — the gate can reward that taste instead of funder fit. No extra cost.*
> **(B) Writer and assessor off OpenAI** (assessor on the question-1 model); infer and extraction may stay on OpenAI. *Stake: the coach and the judge are independent; ≈ +$0.02 per draft typical with Sonnet (≈ +$0.06 with Opus 4.5); bake-off assessor candidates exclude OpenAI. Production holds both provider keys.*
> **(C) Every app role off OpenAI** — production runs Anthropic only; OpenAI is used only by the eval judge. *Stake: cleanest independence (the citation checker never grades its own family's claim-to-source mapping) and one provider key in production; most Anthropic spend; changes key custody, so one more architecture reconcile.*
> Agent recommendation: **B** — the assessor is the judge's stand-in inside the loop, so sharing the judge's family undercuts the independence you locked; infer and extraction do not shape the prose the judge scores, and the citation checker reads the claim plus the captured source text, so their family matters less.

> **3. Which OpenAI models score drafts and check citations until the bake-off?** (D10) At the bake-off, judges are ranked by agreement with your calibration ratings (already locked). Something has to judge the first eval runs and the calibration drafts.
> **(A) `gpt-5` judges, `gpt-5-mini` checks citations** — ≈ $0.05 per draft judged. *Stake: strongest reader; reasoning models take no temperature setting, so run-to-run noise may be wider (wider noise bands, a less sensitive gate).*
> **(B) `gpt-4.1` judges, `gpt-4.1-mini` checks citations** — ≈ $0.03 per draft judged. *Stake: deterministic settings (temperature 0) usually mean tighter noise bands; an older generation of reader.*
> **(C) Let your calibration ratings pick the judge:** score the 10–15 calibration drafts with both `gpt-5` and `gpt-4.1`, keep whichever agrees with you more (the bake-off rule, applied early); `gpt-5-mini` checks citations; report-only runs before calibration use `gpt-5`. *Stake: under $1 of extra judging; if `gpt-4.1` wins, the noise-band history restarts at the pick, so blocking starts about 10 nights after calibration at the earliest.*
> Judging is roughly 10–25% of eval spend either way; the per-PR, model-change ($10) and nightly ($5) caps are driven mainly by drafting.
> Agent recommendation: **C** — evidence-chosen, matches the rule you already locked for the bake-off, and costs cents.

### Delta 2026-10-03 — outcome

| Field | Value |
|-------|-------|
| All delta rows locked or true-waived? | no (D8, D9, D10 open) |
| Next gate | governor answers above (one batch); §G.1 again only if D9 locks as C |
| Governor answer | |
| **Implement unblocked** | **no** for: the P1a packet (Models+tests, T022–T035 — T030 needs D8 + D9), everything after it that needs P1a merged (P2a, P2b), the P2b packet until D10 locks (T082 onward), and P3 (D3). **Narrow exception continues** (Out-of-scope excludes D3 and D8–D10) for: Phase 1–2 orchestrator glue (CP0, with T007's `ANTHROPIC_API_KEY` names), P0 ops (T013–T021, now with `ANTHROPIC_API_KEY`), the P1b packet (Durability: storage), the P1c packet (Ship), and T079 golden-set synthesis. Flips to **yes** per packet as T105 / T106 / T107 record locks |
