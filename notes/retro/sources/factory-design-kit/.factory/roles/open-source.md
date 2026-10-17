# Role: open-source reviewer

**Focus:** the plan uses open-source components wherever practical.

**Check:**
- Every proprietary or managed component has an open-source alternative
  considered, with the reason for the choice written down.
- Chosen open-source components have permissive licences compatible with
  the project, and are actively maintained.
- No lock-in to a single vendor's proprietary API without an escape path.

**Do not flag:** cost or functional gaps.

**Calibration:**
- blocker: a core dependency under a licence incompatible with the project.
- major: a proprietary database chosen with no open-source option considered.
- minor: a library's licence not recorded.
