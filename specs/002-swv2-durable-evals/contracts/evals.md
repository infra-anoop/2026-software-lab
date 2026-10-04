# Contract — evals and quality gate (002)

## Golden case (`apps/smart-writer-v2/evals/golden/<case-id>.yaml`)

| Field | Rule |
|-------|------|
| `id` | stable slug |
| `split` | `tuning` \| `heldout` |
| `category` | e.g. `foundation-program`, `government-rfp`, `corporate-giving`, `nongrant-smoke` |
| `funder_rfp` | `{source_url, retrieved_at, sha256, excerpt}` (the snapshot is the source of truth; the URL is provenance only) |
| `org_materials` | list of `{path, sha256}` under `evals/golden/materials/` (content-addressed; CI verifies hashes) |
| `prompt` | the user's opening message(s) |
| `web_research` | bool (per-PR subset forces `false`; nightly honors it) |
| `expectations` | governor notes (may be omitted); never shown to the judge |

**Held-out custody (sealed):** `heldout` cases live under `evals/golden/heldout/`. The eval runner refuses to load them unless invoked as `evals.run --postmortem` with sprint id; `eval.heldout_sealed` scans every workflow and run config for that path. Their drafts and scores are first generated at the post-mortem.

## Judge output (`ProgramOfficerJudge`, Gemini)

`{funder_fit, narrative, evidence_of_impact, voice}`: each `{score: 1..5 int, rationale}`. The persona prompt is versioned in `evals/prompts/program_officer.md`. The judge sees the RFP excerpt and the draft only.

## Support output (`SourceSupport`, Gemini)

Input per cited claim: the claim text plus the **exact captured source text** from `provenance_records.source_text` (for uploads/materials, the hashed file; for nightly web runs, the page text captured during that run and stored in the run artifact). Unresolvable references are `unsupported`.
Output: `{claim, source_sha256, verdict: supported|unsupported, quote?}`.
Draft support rate = supported / cited claims. **A draft with zero cited claims on a case with source materials scores 0** (no reward for omitting citations); citation count is reported alongside.

## Per-PR gate (paired — locked 2026-10-03)

- One job builds **main** and **PR** heads. Both run the per-PR subset (`evals/subset.yaml`, tuning cases only, sized so a paired run costs ≤ ~$1.50) with the same seeds and settings.
- Per dimension d: `Δd = mean_main[d] − mean_pr[d]`; the support rate likewise.
- **Noise band:** `band[d]` = 95th percentile of |Δd| over the most recent ≥ 10 **paired no-change comparisons** (main vs main, run nightly and on PRs that do not touch drafting paths), with a floor of 0.25 for scores and 0.05 for support.
- **Block** if any `Δd > band[d]` or `Δsupport > band[support]`; no offsetting.
- **Report-only** until ≥ 10 no-change comparisons exist **and** at most 1 of the last 10 would have blocked **and** D1 calibration is met (`evidence/calibration-*.yaml`). The state is shown in the check summary.
- Overrides: drift class (orchestrator + reason).

## Nightly (main)

- One paired no-change comparison on the subset (feeds the band).
- Full **tuning** set ×1 for monitoring and latency (never held-out).
- **Nightly cap (D7):** $5 per night. When the dry-run estimate exceeds it, the run is skipped, the job summary says so, and artifact `swv2-nightly-over-budget` makes the orchestrator flag it on the factory board.
- **Latency workload:** every tuning case at its own `web_research` setting, with real providers, on a GitHub-hosted runner. p95 over that night's case runs plus a rolling 7-day p95. The first case per run is reported separately as a cold start. Reported against the 10-minute target, not gated.
- **Nightly-only regression** (a dimension or support below the previous 7-night median by more than its band): the orchestrator opens a regression order on the factory board within the same working day; it must be fixed or overridden with a reason within **2 working days**. Every app PR's eval summary shows the open regression; it does not block merges.

## Spend ledger

Per-PR cumulative eval cost from prior `swv2-evals` check runs on the PR. A new run is refused when `ledger + estimate > $2` (governor-only "spend" gate). A **model-change PR** (full tuning set, see scope detection) has its own budget of **$10** (D6) instead of $2; beyond it the run waits for governor approval through the same spend gate. Skipped when the `apps/smart-writer-v2` + `modules/lab_shared` tree hash equals the last evaluated hash.

## Calibration and blinded review (`evals/calibrate.py`)

Generates `evidence/calibration-sheet-<date>.md` (drafts without scores); the governor fills `evidence/calibration-<date>.yaml` `{case, dimension, score}`; the script computes the share within ±1 per dimension (D1: ≥ 80% on every dimension). The post-mortem blinded review uses the same flow with ~5 drafts, including the first-ever held-out drafts.
