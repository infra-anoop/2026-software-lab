# Contract — evals and quality gate (002)

## Golden case (`apps/smart-writer-v2/evals/golden/<case-id>.yaml`)

| Field | Rule |
|-------|------|
| `id` | stable slug |
| `split` | `tuning` \| `heldout` |
| `category` | e.g. `foundation-program`, `government-rfp`, `corporate-giving`, `nongrant-smoke` |
| `funder_rfp` | `{source_url, excerpt}`; public RFP text |
| `org_materials` | list of synthetic documents (inline text or fixture upload paths) |
| `prompt` | the user's opening message(s) |
| `web_research` | bool (per-PR subset forces `false`; nightly honors the case) |
| `expectations` | optional notes for the governor; not seen by the judge |

`evals/subset.yaml` lists one `tuning` case per category for per-PR runs. `heldout` cases may appear only in nightly and post-mortem runs; the `eval.heldout_unused` check scans bake-off, prompt, and judge-selection run configs.

## Judge output (`ProgramOfficerJudge`, Gemini)

`{funder_fit, narrative, evidence_of_impact, voice}`: each `{score: 1..5 int, rationale: str}`. The persona prompt is versioned in `evals/prompts/program_officer.md`. The judge sees the RFP excerpt + draft only (not expectations, not org materials beyond what the draft cites).

## Support output (`SourceSupport`, Gemini)

Per cited claim: `{claim, source_ref, verdict: supported|unsupported, quote?}`. Support rate = supported / cited claims per draft; averaged per run.

## Noise band and gate (`lab_shared.evals`)

- Nightly on `main`: full set ×3 → per case-dimension mean; **band[d] = max(range of per-run means across the 3 repeats for dimension d, 0.25)**; same for support rate (floor 0.05). Published as artifact `swv2-eval-baseline.json`.
- Per PR: the subset ×1. For each dimension d: `drop = baseline_subset_mean[d] − pr_mean[d]`. **Block if any `drop > band[d]`**, or support `drop > band[support]`. No offsetting.
- Gate state: `report_only` until a baseline exists **and** `evidence/calibration.yaml` shows D1 met; then `blocking`. Drift-class override (orchestrator, reason) per factory FR-020.

## Spend ledger

Per-PR cumulative eval cost from prior `swv2-evals` check runs on the PR. A new run is refused when `ledger + estimate > $2` (governor-only "spend" gate). Skipped when the `apps/smart-writer-v2` + `modules/lab_shared` tree hash equals the last evaluated hash.

## Calibration and blinded review (`evals/calibrate.py`)

Generates `evidence/calibration-sheet-<date>.md` (drafts without scores) for the governor; the governor fills `evidence/calibration-<date>.yaml` `{case, dimension, score}`; the script computes the share within ±1 per dimension (D1: ≥ 80% every dimension). Post-mortem blinded review uses the same flow with ~5 drafts, held-out included (FR-013b).
