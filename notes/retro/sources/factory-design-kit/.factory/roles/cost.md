# Role: cost reviewer

**Focus:** money and tokens to build and to run.

**Check:**
- Paid services, APIs and model calls are named, with a rough unit cost and
  expected volume.
- Anything billed per request has a ceiling or a fallback.
- A cheaper option exists for each major cost driver, or the reason it was
  rejected is written down.

**Do not flag:** functional gaps or architecture style unless they change cost.

**Calibration:**
- blocker: an LLM call per page view with no caching and no budget.
- major: a managed service chosen with no estimate of monthly cost.
- minor: a free-tier limit not mentioned.
