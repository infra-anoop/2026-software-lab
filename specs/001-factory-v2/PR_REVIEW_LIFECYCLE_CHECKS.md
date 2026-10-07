# PR review — lifecycle check kinds

## Decision

**Reject.**

## Findings

| ID | Severity | Tag | Location | Issue | Fix |
|----|----------|-----|----------|-------|-----|
| R-LC1 | Blocker | product | `scripts/factory/src/factory/lifecycle/derive.py:48-50,135-138` | A missing PR-head commit becomes an empty catalog set, after which installed gate ids are still judged from GitHub statuses. An accepting order containing only registered gates can therefore become `accepted` even though its head tree is unavailable, contrary to the required fail-closed behavior. | Make readability of the PR-head commit a prerequisite for acceptance whenever checks are evaluated, and add a regression where an accepting gate-only order has green statuses but its head object is absent. |

## Review notes

- `cli/board.py` has exactly the amendment-02 repo pass-through change.
- `orders/lease.py` omits `repo`, but this is harmless: the only affected transition is between `in_review` and `accepted`, and both states count toward `ACTIVE_STATES`.
- `gates/repo/status_test.py` omits `repo`, but this is harmless: `NoGitHub` returns no PRs, so check satisfaction is never evaluated.
- The board contract test is valid: commit `f6c9e38` is red against the old caller, it exercises the real CLI and lifecycle seams, and its assertions specifically require the board to agree with repo-aware derivation.
- The diff is within amendment-02 owned paths, and `tasks.md` is unchanged.
- Required suite: `1065 passed, 7 xfailed`.
- Required gates: `24 passed`; only `pr-links-order` failed because the review branch is not a `wo/<order-id>` branch, the permitted review-branch exception.

## Triage (orchestrator, round 1)

| id | Ruling | Fix required |
|----|--------|--------------|
| R-LC1 (Blocker) | Accept. Tagged product, but it applies the order's own fail-closed rule (amendment-01 ruling 3: rows are judged at the head) and chooses no new behaviour, so the orchestrator adjudicates it. Without the head tree the derivation cannot know whether a registered gate id is a head catalog row, so no order may be accepted from statuses alone | Red regression first: an accepting gate-only order with green statuses whose head commit is absent stays in review. Then make a readable PR-head commit a prerequisite for check satisfaction |
