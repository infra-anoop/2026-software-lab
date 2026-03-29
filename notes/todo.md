My learning roadmap
Learn about Nix. its purpose and how to bring it in
Learn Railway or fly.io (railway.toml is modern CI/CD )
Supabase
Learn LlamaIndex
Learn and use Obsedian 
Container registry
Subfolders and folder structure
Deployment 
Github actions ( CI/CD) 
pinecone vector db
The "AI Personalization" File: Project config. curosrrules


Feb 17, 2026

Logfire: use LOGFIRE_TOKEN from environment (e.g. Codespaces secrets); .logfire dir not used and can be deleted.
find a CLI way to deploy to railway. That way parameters can be passed from repository
create a script like "go project a" and that should do things like uv sync etc.
Is Railway.toml still required
Flake other targets seem to be hard coded for research-auditor.  What is the general way to fix it
get in the habit of feature branch development and merge to main and publish from main method. Talk to LLM to get comfortable
ship-registry to trigger only after verify source completes
verify source should run not only on push to main but also for any v* tags
Revisit workflows.  these 4 workflows didn't trigger as expected. Gemini thought that an alternative approach where there is only one master workflow and conditional execution is controlled by key words jobs, needs, and uses.
hookup http framework to play with the app by giving different topics

March 28, 2026
CI/CD: Add preview deployment (separate Railway target + workflow wiring). Same v* tag trigger; route preview vs production using branch context and/or whether the tagged commit is on main—see comment block in `.github/workflows/ci-cd-pipeline.yml`.
1: Develop a new secerets architecture. To avoid secrets sprawl. Explore 1password API or Github workflow.  For now the secrets are in Railway
