# T* review — `factory-status-test` (round 1)

## A. Executive verdict

**Do not implement against these tests yet.** Round 1 uses the normal Blocker /
Debate / Later / Nit bar. The tests are honestly red and reject an always-passing gate,
but they can go green without using the board derivation that T102 explicitly names.
Their D5 probe also leaves a plausible head-package import path unpoisoned, while two
proposed blocking rules are product content not established by I-M4 or its catalog row.

## B. Findings table

| ID | Severity | Lens | Locus | Finding | Suggested resolution |
|----|----------|------|-------|---------|----------------------|
| T-ST1 | Blocker | Wrong-thing test | `test_blocks_order_events_the_board_would_drop`; T102 | **Root-cause class: oracle not observed.** The tests assert hand-picked consistency symptoms, but never make the result of `main`'s lifecycle/board derivation observable. A bespoke scanner that parses the bus, rejects orphan events and missing decision requests, and never calls the derivation passes all eight tests. **Consequence:** CI can certify I-M4 while the gate is disconnected from the board used by the governor. **Likelihood:** high; direct scanning is the shortest implementation suggested by these cases. | Smallest fix: add one sabotage test that replaces `main`'s derivation result with a snapshot omitting a known valid order and requires the gate to block. This one regression proves the gate compares head order folders with the installed derivation rather than reimplementing selected rules. |
| T-ST2 | Blocker | Lock fidelity / D5 | `test_executes_no_head_code` | **Root-cause class: incomplete trust-boundary sentinel.** The fixture poisons the gate, lifecycle, renderer, conftests and `sitecustomize`, but not the head's `factory` package root or `factory.bus.store`. An implementation can export the head tree and import its bus loader while still blocking the orphan and leaving the marker absent. **Consequence:** PR-controlled Python executes in the trusted judge, violating the D5 letter lock for every contributor and invalidating status authority. **Likelihood:** medium; reusing the head's loader is a plausible shortcut. | Smallest fix: poison the head package root and `factory/bus/store.py` in the existing D5 test; keep the single marker assertion. |
| T-ST3 | Debate | Scope | proposed pass/fail oracle; I-M4; `board.matches_reality` | **product:** “every head bus file parses” is already the `bus.schema` gate and is not stated by I-M4, T102, or `board.matches_reality`. “Every governor wait has a recorded decision request” changes `main`'s deliberate placeholder behavior and is likewise not an approved shall. The one-entry-per-order rule is supported by “for every order” plus T102's board-derivation wording; the other two rules are invented product policy. | Human choice: narrow this gate to comparing order folders with `main`'s derived board, or explicitly lock the two additional blocking rules in the contract/catalog. Do not derive new product shalls from the test handoff. |
| T-ST4 | Nit | Red-first honesty | focused test file | Strength: all eight cases fail at the missing entrypoint, negative cases defeat an always-pass gate, malformed data is not hidden by the tolerant `bus_snapshot`, and the tests use only local fixture git repositories with no network or clock race. | Keep these controls after resolving T-ST1–T-ST3. |
| T-ST5 | Later | Order data | order and handoff artifacts | No defect found in the disclosed order metadata: the fifth owned path makes the handoff note owned; 50 minutes is within the 60-minute horizon; omitting `factory-status-test` from `checks` is necessary under D5 bootstrap; and `lock.letter-tokens` judges declared order locks even though D5 is absent from `main`'s spec. The phrase already appears in changed Python source. | At implementation handoff, record the bootstrap manual equivalent for the omitted self-gate; no test edit is needed now. |

## C. Adversarial positions

1. **Position: these tests would go green while a spec lock fails.** A gate can read
   every blob itself, reject parse errors, orphan events and unresolved decision ids,
   and return the expected messages without ever invoking `main`'s lifecycle derivation.
   It can also import `factory.bus.store` from an exported head tree because that module
   is not poisoned. The suite then goes green while both T102's derivation requirement
   and D5 fail. **What would have to be true for the suite to be right anyway:** direct
   validation would have to be accepted as equivalent to board derivation, and importing
   unpoisoned head Python would have to be excluded by implementation review rather than
   the contract tests.

2. **Position: these tests over-constrain implementation / test the wrong layer.**
   Requiring every bus blob to parse duplicates `bus.schema`; requiring a decision
   request rejects the placeholder behavior intentionally implemented by `BusView`.
   Neither is in I-M4's “one board answers” statement or the catalog shall that board
   state equals derived state. These checks can block unrelated malformed bus content
   or an intentionally visible missing-decision placeholder even when order membership
   matches the board. **What would have to be true for the suite to be right anyway:**
   the governor must explicitly adopt both conditions as part of this gate's product
   contract.

## D. Catalog / contract coverage map

| Catalog id or contract hook | Test file / name | Can fail today? | Gap |
|-----------------------------|------------------|-----------------|-----|
| T102: use `main`'s board derivation over head bus | `test_blocks_order_events_the_board_would_drop` | no | A direct consistency scanner passes; derivation output is never made observable. |
| D5: head is only data | `test_executes_no_head_code` | partly | Selected modules are poisoned, but head package/bus imports remain executable. |
| I-M4 / `board.matches_reality`: every order represented | valid-bus and orphan-event cases | yes | Positive and dropped-event symptoms are covered; T-ST1 prevents claiming the named oracle. |
| Fail closed on unreadable head | `test_fails_closed_when_the_head_commit_is_unreadable` | yes | None. |
| Proposed parse-all rule | malformed YAML/schema-invalid parametrization | yes | Product basis absent; duplicates `bus.schema`. |
| Proposed recorded-decision rule | `test_blocks_a_governor_wait_with_no_recorded_decision` | yes | Product basis absent; contradicts accepted placeholder behavior unless newly locked. |

## E. Edit list

- `scripts/factory/tests/unit/gates/repo/test_status_test.py`: add one sabotaged-derivation
  case proving a missing derived entry blocks.
- `scripts/factory/tests/unit/gates/repo/test_status_test.py`: poison the head package root
  and `factory/bus/store.py` in the existing D5 test.
- `scripts/factory/tests/unit/gates/repo/test_status_test.py`: remove parse-all and
  missing-decision blocking cases unless the governor locks those product rules.

## F. Questions for the human

1. Should this gate only prove that every head order folder appears in `main`'s derived
   board, or should it also duplicate `bus.schema` by rejecting every malformed bus file?
2. Should an order waiting on an unrecorded decision block, replacing the board's current
   visible placeholder behavior?

## Round 2

### A. Executive verdict

**Do not implement against these tests yet.** Round 2 uses the normal bar. T-ST2 is
resolved: the hostile head now includes the package root and every plausible `factory`
module the gate could import, while retaining the no-checkout/no-write controls. T-ST1 is
only partly resolved because the new test pins the exact aggregate helper rather than
the accepted requirement to use `main`'s lifecycle derivation. T-ST3 remains parked for
the governor and was not reviewed this round.

### B. Findings

| ID | Severity | Lens | Locus | Finding | Suggested resolution |
|----|----------|------|-------|---------|----------------------|
| T-ST6 | Blocker | Scope / wrong-layer test | `test_blocks_when_main_derivation_omits_a_head_order` | **Root-cause class: implementation symbol substituted for contract behavior.** The test requires a call to the exact internal helper `factory.lifecycle.derive.derive_from_view`. A reasonable implementation can build the same head `BusView`, call `main`'s `derive_order` for each record, and compare the resulting lifecycle entries with head order folders. That satisfies T102's “main's board derivation” requirement but fails `assert calls`. **Consequence:** a contract-correct implementation is rejected before implementation review. **Likelihood:** medium; per-record derivation is a direct design when reporting the particular omitted order. | Smallest fix: sabotage and spy on `derive_order` (including a top-level gate alias) instead. Have the wrapper change the `WORKING` lifecycle's id, then require the gate to block naming `WORKING`. Both aggregate `derive_from_view` and direct per-record use then pass, while a bespoke scanner still fails the test. |

### C. Round-2 checks

- **T-ST1:** The sabotage makes derivation output observable, but exact
  `derive_from_view` coupling over-constrains a reasonable implementation (T-ST6).
- **T-ST2:** Resolved. The package root, bus/config/order/lifecycle/board/gate modules,
  conftests, and `sitecustomize` are hostile; any plausible head import writes the marker.
- **Regression:** None found outside T-ST6. The focused suite remains honestly red:
  **9 failed** at the missing entrypoint, with no collection errors. Ruff check and format
  check pass. The fixtures remain local and deterministic.
- **T-ST3:** Out of scope by orchestrator instruction; no disposition.
- **Later items:** None.

## Round 3 (harm bar)

### Verdict

**Approve tests as-is.** T-ST6 is resolved: sabotaging `derive_order` exercises both
reasonable designs, because `derive_from_view` calls that same per-record function while
a gate may also call it directly. The changed lifecycle id must affect the gate's verdict,
so merely calling derivation while trusting a parallel scanner cannot pass. The D5
hostile-head coverage from round 2 remains intact, and no test can now pass falsely on
the reviewed locks.

### Harm-bar findings

No Blocker meets constitution §J's round-3 harm bar. No Later item was found.

T-ST3 remains parked for the governor and out of scope; this approval does not adjudicate
the malformed-bus or missing-decision product rules.

### Verification

- Focused suite: **9 failed**, all at the intentionally missing gate entrypoint; no
  collection error.
- Ruff check and format check: pass.
- Delta inspection: only the oracle sabotage moved from `derive_from_view` to
  `derive_order`; the remaining tests are unchanged.

## Triage

Rounds 1 and 2 were triaged by the orchestrator in `wo-20261006-factory-status-test.amend-01` (T-ST1 and T-ST2 accepted, T-ST4 noted, T-ST5 accepted as Later) and `.amend-02` (T-ST6 accepted). The product Debate T-ST3 was locked by the **governor on 2026-10-06**, recorded in `.amend-05`. The tests are frozen; none was added or changed for the lock.

| ID | Disposition | Decided by | Resolution |
|----|-------------|------------|------------|
| T-ST1 | accept | orchestrator (process) | `test_blocks_when_main_derivation_omits_a_head_order` added (`amend-01`), reworked under T-ST6 |
| T-ST2 | accept | orchestrator (process) | `test_executes_no_head_code` poisons the head `factory` package (`amend-01`); resolved in round 2 |
| T-ST3 | **closed: option B, governor 2026-10-06** | governor (product) | Verbatim: "T-ST3 = option B, block both (governor, 2026-10-06 09:16 PT). 1. A malformed or unreadable head bus file blocks. This already works through `main`'s strict loader, so keep it. 2. An order waiting on the governor with no recorded decision request on the bus blocks, naming the order and the decision." Rule 1: `test_fails_closed_on_a_malformed_bus_file` passes with no added code. Rule 2: `test_blocks_a_governor_wait_with_no_recorded_decision` passes; the gate blocks each open dependency of a `blocked_on_governor` board entry that has no decision request on the head bus |
| T-ST4 | noted — strength | orchestrator (process) | Controls kept |
| T-ST5 | accept (Later) | orchestrator (process) | Bootstrap manual equivalent recorded in the handoff note |
| T-ST6 | accept | orchestrator (process) | Sabotage and spy moved to `derive_order` (`amend-02`) |
