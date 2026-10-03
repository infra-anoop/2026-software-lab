# Contract — gate registry and CI checks

Registry: `scripts/factory/gates.yaml` (schema in [`../data-model.md`](../data-model.md) § Gate). CI workflow `.github/workflows/factory-gates.yml` runs on `pull_request`. One CI job per gate *group* (to keep runner minutes low); each gate reports a separate status line `factory/<gate-id>` via the checks API so branch protection can require each one.

## Override resolution

A gate that fails looks for `bus/orders/<order-id>/override-NN.yaml` with `gate: <id>` in the PR head:

- `class: drift` → override by `orchestrator` or `governor` with a reason → status `success` with summary "overridden: <reason>"; counted.
- `class: governor-only` → override must have `actor: governor` and (under D4-A/B) a verified identity; otherwise stays `failure`.

## P1 registry (Wave 1)

| Gate id | Class | Category | Intents | Scope |
|---------|-------|----------|---------|-------|
| `bus.schema` | drift | drift | I-M2 | repo |
| `bus.immutable` | drift | drift | I-M2 | changed |
| `bus.no-handwritten-status` | drift | drift | I-M2 | changed |
| `factory-check-intent` (presence) | drift | drift | I-N1, I-P4 | repo |
| `red-first-proof` | drift | drift | I-B7, I-P2 | changed |
| `test-seam-ban` | drift | drift | I-A8 | changed |
| `diff-within-owned-paths` | drift | drift | I-B8, I-A8 | changed |
| `deferral-words-need-od` | drift | drift | I-B6 | changed (specs/**) |
| `order-fidelity-declared` + `lock.letter-tokens` | drift | drift | I-B5 | changed |
| `decision-request-no-ids` | drift | drift | I-B3 | changed |
| `catalog-test-linkage` | drift | drift | I-B7 | changed |
| `pr-links-order` | drift | drift | I-P1 | PR |
| `order-blocked-on-open-human-od` | governor-only | governor_decision | I-X3 | PR |
| `spawn-concurrency-cap` | drift | drift | I-X4 | PR |
| `verdict.reviewer-family-differs` + `verdict.inputs-isolated` | drift | drift | I-P3 | PR |
| `message.override` | governor-only | governor_decision | I-M1, I-P9 | PR |
| `gate.fail-mode-category` | drift | drift | I-P9 | repo |
| `hook-has-ci-twin` | drift | drift | I-G5 | repo |
| `factory-status-test` | drift | drift | I-M4 | repo (unit) |
| existing: `validate-secrets-schema` | governor-only | secrets | I-O2, I-A3 | repo |
| existing: `validate-deploy-env`, `uv-sync-locked` | drift | drift | I-O1, I-O3 | repo |

**Deferral-words rule detail:** in `specs/**` and `notes/sprints/**`, the words *later, optional, deferred, TBD, future, stretch* need, on the same line or table row, one of: an Open Decision id that exists (`D\d+`), a pointer `→ <artifact>` to an existing file or phase (`→ plan`, `→ sprint 03` with a waived OD), or `[governor-judged]`. Spec-review tables ("Later → plan") satisfy it by pointer.

## P2 registry (Wave 2, by sprint close)

`import-layers`, `agent-has-output-type`, `banned-getenv-outside-config`, `vendor-imports-only-in-adapters`, `generic-identifier-ban`, `lab-shared-declares-consumers`, `new-dependency-needs-decision-ref`, `research-decision-has-nonsibling-alt`, `od.arch-options-have-consequences`, `od.plain-options`, `message.correction` + `repeated-corrections`, `sprint-close-requires-postmortem`, `codeowners-governor-on-rule-paths` (governor-only, per D4), `process-rule-cites-check`, `mutation-changed-lines` (70%), `block-system-path-edits` (hook + CI twin).
