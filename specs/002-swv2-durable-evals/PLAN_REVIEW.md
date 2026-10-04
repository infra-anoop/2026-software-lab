# Plan Architecture Review — Smart Writer V2 durable state + measured quality

**Reviewer role**: Independent architecture / plan reviewer  
**Primary**: `specs/002-swv2-durable-evals/plan.md`  
**Locks**: Approved delta spec, F1–F9, A27–A29, and frozen baseline decisions  
**Companions**: `research.md`, `data-model.md`, `contracts/`, `acceptance.md`, `quickstart.md`  
**Date**: 2026-10-03

## A. Executive verdict

**Do not approve architecture yet**

The plan names its runtimes, custody, repositories, graph nodes, data model, and non-sibling alternatives well enough that most implementation boundaries are task-ready. Approval is blocked by two durability races: retention can delete a conversation while it is being used, and startup recovery has no atomic ownership protocol preventing a recovered job from being duplicated or stranded. The eval architecture also publishes its held-out slice nightly despite a locked promise that the slice is never used for selection, while its three-repeat range is too weakly specified to support the no-op and regression claims. Phasing is ordered sensibly, but those architecture contracts must be repaired before tasks.

## B. Findings table

| ID | Severity | Lens | Plan locus | Finding | Suggested resolution (for human) |
|----|----------|------|------------|---------|----------------------------------|
| **P1** | **Blocker [arch]** | Data & contracts | `plan.md` Boundaries `retention`; `data-model.md` Use/Sweep; spec FR-004 | The sweep is a read-then-side-effect-then-delete sequence: select rows older than 30 days, delete Storage objects and checkpoints, then delete the conversation. A concurrent open/upload/generate/job completion can refresh `last_used_at` after selection but still lose its Storage object or entire conversation. A running recovered job can likewise finish into a conversation the sweeper has removed. “Idempotent” does not solve this eligibility race. | Lock a deletion protocol before tasks: atomically mark/claim an expired conversation only if it is still expired and has no active job, recheck under a row lock, make user/job touches reject or cancel deletion, and define compensating retry for Storage deletion. Test touch and job-completion races, not only static fixtures. |
| **P2** | **Blocker [arch]** | Orchestration / durability | `plan.md` Orchestration; `research.md` Jobs; `data-model.md` Job recovery | Durable job rows plus an in-memory `JobRunner` do not yet form a durable dispatch protocol. No atomic claim/lease identifies which process owns `queued` or `running`; a crash after enqueue but before status change, during startup recovery, or during a rolling overlap can strand or duplicate execution. LangGraph checkpoints recover graph state but do not make external calls, artifact writes, cost charges, or the jobs-table transition exactly-once. | Specify a transactional state machine with claim/lease, attempt identity, stale-lease recovery, and idempotent result publication. Either adapt `JobRunner` around durable claims or choose the researched Postgres queue alternative. Define what happens when a node repeats after checkpoint recovery. |
| **P3** | **Blocker [product]** | Spec lock fidelity / eval validity | F2; spec FR-007/SC-013; `research.md` Evals; `contracts/evals.md` | The locked held-out slice is “never used for prompt, model, or judge selection,” yet the full held-out scores are run and published nightly to Logfire and CI artifacts. A config scan can prove that a run did not directly load held-out cases for a selection command; it cannot prevent humans or agents from selecting prompts/models after observing nightly held-out results. Repeated publication converts the holdout into a monitored test set and contradicts the letter of F2/SC-013. | Keep one genuinely sealed final slice whose drafts/scores are revealed only at post-mortem, or weaken the lock explicitly and create a fresh holdout on a fixed cadence. Tuning and nightly-monitoring sets may remain visible, but must not be called held-out. |
| **P4** | **Debate [arch]** | Learning / SOTA fit / eval statistics | `research.md` Evals; `contracts/evals.md` Noise band | The strongest case for `k=3` plus a range is cost and transparency. The attack is that a range of three means has no stable confidence interpretation, the 0.25/0.05 floors are asserted rather than calibrated, and one PR sample is compared with a previous nightly sample under judge and model randomness. It can be loose after one outlier, tight after three lucky runs, and cannot substantiate SC-006’s no-op behavior. Managed alternatives are visible, but their experiment-diff and variance tooling is rejected without showing the local method is adequate. | Human chooses: (A) keep the local gate but require a paired main-vs-PR run, more repeats or a predeclared robust interval calibrated on historical no-ops; or (B) adopt a managed/OSS eval backend for experiment comparison while retaining pydantic-evals as the runner. Record the statistical operating point and cost consequence. |
| **P5** | **Blocker [arch]** | Data & contracts / cost | `plan.md` `spend`; `research.md` Search/LLM; `contracts/http-api-delta.md`; spec FR-017 | The meter “sums PydanticAI usage per call and stops before a call that would cross the ceiling.” Usage is known after a call, so past usage alone cannot guarantee that the next call will not push the job over the locked $3 maximum. A price table also needs model-version, token-class, tool, retry, and provider-pricing semantics. The architecture currently promises a hard pre-call property with post-call information. | Define a conservative pre-call reservation from model-specific maximum output tokens plus bounded input/tool/retry cost, enforce provider token caps, reconcile actual usage after each call, and fail closed on unknown model prices. If that is too conservative, ask the governor to change “never above” rather than silently implementing a post-hoc meter. |
| **P6** | **Debate [arch]** | Topology & runtime custody | `plan.md` Staging database D5-A; `research.md` Data/Topology; `data-model.md` `langgraph.*` | The recommended shared-project option isolates app tables with `search_path=staging` and Storage with a second bucket, but declares one fixed `langgraph` checkpoint schema. Production and staging would therefore share checkpoint tables unless the saver can be configured to distinct schemas. This weakens staging isolation and makes retention/recovery capable of touching the other environment’s checkpoints. D5 is correctly open, but Option A’s stated consequences are incomplete. | Human chooses after the plan proves one of: environment-specific saver schemas and credentials with tests; a separate Supabase project; or a recorded Neon fidelity waive. Do not approve Option A on `search_path` alone. |
| **P7** | **Debate [arch]** | Eval data contract | `contracts/evals.md` Golden case and SourceSupport; `research.md` Evals | The support checker outputs `source_ref` and an `optional` quote, but the contract never defines the immutable source corpus it receives. Public URLs and web results can drift; fixture upload paths do not specify content hashing or source resolution. `supported / cited claims` is also undefined for a draft with zero cited claims, which can reward citation omission or produce a divide-by-zero policy fork. | Persist content-addressed source snapshots in each case, pass the exact cited source text to the checker, validate references before judging, and lock zero-citation behavior as failure or a separately reported coverage gate. Keep web-enabled nightly data versioned rather than silently mutable. |
| **P8** | **`Later` [product]** | Spec lock fidelity / cold-agent readiness | F7–F8; `plan.md` Risks and Phasing; `contracts/evals.md` | Product review explicitly `deferred` two definitions to the plan: the canonical latency workload/sample and the owner/time bound for a nightly-only regression. The plan mentions p95 and an orchestrator-owned board item but defines neither workload/sample nor deadline. Tasks would have to invent product policy. | Add the canonical latency cases, sample count, warm/cold conditions, and reporting aggregation; add the nightly-regression owner, merge consequence, and response deadline before generating matching eval tasks. |
| **P9** | **Nit [arch]** | Strength / cold-agent readiness | Architecture, `research.md`, contracts | Strength: unlike the frozen baseline plan, this delta locks one-service same-origin topology, server-side secret custody, named LangGraph nodes, durable entities, explicit API deltas, and credible non-sibling alternatives for every required block. D5-C is also correctly identified as an A27 fidelity delta rather than smuggled in as “Postgres equivalent.” | Preserve these locks. After P1–P8 are resolved, a cold agent should not need chat archaeology for ordinary repository, cookie, UI-build, or provider-adapter tasks. |

## C. Adversarial positions

### 1. Position: kill or narrow one Architecture building block / boundary

Kill the in-memory `JobRunner` as the executor for durable jobs. Once a durable jobs table and Postgres checkpointing exist, a process-local queue adds a second scheduler with no durable handoff, lease, or attempt identity. Startup scanning is an improvised queue protocol, and every crash window must now be solved around it. A small Postgres-backed queue such as Procrastinate/pgqueuer would make claim, lease, retry, and recovery explicit while keeping the one-service/one-database topology and LangGraph checkpointer. If that is too much for P1, narrow the promise to visible failure after restart; do not imply robust resume.

**What would have to be true for the plan’s stance to be right anyway:** `JobRunner` must become a thin executor over transactional durable claims, all repeatable side effects must be idempotent, and rolling overlap must be proven safe.

### 2. Position: Architecture under-teaches SOTA / over-self-hosts / skips managed alternatives

The alternatives research is materially better than the baseline, but the eval choice still optimizes stack coherence over statistical and review quality. Braintrust and LangSmith are dismissed as extra vendors, while the local design must independently implement dataset versioning, paired experiment comparison, human calibration, blinded review, variance handling, cost ledgers, and artifact retention. That is the largest new learning surface in the feature, yet the plan spends only three repeats on uncertainty and publishes the holdout into ordinary telemetry. Either use managed experiment tooling for the evaluation-control plane or narrow the local claim to a first measurement harness, not a reliable blocking gate.

**What would have to be true for the plan’s stance to be right anyway:** the local runner must prove stable no-op false-positive rates, immutable datasets, blinded holdout custody, and reproducible comparisons within the stated budget.

## D. Independence / tasks readiness

**No — not for the durability and blocking-eval slices.** A cold agent can generate tasks for repository interfaces, cookie ownership, same-origin HTTP, UI image build, migrations, model factories, and ordinary eval schemas. It cannot safely generate tasks for retention, job recovery, hard spend enforcement, staging checkpoint isolation, or held-out custody without inventing architecture.

The remaining chat-shaped forks are:

- Expired-conversation claim/lock behavior under concurrent touch and active jobs.
- Durable job claim, lease, attempt, retry, and idempotent publication semantics.
- Whether “held-out” remains truly blind or becomes a visible monitoring set.
- Paired versus historical baseline comparison and the statistical operating point.
- D5 staging form and environment isolation of LangGraph saver tables.
- Immutable support sources and zero-citation treatment.

`research.md` does not fail the alternatives gate: it names credible managed, OSS, and non-sibling choices for every major block. The defect is now judgment and contract precision, not missing exploration.

## E. Edit list

1. **Architecture — retention boundary**: add expired-row claim/lock, active-job exclusion, concurrent-touch behavior, and Storage compensation.
2. **Architecture — jobs**: add durable claim/lease/attempt state machine and idempotent result-publication rule.
3. **research.md — jobs**: compare the completed durable-claim design directly with Procrastinate/pgqueuer, not only at a `future` replica trigger.
4. **Architecture / evals**: separate visible nightly monitoring data from a sealed post-mortem holdout.
5. **contracts/evals.md — gate**: define paired or historical comparison, calibrated variance rule, baseline version, and no-op false-positive evidence.
6. **Architecture — spend**: specify pre-call reservation, provider token bounds, retry/tool accounting, and unknown-price failure.
7. **Staging D5**: state the LangGraph schema and credentials for each environment under every option.
8. **contracts/evals.md — support**: add content-addressed source snapshots, checker inputs, citation coverage, and zero-citation semantics.
9. **Architecture — eval operations**: add nightly-regression owner, merge consequence, and response deadline.
10. **Architecture — latency**: add canonical workload, sample size, warm/cold conditions, and p95 aggregation.

## F. Questions for the human

1. Should the held-out set stay genuinely unseen until post-mortem, or may nightly results become a visible monitoring set with a separately sealed final holdout?
2. For durable execution, keep `JobRunner` only if it is rebuilt around transactional leases, or use a Postgres-backed queue now?
3. Is a paired main-vs-PR evaluation worth the extra spend to make the blocking comparison defensible, or should the first release remain report-only?
4. Which D5 staging form do you lock after accounting for checkpoint-schema isolation: shared Supabase project, separate project, or explicit Neon fidelity waive?
5. Should a draft with no cited claims fail source-support coverage, or be reported separately without passing the support gate?
