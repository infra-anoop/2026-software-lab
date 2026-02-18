Research-Auditor App — Structural Review
1. Organization score: 6.5 / 10
What works well
Clear split: app/ (agents, db, orchestrator, entrypoints), tests/ (unit vs integration), scripts/ for one-off/legacy.
Protocol-based persistence (RunRepo) with NullRepo and SupabaseRepo is a good abstraction.
Pydantic models in app/agents/models.py define agent outputs in one place.
Single entrypoints: CLI = app.main, HTTP = app.entrypoints.http, and flake/railway point at them consistently.
What holds the score back
Two persistence paths (Supabase in main.py vs runs/turns in the orchestrator) and the CLI only using one of them.
Stale or misleading references (comment in http.py, requirements.txt vs pyproject.toml, pyproject name vs folder name).
No app/__init__.py (optional but usual for a top-level app package).
HTTP entrypoint is health-only; no API that runs the workflow, so “deployment works” = health check only.
So structure is reasonable and navigable, but wiring between entrypoints, workflow, and persistence is inconsistent and some cruft remains.
2. Bugs and issues
B1. CLI skips run/turn persistence
main.py calls app.ainvoke(initial_input) and never calls run_workflow().
run_workflow() is the only place that sets run_id/step and calls create_run, append_turn, finalize_run.
So when you run the app from the CLI, the runs and turns tables are never written; only save_to_supabase() (research_audits) runs. The orchestrator’s persistence is effectively dead on the main entrypoint.
B2. Duplicate Supabase usage
main.py builds its own supabase client and writes to research_audits.
The orchestrator uses RunRepo (SupabaseRepo) for runs and turns.
Two separate Supabase clients and two persistence patterns for one app; if one is “correct,” the other is either redundant or the intended design is unclear.
B3. Stale comment in HTTP entrypoint
app/entrypoints/http.py line 1: # apps/research-auditor/app/server.py — file is actually app/entrypoints/http.py and there is no server.py. Misleading for anyone reading the file.
B4. Unit test imports the wrong “app”
tests/unit/test_app_smoke.py does import app and asserts app is not None.
There is no app/__init__.py, so this imports the package app. The LangGraph workflow is app in app/orchestrator/run.py. So the test only checks that the package exists, not that the workflow or any real entrypoint is importable. Name collision between package app and variable app (the graph) is confusing.
B5. requirements.txt vs pyproject.toml
requirements.txt exists with a different dependency set (e.g. pip-audit, safety, httpx, pyyaml, psutil, unversioned pydantic-ai).
Run path is uv + pyproject.toml (and flake/container use that). So requirements.txt is either legacy or for a different path; it can confuse and could drift. Old archive docs already flag this.
B6. Harsh agent import-time behavior
researcher.py and critic.py call sys.exit(1) if OPENAI_API_KEY is missing at import time.
Any code that imports the agents (e.g. tests, tooling, or a future path that sets env later) will exit the process. Makes testing or optional “no-LLM” modes harder.
3. Recommended improvements
R1. Unify CLI with run/turn persistence
Have main.py call run_workflow(initial_input) instead of app.ainvoke(initial_input) when you want runs/turns recorded (and keep using the same initial_input shape). That way one code path uses both research_audits and runs/turns consistently. If you intentionally want “CLI without run/turn persistence,” document that and consider a flag or env to choose.
R2. Single Supabase story
Prefer one place that creates the Supabase client and one persistence story: either (a) main gets the client from a small shared module and uses it for research_audits while the orchestrator uses the same (or a repo that uses it), or (b) move research_audits write into the orchestrator/repo layer so all persistence goes through the same abstraction. Reduces duplication and confusion.
R3. Name the package and the graph explicitly
In app/orchestrator/run.py, export the compiled graph under a clear name, e.g. workflow_app or graph, and have main.py import that. Avoid reusing the name app for the graph so it’s obvious that import app is the package and the other is the workflow.
R4. Add app/__init__.py
Empty or with a short docstring; optionally export a small public API (e.g. run_workflow, workflow_app). Makes app clearly a package and can simplify tests (e.g. from app.orchestrator.run import workflow_app).
R5. Fix or remove requirements.txt
If everything runs via uv + pyproject: delete requirements.txt or add a one-line comment that dependencies are in pyproject.toml and this file is legacy/unused. If something (e.g. Railway or a script) still uses it, align it with pyproject or migrate that path to uv and then remove.
R6. Align pyproject name with folder
pyproject.toml has name = "research-auditor-industrial"; directory and docs say “research-auditor.” Either rename the project to research-auditor or document why the suffix is intentional (e.g. internal product name).
R7. Centralize env and API key check
Move load_dotenv() to a single place (e.g. main.py or a small app/config.py) and optionally a single “require OPENAI_API_KEY or exit” helper used by the CLI/HTTP entrypoints, rather than each agent exiting at import time. Keeps agents importable for tests and other entrypoints.
R8. Clarify deployment contract
Document that the current deployment image runs app.entrypoints.http (health + static message only) and that there is no HTTP API to run the workflow yet. If the next step is to add a POST endpoint that calls run_workflow, say so in a short “Deployment / API” note in the app README or in http.py.
R9. Scripts vs entrypoints
scripts/railway_smoke_server.py is marked legacy and duplicates the “listen on PORT, 0.0.0.0” idea of app/entrypoints/http. Consider removing it once you’re confident the real HTTP entrypoint is the only one used in CI/Railway, or move any unique behavior into the main HTTP entrypoint and delete the script.
R10. Optional: typing for save_to_supabase
save_to_supabase(final_state) takes the raw state dict. Adding a type hint (e.g. AgentState or a small “FinalState” type) would make the contract clear and catch misuse.
Summary
Score: 6.5/10 — structure is decent but persistence and entrypoint wiring are inconsistent and some cruft remains.
Bugs: CLI doesn’t use run/turn persistence (B1), duplicate Supabase usage (B2), stale comment (B3), unit test imports package not workflow (B4), conflicting requirements (B5), exit-on-missing-key at import (B6).
Improvements: Unify CLI with run_workflow (R1), single Supabase story (R2), clear naming for graph vs package (R3), add app/__init__.py (R4), fix/remove requirements.txt (R5), align pyproject name (R6), centralize env/API key (R7), document deployment/API (R8), clean scripts (R9), type save_to_supabase (R10).
We can go through any of these one by one and decide what to change first.