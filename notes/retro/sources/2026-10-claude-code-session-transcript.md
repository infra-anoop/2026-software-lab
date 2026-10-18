What is the conceptual difference between speckit workflows and github agentic workflows

Ran 28 commands, created 3 files, shared files
I’ve built this as a kit you can drop into a repo: factory-design-kit.zip contains a .factory/ folder. The Python controller is tested; the two workflow files are not yet run. I also looked at Spec Kit’s source code, which settles the earlier Cursor question: when a workflow step runs, Spec Kit calls cursor-agent -p --trust --approve-mcps --force and passes the step’s model. So Cursor works for unattended steps once its command-line agent is installed. --force auto-approves the agent’s actions, so run workflows inside your Codespace.

How your six steps map to the tools:

Your step	Tool	Who decides
1. Problem statement	/speckit.specify, typed in Cursor	You
2. Probing questions	/speckit.clarify, which asks up to five targeted questions per run and writes your answers into spec.md; repeat it	You and the agent, in conversation
3. Critical spec review	factory-review-loop workflow, stage spec	Code
4. Functional spec, architecture, execution plan	speckit.plan (architecture and design files), speckit.tasks (execution plan), speckit.analyze (consistency check)	Code sequences, agents write
5–6. Plan review, loop, escalate	factory-review-loop workflow, stage plan	Code
Steps 1–2 stay interactive on purpose. They are a conversation with you, and a headless step can’t ask you questions.

A: Getting the workflow. design.yml runs your steps 3–6 in order. review-loop.yml is a reusable sub-workflow called once for the spec and once for the plan. Each round of the loop:

Prepare (code): starts the round and writes a context file listing the artifacts, last round’s open findings and the reviser’s responses.
Review (agents, in parallel): one reviewer per role.
Check (code): validates every review file against the Pydantic models.
Repair (agent, only if needed): one attempt to fix invalid files, given the exact errors.
Converge (code): strict check that fails the run if files are still invalid, then decides: converged, continue or escalate.
Revise (agent, only if continuing): addresses the findings and writes a structured report.
The round cap lives in config.json (max_rounds: 3). If the loop doesn’t converge, code writes escalation.md and an approval gate shows it to you.

B: Seeding reviewer roles. Each role is a markdown brief in .factory/roles/. I included spec-critic, cost, competition, architecture and open-source. Each brief has four parts, and the last two do the most to cut extra rounds:

what to focus on;
what to check;
what not to flag, so reviewers don’t wander outside their lane;
calibration examples of blocker, major and minor.
_shared.md holds rules for every reviewer: evidence required, keep finding ids stable across rounds, don’t re-raise a rejected finding without new evidence. config.json lists which roles review each stage, with a model per role. Adding a role means writing one markdown file and adding one config line.

C: The packet format, in packets.py.

ReviewVerdict: what each reviewer returns, a list of findings plus the ids now resolved. Each Finding has a stable id, severity, confidence from 0 to 100, file, section, issue and recommendation. A validator rejects ids that don’t belong to the reviewer, and an “approve” verdict that still contains a blocker.
RevisionReport: the reviser marks each finding fixed, rejected or needs-human, with a reason.
LoopState: the only object the workflow branches on; produced by code, never by an agent.
Convergence is computed in code, not taken from the reviewers’ approve/revise vote. A round converges when no blocker or major finding with confidence of 80 or more is still open. A needs-human response sends the issue to you immediately instead of using up rounds.

D: Wiring Pydantic into the workflow. Spec Kit shell steps have an output_format: json option. The script prints JSON, and the next steps read its fields: the loop condition is {{ steps.converge.output.data.continue_loop }}. A non-zero exit code fails the step, so the plain check always exits 0 and lets the repair step run, while the strict check exits 1 if files are still invalid. A failed run can be picked up again with specify workflow resume. factory.py schemas generates JSON Schema files from the same models for agents to write against, so there is one source of truth. The only workflow value interpolated into shell commands is stage, which is restricted to spec or plan; Spec Kit’s docs warn that agent output put into shell commands can inject commands.

What’s tested and what isn’t:

Tested: factory.py through simulated rounds. It catches an invalid review file, converges on round two, and escalates at the round cap with a correct escalation.md.
Not run: the workflow YAML. I wrote it from Spec Kit’s docs and engine source. Three expression details may need adjusting:
item.model inside the parallel reviewer step;
whether the parallel step can see the round number from the prepare step;
whether the result of the last round is still visible after the loop ends.
Run specify workflow validate and a trial with one cheap reviewer before relying on it.

Factory design kit
ZIP 

Review loop
YML 

Packets
PY 

Factory
PY 
One other frustrating thing I am finding is agents flaky behavior in procedural matters. It is one thing to do things buggy or sub optimal. Those things can be caught by test or review. But it is quite another to say - I am working on x - and then forget to work. Or waiting for CI to finish, but then don’t pick up the ownership of post CI. That breaks the workflow.  Any insights on how that can be fixed or tightened

Searched the web
These aren’t reasoning failures that better prompting will fix; they’re control-flow failures. An agent has no clock and nothing running in the background. Its turn ends as soon as it writes a message without calling a tool. So “I’m working on X” is just a sentence it typed before stopping. “I’ll wait for CI” is the end of its turn, with nothing to wake it when CI finishes. Taking over after CI depends on the agent remembering, and an agent that has stopped remembers nothing. The fix follows your 2d principle: take every procedural duty away from the agent and give it to something that persists. That means waiting, follow-up, ownership, and deciding whether a task is done.

Failure	Why it happens	Fix	Where it lives
Announces work, then stops	Its turn ended on a sentence	A code check that the expected output exists; Claude Code’s Stop hook (below)	Workflow step, agent hook
Waits for CI, never comes back	Nothing wakes it up	The workflow engine waits, not the agent	Workflow shell step
Doesn’t take over after CI	Ownership depends on its memory	The next workflow step owns it by design and is handed the CI result	Workflow
Says “done” when it isn’t	Its own report is trusted	Validated status file plus tests run by code	factory.py
Hangs or wanders	No limit on a run	A timeout on every step; small tasks	Workflow
Loses track mid-task	Progress lives only in its context	A progress file on disk	Ledger
1. Agents never wait; the engine does. A shell step blocks until CI finishes, and the next agent step starts only if something needs fixing. Note the underscores in the step IDs: a hyphen inside {{ }} may be read as a minus sign.

yaml
- id: wait_ci
  type: shell
  run: "python .factory/bin/factory.py ci-wait"   # wraps `gh pr checks --watch`, saves failed logs
  output_format: json
  timeout: 3600
- id: fix_ci
  type: if
  condition: "{{ steps.wait_ci.output.data.failed }}"
  then:
    - id: ci_fixer
      type: prompt
      prompt: "CI failed. Read .factory/ci/failed-logs.txt, fix, commit, push, then write your status JSON."
Wrap these two in a do-while with a cap and CI repair works like the review loop. No agent has to remember anything. The ci-wait command isn’t in your kit yet; I’d add it to factory.py alongside prepare and check.

2. Done means checked, not claimed. After every agent step, a code step checks the step’s expected results: the output file exists and validates, a new commit exists, tests pass. If the agent narrates and exits, the check fails and the step retries with the reason fed back. The status format you already have helps here. Its allowed values are DONE, DONE_WITH_CONCERNS, NEEDS_CONTEXT and BLOCKED, with no “in progress”. So “I’m working on it” is literally an invalid output.

3. Inside a single agent run, use a Stop hook. Claude Code runs a Stop hook script every time the agent finishes a turn. If the script prints a “block” decision with a reason, the agent can’t stop and receives that reason as its next instruction. That’s how you get “you can’t stop until tests pass.” Two catches:

Check the stop_hook_active flag, which Claude Code sets when the agent is already continuing because of the hook. Otherwise you can create an endless loop.
Exit code 1 does not block; only exit code 2, or the JSON block decision, does.
I haven’t verified an equivalent for Cursor’s command-line agent. The workflow check in point 2 works with any agent, so make that your main guarantee and treat the hook as an extra layer.

4. For waits measured in hours, trigger on events. A workflow can wait minutes for CI; it shouldn’t hold a run open for a slow human review. Let gh-aw start a fresh agent run when the event happens (CI finished, a review posted), with the PR as its context. “Who owns post-CI” then becomes “what runs when CI completes”, which a machine guarantees.

5. Keep agent runs short and single-purpose. The longer a run, the more it drifts into narration. One task per run, a timeout on each step, and progress recorded in the ledger file rather than in the agent’s context. Anthropic’s long-running harness design and the Superpowers ledger both make this same move.

One habit change. Most of this flakiness shows up in interactive chat, because there the agent is your orchestrator by default. A simple rule fixes it: anything involving a wait or a handoff goes into a workflow, and chat is for thinking and steering.

