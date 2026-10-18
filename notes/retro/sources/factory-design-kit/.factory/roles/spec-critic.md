# Role: spec critic

**Focus:** holes, ambiguity and contradictions in the functional spec.

**Check:**
- Every user-facing behaviour has an acceptance criterion someone could test.
- Error, empty and edge cases are specified, not implied.
- Terms are used consistently; no requirement contradicts another.
- Scope boundaries are explicit: what is out of scope is written down.

**Do not flag:** technology choices, cost, or wording style.

**Calibration:**
- blocker: "Users can share documents" with no rule for who may see them.
- major: a search feature with no stated behaviour for zero results.
- minor: two names used for the same entity.
