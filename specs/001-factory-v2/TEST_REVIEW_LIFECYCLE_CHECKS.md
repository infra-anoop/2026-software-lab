# Test review — lifecycle check kinds

## A. Executive verdict

**Do not implement against these tests yet.** Round 1 reproduces 7 assertion failures
and 21 passes, so the new tests are honestly red against the current lifecycle code.
They pin ordinary catalog rows, wrong status contexts, wrong override ids, and unknown
ids well. However, they do not pin catalog-first collisions or either source ruling, and
the existing gate cases do not prove that linkage cannot satisfy a registered gate.

## B. Findings

| ID | Severity | Lens | Locus | Finding | Suggested resolution |
|----|----------|------|-------|---------|----------------------|
| T-LC1 | Blocker | Lock fidelity | `test_lifecycle.py` check-kind fixtures | **Root-cause class:** the fixture fixes row ids as non-gates and places its catalog on `main`, so classification precedence and source boundaries are unobservable. **Consequence:** lifecycle can read the head registry, read only `main` catalogs, or classify a gate/row collision as a gate while these tests pass; that can falsely accept or withhold acceptance for work-order authors. **Likelihood:** high, because each is a natural implementation shortcut and the helper currently encourages it. | Add one non-parametrized classification-matrix regression covering: collision is catalog-first; a head-only registry id is unknown under the installed registry; a head-only catalog row is recognized; and a registered gate with green linkage but no own status remains `in_review`. This is the smallest sufficient root-cause fix and is red on base through the first three rows. |
| T-LC2 | Debate (`process`) | SNR / regression strength | `CHECK_CASES["status-missing"]` | The existing gate-id cases are not a complete regression guard: none combines a missing `factory/<gate-id>` status with green `factory/catalog-test-linkage`, so an implementation may let linkage vouch for a registered gate. The strongest defense is that this isolated case is already green on base and cannot honestly be introduced as a standalone red-first test. | Include this case in the single red classification matrix requested by T-LC1, rather than adding a standalone always-green test or one test per symptom. |
| T-LC3 | Nit | Red-first honesty | focused lifecycle suite | **Strength:** all seven new failures are state assertions at the intended missing behavior; there are no collection/import errors or mocks that bypass derivation. | Keep the real `derive_snapshot` seam and state-level assertions. |
| T-LC4 | Nit | Wrong-thing resistance | catalog status and override cases | **Strength:** the suite explicitly rejects a row's own green status, an override naming the row, and a green status for an unknown id; these prevent three direct constant-answer implementations. | Keep these negative cases when adding the source/precedence matrix. |

## C. Adversarial positions

1. **Position: these tests would go green while a spec lock fails.** An implementation
   can scan catalogs only on `main`, classify gate ids from the PR head's `gates.yaml`,
   and prefer gate classification over catalog classification. The current helper puts
   `demo.adds` on both refs, asserts it is not installed as a gate, and never mutates the
   head registry, so none of those violations is observable. It can also accept green
   linkage for registered gates because no gate case supplies that status. The suite
   would be right anyway only if registry and catalog sources plus collision precedence
   were enforced by another immutable boundary used by lifecycle; no such boundary is
   under test.

2. **Position: these tests over-constrain implementation / test the wrong layer.** The
   helper imports the installed registry and constructs a full git/PR lifecycle for each
   state assertion, coupling a narrow check-classification contract to registry layout
   and relatively expensive fixtures. The row-override negative also posts a status that
   the trusted job does not produce. The suite would be right anyway if these details
   are treated only as adversarial inputs and lifecycle remains free to factor catalog
   discovery and classification behind any internal API.

## D. Catalog / contract coverage map

| Catalog id or contract hook | Test file / name | Can fail today? | Gap |
|-----------------------------|------------------|-----------------|-----|
| T105 registered gate needs own status | `test_accepted_needs_verdict_and_full_required_check_set` | yes | No green-linkage/missing-own-status combination |
| Catalog row uses linkage status | `test_catalog_row_is_satisfied_by_the_catalog_linkage_status` | yes | Catalog exists on both `main` and head |
| Row status cannot satisfy row | `test_catalog_row_needs_a_green_linkage_status_not_its_own` | yes | None for ordinary non-collision row |
| Override names linkage gate | `test_catalog_row_counts_an_override_of_the_linkage_gate_only` | yes | Negative uses a synthetic row status |
| Unknown ids fail closed | `test_an_id_that_is_neither_a_gate_nor_a_catalog_row_fails_closed` | yes | Does not distinguish installed registry from head registry |
| Catalog-first gate/row collision | none | no | Locked amendment-01 ruling 1 is absent |
| Installed registry source | none | no | Locked amendment-01 ruling 2 is absent and can be red on base |
| PR-head catalog source | none | no | Locked amendment-01 ruling 3 is absent and can be red on base |

## E. Edit list

- `scripts/factory/tests/unit/test_lifecycle.py`: add one classification-matrix test with collision, registry-source, catalog-source, and gate/linkage rows.
- `scripts/factory/tests/unit/test_lifecycle.py`: provide fixture helpers that can add an acceptance row only on the work branch and mutate only the head registry.
- `scripts/factory/tests/unit/test_lifecycle.py`: retain the current ordinary-row status and override negatives unchanged.

## F. Questions for the human

None. The missing behaviors are already locked by amendment-01; no new product choice is
required.

## Triage (orchestrator, round 1, 2026-10-07)

Reviewer text above is unchanged.

| Finding | Decision | Change |
|---------|----------|--------|
| T-LC1 (Blocker) | **Fix as suggested.** | One classification-matrix test in `test_lifecycle.py` with four rows: an id that is both a gate and a catalog row is catalog-first (green linkage, no own status: accepted); a gate id present only in the head's `gates.yaml` is unknown (stays `in_review`); a catalog row present only in the head's `acceptance.md` is recognised (green linkage: accepted); a registered gate with green linkage and no own status stays `in_review`. Fixture helpers may add a row only on the work branch and change only the head registry. Red on base through its first three rows |
| T-LC2 (Debate, process) | **Fold into T-LC1's matrix** (its fourth row), as suggested. | — |
| T-LC3, T-LC4 (Nit, strength) | Keep | — |

Round 2 is the reviewer's check of this one change.
