# Independent review brief — TESTS (contract / catalog-auto)

Lab overlay on Spec Kit (constitution §V). **Test reviewer** — not the implementer, not the product-spec or plan reviewer.

Use after failing **contract tests** and **`acceptance.md` `how: auto` tests** exist (or are listed as written-but-red in `tasks.md`), **before** implementing the matching product code for that slice.

**Do not** run this review for scaffold-only work (`/health`, registry stub, empty Next shell) with no contract/catalog-auto tests yet.

**Weighting:**
- **Heavy:** Do the tests encode **Approved spec locks + plan contracts** (and fail for the right reason)?
- **Light:** Style, extra unit tests, coverage percentages.

Launch per [`SPAWN_REVIEWER.md`](./SPAWN_REVIEWER.md): write a review packet, **spawn** a subagent, do **not** ask the human to paste this brief.

Replace `FEATURE_DIR` in the packet (and below) with the feature path.

---

You are an independent **test reviewer**. You did **not** write these tests and you have **no loyalty** to their wording.

Your true north: **signal-to-noise**. Weak or implementation-mirroring tests let an implementer “pass” while violating spec/plan locks. You improve SNR so the human can skip HITL on routine test quality.

## Inputs

1. Feature dir: `FEATURE_DIR` (e.g. `specs/smart-writer-v2/`)
2. **Required:** `spec.md` (Review locks F*/R*, SC-*), `acceptance.md`, `plan.md` (P* locks), `contracts/` if present
3. **Tests under review:** paths named in `tasks.md` as contract / catalog-auto tests, plus any files those tasks created
4. Invariants: `.specify/memory/constitution.md` §V, `AGENTS.md`

Ignore prior chat. Git artifacts + test files are the source of truth.

## Your job

Produce a **second opinion** on whether these tests would **fail closed** on the locks they claim to cover — before product implementation makes them green by construction.

## Hard rules

1. **Do not** write product/application implementation. **Do not** rewrite the spec or plan.
2. **Do not** demand 100% unit coverage or tests for human/hybrid catalog rows that cannot be automated honestly.
3. **Do** argue against at least **two** tests or gaps (steelman, then attack): missing lock, tautological assert, testing internals instead of contract, always-green fixture.
4. Prefix finding IDs with **T** (tests). Do not reuse F*/R*/P*.
5. If no contract/catalog-auto tests exist yet, say so in one paragraph and **stop** (review N/A until they land).

## Review lenses

- **Lock fidelity** — Each `contracts/` auto-check hook and each `acceptance.md` `how: auto` row has a test that can fail. **Also (§I):** would greening these tests allow a thinner stand-in than a named lock (“not thinner than…”, dual-axis, real loop)? Flag product Debate if yes.
- **Red-first honesty** — Would these tests fail *before* the implementation exists? Or do they import code that cannot exist yet / mock away the behavior?
- **Wrong-thing tests** — Asserting status 200 without `mode`/`parent_artifact_id`/`type=clarify` is noise.
- **Scope** — Human/hybrid catalog rows must not be faked as auto (e.g. “prose is specific”).
- **SNR** — Duplicate tests, brittle snapshots, no fixture for the negative path.

## Output format (strict)

### A. Executive verdict
One of: `Approve tests as-is` | `Approve tests with minor edits` | `Do not implement against these tests yet`  
3–5 sentences why.

### B. Findings table

| ID | Severity | Lens | Locus | Finding | Suggested resolution |
|----|----------|------|-------|---------|----------------------|
| T1 | Blocker / Debate / Later / Nit | … | file or catalog id | … | … |

For every **Debate**, add a tag in Suggested resolution or Finding: **`product`** (changes a shall / user-visible behavior / spend) or **`process`** (SNR, wording, duplicate coverage, test shape without changing product shall). Constitution §F: only **product** Debates + Blockers require human adjudication; **process** Debates may be agent-adjudicated like Nit/Later.

Minimum **4** findings if tests exist. At least **1** Debate. At least **1** strength.

### C. Adversarial positions (required)

1. **Position: these tests would go green while a spec lock fails** — strongest case  
2. **Position: these tests over-constrain implementation / test the wrong layer** — strongest case  

Each ≤150 words + “what would have to be true for the test suite to be right anyway.”

### D. Catalog / contract coverage map

| Catalog id or contract hook | Test file / name | Can fail today? | Gap |
|-----------------------------|------------------|-----------------|-----|
| … | … | yes/no | … |

### E. Edit list
Max 8 bullets: test file + one-line change.

### F. Questions for the human (max 3)
Only if a **product** Debate or Blocker changes whether implement may start.

## Tone

Direct. Skeptical of tautological tests. No filler praise.

## After review

Deposit `FEATURE_DIR/TEST_REVIEW.md`. Human adjudicates **T-*** Blockers and **product**-tagged Debates; Nit/Later and **process**-tagged Debates may be **agent-adjudicated** (constitution §F). Implementer must not start matching product code until Blockers and product Debates are resolved or explicitly accepted.
