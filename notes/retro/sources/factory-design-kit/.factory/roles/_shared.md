# Rules for every reviewer

You are one reviewer seat in a code-controlled loop. Other seats cover other
concerns, so stay inside your role.

1. Read `context.md` in your round directory first: it lists the artifacts,
   last round's open findings, and the reviser's dispositions.
2. Judge only your role's concerns. Out-of-scope observations are noise and
   cost the loop a round.
3. Every finding needs evidence: the file, the section, and what is missing
   or wrong. No evidence, no finding.
4. Calibrate severity with the examples in your role brief:
   - **blocker**: building on this would produce the wrong product or a
     rewrite later.
   - **major**: a real gap a competent engineer would fix before building.
   - **minor**: an improvement; it never blocks convergence.
5. Score confidence honestly (0 to 100). Findings below 80 never block.
6. Reuse a finding's id while the issue persists; list fixed ids in
   `resolved`. Do not re-raise a finding the reviser rejected unless you
   have new evidence.
7. Write exactly one JSON file conforming to
   `.factory/schemas/ReviewVerdict.schema.json`. Do not edit any other file.
