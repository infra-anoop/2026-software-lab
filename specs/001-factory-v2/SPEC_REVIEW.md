# Product spec review — Factory v2

## A. Executive verdict

**Do not approve yet.**

The spec has a clear governor-facing win, unusually strong traceability scaffolding, and concrete failure cases, but several core promises are not yet internally coherent. In particular, an orchestrator can apparently override gates that are also declared fail-closed, reviewer-family difference is substituted for review isolation, and the numeric concurrency behavior remains undecided without an Open Decision. The proposed seeded suite also proves that fixtures trigger detectors, not yet that the factory catches the actual silent-substitution failure it claims to eliminate. Finally, the finish bar makes every P2 item mandatory while scheduling much of P2 as stretch work, which obscures what must be true after the three-day Wave 1.

## B. Findings table

| ID | Severity | Lens | Spec locus | Finding | Suggested resolution (for human) |
|----|----------|------|------------|---------|----------------------------------|
| F1 | Blocker | Product — gate semantics | US4 scenarios 1 and 3; FR-020–021 | The spec says the orchestrator can override “a blocking gate,” while fail-closed gates protect spend, secrets, irreversible operations, and governor-owned decisions. If those gates are overridable without governor action, “fail-closed” is not true; if they are not, the promise that gates never make the governor the unblocker is not universally true. A cold planner cannot infer which rule wins. | Define two explicit classes: which gates the orchestrator may override, and which require governor authorization or cannot be overridden. Amend US4, FR-020/021, and SC-004 consistently. |
| F2 | Blocker | Product — unresolved behavior | US2 scenario 6; FR-008; Assumptions (“3–4 active workers”) | “Beyond the concurrency cap (3–4 active workers)” is not a testable cap. Three and four produce different spawn decisions, yet no Open Decision records this unresolved numeric content. | Lock one number for this version, or add a human-owned Open Decision that must close before tasks depending on spawn refusal. |
| F3 | Blocker | Product — intent fidelity | Actor definition; US2 scenario 7; FR-011; `intent.yaml` I-P3 | The intent requires an independent reviewer from another model family **that never sees the author’s thread**. The spec retains only family difference. Different-family metadata neither establishes isolation nor prevents the author narrative from being passed into review, so a named trust property was silently thinned. | Add thread/context isolation to the reviewer shall and acceptance evidence, separately from model-family difference. |
| F4 | Blocker | Product — intent traceability | Framing; FR-023; SC-005; FR-035; `intent.yaml` I-B4, I-M2, I-M3 | The spec claims every intent maps to a check, but material governor guardrails are not in the product finish evidence: no-router behavior/human-routing events, the ≈60-minute per-feature intent-capture budget, and Wave 1’s three-day target/max-two-day slip plus visible Smart Writer progress are absent or reduced to assumptions/post-mortem sentiment. Computing mapping coverage can still report success while these outcomes are untested. | Add failable rows for routing events, intent-capture governor time, and the Wave 1 timebox/cross-feature exit, or explicitly narrow/waive those intents with the governor. |
| F5 | Debate | Product — primary falsifier | US3; SC-002; acceptance rows `seed.substitution` and `seed.jargon_to_governor` | Steelman: one fixture per observed failure is a concrete regression suite and much stronger than prose. Attack: the substitution seed only tests a missing fidelity declaration, not a declared letter lock followed by a different tool/host/thinner behavior; several outcomes permit merely “flagged,” while the story promises drift is caught before reaching the governor. Passing these fixtures can therefore overstate protection against the real sprint-01 failures. | Choose whether the promise is **detector coverage** or **merge prevention**. Add a true declared-lock/substituted-output fixture and state per seed whether flagging or blocking is sufficient. |
| F6 | Debate | Product — finish bar and sequencing | Check scheduling; US6–US8; Assumptions (“Wave 1 targets 3 days”) | Steelman: making P1 and P2 the version finish bar prevents architecture religion and the learning loop from becoming permanent “later.” Attack: the table simultaneously schedules P2 as “Wave 1 (stretch) → 2,” while all P2 is mandatory for this version and Wave 1 has a hard time budget. This gives no failable checkpoint for what must work after three days before Smart Writer work proceeds. | Lock a Wave 1 minimum product slice distinct from the version finish bar, or explicitly accept that Wave 1 may not exit until all P2 work is complete and revise the timebox claim. |
| F7 | Debate | Product — religion-mining loop | US7 scenario 2; FR-029–030; SC-007; acceptance `mining.repeat_proposes` | Steelman: immediate proposals on recurrence close the learning loop faster than sprint-end retrospectives. Attack: “same/equivalent correction” has no observable identity or governor correction path, and `mining.correction_recorded` is only hybrid while repeat detection is labeled automatic. A planner can build anything from exact-id matching to semantic inference, with radically different false-positive and paperwork costs. | Decide whether equivalence is governor-linked, taxonomy-based, or machine-suggested/human-confirmed, and specify the tolerated human action at correction time. |
| F8 | Debate | Process — ceremony versus signal | US8; FR-032–034; SC-006 | Steelman: requiring enforcement references makes normative prose accountable. Attack: “every MUST/NEVER in process docs” is an unbounded repository-wide textual gate that can reward wording avoidance, force low-value check creation, and consume the three-day factory slice without demonstrating less drift. It risks making the factory a paperwork linter—the explicit anti-goal. | Bound the governed document set and define whether a stable check reference or explicit governor-judged marker is sufficient; measure false positives/overrides before expanding it. |
| F9 | Later | Product — architecture boundary | Assumptions (“final bus transport … plan Architecture decision”) | Deferring plain files vs Issues vs a git-native tracker to plan review is appropriate: the spec fixes immutable typed-message behavior and derived status without smuggling in a transport. | Preserve these behavioral constraints in plan alternatives; do not promote a transport brand into a product success criterion. |
| F10 | Nit | Product — catalog consistency and strength | Failable outcomes; Acceptance catalog | Strength: the nine success classes, linked catalog, and explicit aspirational section make the core bet substantially more falsifiable than mood-only “better autonomy.” However, FR-018 says every automatic row links to an existing test/eval while every current automatic row lacks such an id; the catalog header softens this to “once it exists.” | Clarify that linkage is required before Approved, before tasks, or before implementation completion; make FR-018 and the catalog header use the same lifecycle point. |

## C. Adversarial positions

### 1. Position: narrow the primary product bet

Do not build a general factory in this sprint. Build only the smallest enforcement loop around one Smart Writer work order: immutable order, owned paths, red-first proof, lock-fidelity check, independent isolated review, and a derived status view. The current spec tries to solve orchestration, policy linting, architecture religion, scorecards, correction mining, portability constraints, governance, and constitution migration at once. That breadth makes it likely the sprint produces many schemas and fixtures but little evidence that an hour-long worker run stays on intent. A thin end-to-end run would expose where drift actually occurs and give the next gates empirical priority.

**What would have to be true for the spec to be right anyway:** most P1/P2 checks must be cheap compositions over one shared bus and gate framework, with a credible three-day critical path and no delay to the workload.

### 2. Position: replace automatic religion mining with explicit governor tagging

Drop automatic “equivalent correction” detection from this version. Require the governor or orchestrator to link a correction to a stable pattern id when the correction is recorded, and let the post-mortem propose rules from those links. Semantic recurrence detection is itself a judgment system: it can miss paraphrases, merge unrelated concerns, and generate noisy rule proposals. Before enough correction history exists, automating equivalence may create more review work than it saves and undermine the promise of keeping the governor above bookkeeping.

**What would have to be true for the spec to be right anyway:** correction capture must provide enough structured evidence for high-precision equivalence, and false proposals must be demonstrably cheaper for the governor than explicit tagging.

## D. Independence test

**No.** A new agent can understand the product direction, entities, and most acceptance classes, but cannot produce a deterministic plan without inventing product behavior in these areas:

- whether fail-closed gates are orchestrator-overridable;
- whether the active-worker cap is three or four;
- how reviewer thread isolation is established and evidenced;
- whether each seeded violation must block or may only flag;
- how equivalent corrections are recognized;
- what exact product checkpoint must be achieved within Wave 1 before workload execution proceeds;
- which process documents are in scope for the MUST/NEVER enforcement gate.

The bus transport is not a gap here because the spec explicitly and correctly assigns that architecture choice to plan alternatives and review.

## E. Edit list for the authoring session

1. **US4 / FR-020–021** — define override authority separately for ordinary gates and fail-closed spend/secrets/irreversible/governor gates.
2. **Open Decisions** — lock the active-worker cap to one integer or add an open human row before spawn enforcement.
3. **US2 / FR-011 / SC-003** — add reviewer thread/context isolation as a shall with evidence distinct from model-family metadata.
4. **US3 / SC-002 / acceptance.md** — add a seed that declares a letter lock and then substitutes a different/thinner outcome.
5. **US3 / acceptance.md** — state per drift seed whether the required machine action is block or flag.
6. **Success Criteria / acceptance.md** — add failable evidence for no human routing and record the corresponding metric.
7. **Success Criteria / acceptance.md** — add the governor-time budget for feature intent capture, or explicitly remove it from this version.
8. **Check scheduling** — distinguish the three-day Wave 1 exit from the all-P1/P2 version finish bar.
9. **US7 / FR-029** — define correction equivalence and the governor interaction required to establish it.
10. **FR-032 / SC-006** — enumerate the process-doc scope and the accepted enforcement-reference form.
11. **FR-018 / acceptance catalog header** — align the lifecycle point at which automatic rows must link to real test/eval ids.
12. **Intent traceability statement** — reconcile or explicitly waive I-B4/I-M2/I-M3 product outcomes rather than counting mappings alone.

## F. Questions for the human

1. May the orchestrator override spend, secrets, irreversible-operation, or governor-decision gates, or do those require the governor?
2. Is the worker cap three or four active workers for this version?
3. Must each observed drift seed block merge, or is a machine warning sufficient for selected patterns?
4. After three days, must Wave 1 have all P1 and P2 checks, or may it exit on a smaller mandatory slice while P2 completes during Wave 2?
5. Should repeated corrections be linked explicitly by the governor/orchestrator, or inferred automatically and presented for confirmation?
