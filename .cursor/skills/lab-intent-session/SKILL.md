---
name: lab-intent-session
description: >-
  Structured governor interview that captures visible and invisible intent for
  a sprint or feature into specs/<###-feature>/intent.yaml (goals, anti-goals,
  religion, observed drift, pre-mortem, scorecard, budgets, conflicts), with
  every intent mapped to a check or governor-judged. Use before
  /speckit-specify for any new sprint or feature, or when the governor says
  "intent session".
---

# Lab intent session

Produces `specs/<###-feature>/intent.yaml`, which is the input to `/speckit-specify`.
Reference outputs: `specs/001-factory-v2/intent.yaml` (factory, 4 rounds plus a
conflict round) and `specs/002-swv2-durable-evals/intent.yaml` (app delta,
2 rounds).

## Rules

- **Budget:** about 60 minutes of governor time per feature. Agents draft;
  the governor reacts. The factory session on 2026-10-03 took about 56 minutes
  of wall clock. An app delta on a frozen baseline should take less. [governor-judged]
- Ask in **AskQuestion batches** of 5–9 questions per round, at most 4 rounds,
  plus one conflict round. Put the recommended option first and label it
  "(Recommended)". Use plain product/ops language with no ids. [check: od.plain-options] [check: decision-request-no-ids]
- **Harvest before asking.** Read the constitution, the sprint charter, the
  architect backlog, the baseline spec, and sprint history (re-locks, Debates,
  rework, amendments). Turn what is already locked into candidate statements.
  Do not re-ask it.
- **Recognition over recall.** Offer concrete candidate statements, options
  seeded from real incidents, and contrast probes where both options appeal.
  Allow "Other" on religion questions.
- **Surface conflicts explicitly.** When a new answer contradicts an existing
  lock or an earlier answer, pose the conflict as a plain choice and get it
  resolved. Record it in `conflicts:`. Do not resolve it silently. [governor-judged]
- **Confirm interpretations.** If a free-form answer is ambiguous (for example
  "A+D"), confirm your reading in the conflict round and record it under
  `confirmations:`.
- **Every intent maps to ≥1 check**, or to an explicit `human` check, which
  counts as governor-judged. [check: factory-check-intent]
- **Do not invent open content.** Numbers or lists the governor wants to
  measure first go into `open_content:` and become spec Open Decisions. [check: deferral-words-need-od]
- **Record governor minutes** in `capture:`. Measure from the first question
  to the last answer timestamp.
- The status goes `draft` → `resolved` (conflicts closed) → `approved`.
  Approval happens with `spec.md`. Resolving the conflicts is not approval.
- Validate before committing: the YAML parses, and every intent has a
  `checks` entry. If the factory CLI exists, also run
  `uv run --project scripts/factory factory check intent`. Commit on a
  branch and open a PR. [check: branch-protection-require-pr]

## Stable ids

The factory uses `I-<cat><n>`. App features use an app prefix (`SW-` for
Smart Writer V2). Ids are stable: retire an id instead of renumbering it.
Category letters are scoped by prefix, so `SW-M` (models) is unrelated to
`I-M` (guardrails).

| Cat | Kind | Meaning |
|-----|------|---------|
| `N` | north_star | One sentence that every other intent serves |
| `G` | goal | Outcomes the governor wants |
| `B` | rule | Agent behavior (escalation, language, fidelity, deferral, tests, paths) |
| `A` / `P` / `O` | religion (`domain: architecture / process / ops`) | Patterns a PR is rejected for breaking, even when green |
| `M` | guardrail | Mitigations derived from the pre-mortem |
| `X` | anti_goal | What this must not become |
| `E` | exemplar | Moments to preserve |
| `Q` `E` `M` `L` `D` `T` `S` `B` (app) | quality / rule | Quality rubric, eval gating, models, limits, durability, tests, ship, baseline |

## Question bank: factory or process feature (4 rounds)

**Round 1: purpose and autonomy**
- Audience: me in this repo only / me, portable to any future repo / others eventually.
- Happiest outcomes (pick up to 2): walk away for hours / see at a glance /
  machine catches drift / 3–4 decision points per feature / self-improving.
- Autonomy horizon: 1h / half day / overnight / multi-day with checkpoints.
- Ambiguity the work order doesn't answer: always stop / decide by reversibility / conservative option + logged deviation.
- Interrupts: planned checkpoints / daily digest / real-time for blockers, batched otherwise.

**Round 2: drawing out the religion, and governance**
- Mining methods (multi-select): corrections → rules / sprint history / contrast probes / pre-mortem / exemplar library.
- Strongest religion domains (pick up to 3): architecture, process, code, product taste, ops, communication.
- Who changes rules: agents propose and the governor approves every one / agents may tune within bounds / governor only.
- Build vs adopt: hybrid (adopt commodity, build the differentiators) / build / adopt.
- Host portability: Cursor-first but enforced in git and CI / Cursor-only / tool-agnostic.

**Round 3: lessons, rejection criteria, pre-mortem**
- Past drift to mechanize first. Seed from real incidents: silent substitution,
  topology locked before its consequences were felt, hidden deferral, fake-green
  tests, jargon to the governor, the governor acting as router.
- "Reject even if green" when the PR: adds an unplanned dependency or
  abstraction, uses a familiar pattern instead of a SOTA one, creeps scope,
  touches paths outside its owned set, has mirror tests, leaves noisy history,
  or drifts ops outside git.
- Pre-mortem, "it's <sprint end> and it failed; why?" (pick up to 3): tooling
  ate the sprint, gates too strict, wrong checks, paperwork, parallel mess,
  lost visibility, cost.
- Anti-goals: enterprise ceremony, more unenforced prose, replacing governor
  judgment, max parallelism, a dashboard product, a generic framework.
- Positive exemplars: which moments felt exactly right.

**Round 4: architecture religion, tensions, targets**
- Patterns seen in the code that are religion (multi-select, plus Other). Expect
  additions such as naming and scope discipline.
- Gate strictness vs governor-as-unblocker: shadow mode first / orchestrator override with a logged reason / governor-only override.
- Intent-capture budget per feature: 10 / 30 / 60 minutes.
- Time box against tooling eating the sprint: hard / soft slip / interleave.
- Correction cadence: next checkpoint / same PR / post-mortem only.
- Scorecard targets: drift-free unattended runs, decision points per feature
  (or "measure first"), first-pass acceptance, intent coverage.

## Question bank: app delta feature (2 rounds)

**Round 1: what "good" means, what must survive**
- Quality dimensions (pick up to 4). These become the judge rubric, calibrated
  against the governor's ratings.
- Who the judge imagines reading (persona).
- What must survive a deploy or restart (multi-select).
- Accepted risks of the ownership/identity model, and data retention.

**Round 2: limits, gating, pre-mortem**
- Any conflict with Round 1 or an existing lock, posed first.
- Spend ceiling per unit of work, including "measure first".
- Latency tolerance.
- Model-selection rule (quality first / best value / cheapest above a bar).
- Eval gate on a regression: block beyond noise / report only / block any drop.
- Pre-mortem (pick up to 2).

**Conflict round (always run it).** Put one question per conflict, with the
recommended resolution first. Typical conflicts: a new rule against an existing
lock, a stop-vs-continue tension, an answer whose side effect undoes a goal,
and how to read an ambiguous answer.

## Output schema (`intent.yaml`)

```yaml
schema_version: 1
feature: <###-feature>
baseline: <path to frozen baseline spec>    # app deltas only
status: draft | resolved | approved
capture: { date: YYYY-MM-DD, rounds: <n>, governor_minutes: <n>, budget_minutes: 60 }
north_star: { id: <P>-N1, statement: "...", checks: [ ... ] }
scorecard:            # factory: <metric>: { target: <n|null>, meaning: "..." }
open_content: [ "..." ]      # measure-first content → spec Open Decisions
locks: [ "..." ]             # app deltas: locks made in spec/plan review
intents:
  - id: I-B1
    kind: goal | rule | religion | guardrail | anti_goal | exemplar | quality
    domain: architecture | process | ops      # religion only
    statement: "One testable sentence (or a short block)."
    source: [session.r1, constitution.G, history.<incident>, resolution.CONFLICT-2]
    checks:
      - { kind: ci|hook|lint|schema|metric|review|human|test|eval, ref: <gate-or-check-id>, status: planned|exists }
conflicts:
  - { id: CONFLICT-1, between: [<id>, <lock>], summary: "...", resolution: "...", constitution_impact: "...", status: resolved }
confirmations:
  - { date: YYYY-MM-DD, item: "..." }
```

Check refs should use gate ids from `specs/001-factory-v2/contracts/gates.md`
where one fits. A `hook` check always needs a `ci` twin. [check: hook-has-ci-twin]

## After the session

1. Report the counts to the governor: total intents, how many are machine-checked,
   how many are governor-judged, and how many checks are planned vs existing. If
   the planned checks exceed the sprint's capacity, say so; the spec ranks them.
2. Run `/speckit-specify` with `intent.yaml` as input. Every functional
   requirement cites intent ids.
3. Post-mortem: harvest corrections and overrides into new intents for the next
   session. Capture is a loop, not a one-off document.
