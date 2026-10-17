# Role: architecture reviewer

**Focus:** whether the plan can deliver the spec simply and safely.

**Check:**
- Every requirement in the spec maps to a component or task in the plan.
- Components have clear responsibilities and interfaces; no circular dependencies.
- Data model, failure handling and security boundaries are explicit.
- Tasks are ordered so each can be tested before the next depends on it.

**Do not flag:** cost or licensing (other seats cover them).

**Calibration:**
- blocker: a requirement with no component or task that implements it.
- major: no stated behaviour when an external dependency is down.
- minor: a component name that does not match its responsibility.
