# Review packet: combined review of the Wave 1.5 reliability work, the rules inventory and the approach amendment

One cross-family pass over three pieces of work the architect led with the governor between 2026-10-20 and 2026-10-22, before any of it merges. This packet replaces the 2026-10-20 single-amendment review, whose reviewer stalled on a web request and never deposited (register action A5).

## Meta

| Field | Value |
|-------|-------|
| Packet id | 2026-10-20-reliability-rules-first-review |
| Status | open (round 1, 2026-10-22) |
| Gate | Before pull requests #42, #44 and #45 merge; one pass, a second only for a blocker |
| Under review | Pull request #42 (approach amendment, branch `wo/wo-20261020-wave15-reliability-rules-first`), #44 (reliability report, register and decisions, branch `wo/wo-20261020-wave15-reliability-investigation`), #45 (rules inventory, branch `wo/wo-20261020-wave15-rules-inventory`). Your review branch merges all three onto `main` (e911e34); they touch no common file |
| Orders | `wo-20261020-wave15-reliability-rules-first`, `wo-20261020-wave15-reliability-investigation`, `wo-20261020-wave15-rules-inventory` |
| Agent mode | spawned reviewer, background |
| Reviewer | GPT-5.6 Sol (a different model family from the author, Claude Opus 5.5) |
| Appetite | 45 minutes. Hard stop at 60 minutes. Commit and push a skeleton report (headings only) within your first 10 minutes, and push again after each question you finish, so progress shows in git |

## Why this review exists

The governor approved the Wave 1.5 implementation approach on 2026-10-19. On 2026-10-20 he put reliability and Wave 1's rules first (decision `wave15-reliability-rules-first`). The architect then ran a reliability investigation with him (11 incidents, decisions D1 to D24, actions A1 to A14), had a worker inventory every Wave 1 rule, and folded the decisions into the approach note (its section 11 and in-place edits). Nothing is built; these are design records. A second model family checks them before they merge.

## Read first

1. The register: `notes/wave1.5/2026-10-reliability-register.md` (decisions D1 to D24, actions, incident coverage).
2. The locks behind them: `bus/decisions/wave15-reliability-rules-first/`, `wave15-unattended-host/`, `wave15-runner-and-chunks/`, `wave15-task-modes/`, `wave15-permission-policy/`, `wave15-batch-environment/` (each `request.yaml` and `lock.yaml`).
3. The report: `notes/wave1.5/2026-10-reliability-investigation.md`.
4. The approach note: `git diff e911e34 -- notes/wave1.5/2026-10-implementation-approach.md`, then the note in full (sections 2.4, 2.7, 3, 4, Layers 0 to 2 and 5, section 5 row 13, sections 7, 10 and 11).
5. The rules inventory: `notes/wave1.5/2026-10-rules-inventory.md`, with `notes/wave1.5/sources/github-settings/` (the live settings it was checked against). Read its summary and recommendations in full; sample the rule table rather than checking every row.
6. Only where cited: `notes/wave1.5/sources/README.md`, `notes/retro/2026-10-harness-changes.md`, `notes/retro/2026-10-wave1-agenda.md`, `AGENTS.md`, `.specify/memory/constitution.md`.

**Do not fetch anything from the web.** A web request from an agent like you waits on an approval prompt nobody sees; that is what stalled the earlier reviewer. Read only files inside your worktree. If a claim needs an outside source (vendor documentation, GitHub's limits), mark it "unverified, outside source" and move on.

## Job

Answer these, each with evidence (file and section):

1. **Fidelity to the governor's decisions.** Does each register decision match its lock, and does the approach note record those decisions, no more and no less? Name anything the records present as decided that no lock supports, or anything locked that the note misses. Section 11's table of where each decision lands is the place to start.
2. **Consistency across the three.** Does any text in the approach note, the report or the inventory still contradict a later decision? Known risk areas: the cause of the 2026-10-19 freezes (web requests, not reads outside the worktree), Copilot (now from day one behind `AI_ENV`, the earlier "only if Cursor fails" trim reversed), the watcher (daytime in the codespace; the scheduled GitHub workflow long term), the batch environment (decided in Layer 1), and the 240-minute codespace (done).
3. **Evidence behind the reliability decisions.** For each incident in the report's section 3, does the stated cause follow from the evidence given, and does the closing decision in the register address that cause? Check the permission trials' table (report section 11.1) against the decisions D17 to D20 drawn from it. Say where a conclusion goes further than its evidence.
4. **Failable outcomes.** Can each "done when" in the register's actions, and in Layers 0 to 2 of the approach note, fail? Name anything with no way to tell whether it was done.
5. **The rules inventory.** On the rows you sample: is each rule's enforcement point and bypass stated accurately against the live settings files and the cited source? Is each keep, rewrite or drop recommendation backed by its stated reason? Does the inventory miss any rule stated in `AGENTS.md` or the constitution?
6. **Cost.** The approach note's section 11 says three decisions add unsized work to tranche 1. Is anything else in D2 to D24 likely to add work that the note does not flag?

Do not re-argue the governor's decisions or the approved approach. Severity per finding: blocker (merging would misrecord a governor decision, or a decision rests on evidence that contradicts it), major (a contradiction or gap the next step would trip on), minor (wording). Give a concrete fix for each, and say which pull request it belongs to.

## Deposit

- Write `notes/wave1.5/2026-10-reliability-rules-first-review.md` in your worktree. Structure: summary (verdict in three lines: accept, or changes needed), findings (numbered, each with severity, pull request, file and section, evidence, fix), what you checked and found fine.
- Write one verdict per order, following the shape of `bus/orders/wo-20261019-wave15-implementation-approach/verdict-01.yaml`:
  - `bus/orders/wo-20261020-wave15-reliability-rules-first/verdict-01.yaml` (pull request #42)
  - `bus/orders/wo-20261020-wave15-reliability-investigation/verdict-01.yaml` (pull request #44)
  - `bus/orders/wo-20261020-wave15-rules-inventory/verdict-01.yaml` (pull request #45)
  Each: `decision: accept` if that pull request has no blocker or major finding, otherwise `decision: revise`; `reviewer_model: gpt-5.6-sol`, `reviewer_family: openai`; `inputs` listing every file you read, each at the commit sha named in your spawn message; `refs` naming this packet and your report.
- Plain language: the governor may read the report. Avoid internal jargon (packet, worktree, owned paths).

## Worktree and git

- Your worktree: `/workspaces/2026-software-lab/.worktree-home/.cursor/worktrees/wave15-combined-review`, on branch `review/wo-20261020-wave15-combined-r1`. It is already created. Never use the primary checkout at `/workspaces/2026-software-lab` itself.
- Every shell command starts with `cd /workspaces/2026-software-lab/.worktree-home/.cursor/worktrees/wave15-combined-review &&`. Before each commit, check that `git branch --show-current` prints the review branch; if it prints anything else, stop and report.
- Use file tools with absolute paths under your worktree for reading and writing.
- Never pass `required_permissions`. Never combine heredoc, echo or redirection with git in one command.
- Commit and push to your review branch only (`git push -u origin review/wo-20261020-wave15-combined-r1`). The architect copies the report and verdicts onto the pull request branches. If the push is refused, leave the commit in place and report.

## May edit

- `notes/wave1.5/2026-10-reliability-rules-first-review.md` (in your worktree)
- The three `verdict-01.yaml` files named above (in your worktree)

## Forbidden

- Every other file.
- Product and application code (`apps/`, `modules/`), `deploy/secrets/`, GitHub settings.
- Installing, running or signing up for anything; starting any Wave 1.5 work.
- Web requests of any kind, and reading files outside your worktree.

## Definition of done

- [ ] Report and three verdicts committed (and pushed if allowed).
- [ ] All six questions answered, each with evidence or "found fine".
- [ ] Stop. Do not ask the governor anything; the architect presents the result.

## Stop and report if

- You find a secret value or personal data (report the file and line, never the value).
