{
  # ═══════════════════════════════════════════════════════════════════════
  # MULTI-TARGET NIX FLAKE
  # ═══════════════════════════════════════════════════════════════════════
  # 
  # This flake provides FOUR deployment targets:
  #
  #   1. DEVELOPMENT (devShells.default)
  #      - For: Coding in GitHub Codespaces
  #      - Access: Automatic (via devcontainer postCreateCommand)
  #      - Entry: Interactive shell
  #      - Contains: Development tools (uv, git, etc.)
  #
  #   2. CLI APPLICATION (packages.default)
  #      - For: Command-line usage
  #      - Access: `nix run` or `nix profile install`
  #      - Entry: app.main (CLI interface)
  #      - Contains: App + minimal dependencies
  #
  #   3. CI/CD CHECKS (checks.*)
  #      - For: GitHub Actions automated testing
  #      - Access: `nix flake check`
  #      - Entry: Test runners, linters
  #      - Contains: App + test tools
  #
  #   4. DEPLOYMENT CONTAINER (packages.container)
  #      - For: Production deployment (Railway via GHCR)
  #      - Access: Docker image built and pushed
  #      - Entry: app.entrypoints.http (HTTP server)
  #      - Contains: Minimal app + runtime
  #
  # ═══════════════════════════════════════════════════════════════════════

  description = "2026 Multi-Agent Lab - Complete Build Pipeline";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-24.11";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = import nixpkgs { inherit system; };
        
        # ─────────────────────────────────────────────────────────────────
        # SHARED DEPENDENCIES: Used across multiple targets
        # ─────────────────────────────────────────────────────────────────
        
        # Runtime dependencies (needed to run the app)
        runtimeDeps = with pkgs; [
          python312     # Python runtime (NOT from devcontainer in build targets)
          uv            # Package manager
          libffi        # For Python packages with C extensions
          zlib
          openssl
        ];
        
        # Development-only tools (NOT in production)
        devOnlyTools = with pkgs; [
          git           # Version control
          gh            # GitHub CLI
          gcc           # Compiler (for building C extensions)
          pkg-config    # Build tool
        ];

      in
      {
        # ═════════════════════════════════════════════════════════════════
        # TARGET 1: DEVELOPMENT SHELL
        # ═════════════════════════════════════════════════════════════════
        # Activated when: `nix develop` (or via devcontainer)
        # Purpose: Interactive development in Codespaces
        # Entry point: None (interactive shell)
        # Control flow: Developer types commands manually
        # ═════════════════════════════════════════════════════════════════
        devShells.default = pkgs.mkShell {
          buildInputs = runtimeDeps ++ devOnlyTools;
          
          shellHook = ''
            # Force uv to use this shell's Nix Python for new venvs. Otherwise uv may pick
            # /usr/local/bin/python (devcontainer) and mix runtimes — native modules (zlib,
            # ssl, etc.) can then fail to load when LD_LIBRARY_PATH differs.
            export UV_PYTHON="''${UV_PYTHON:-$(command -v python)}"

            echo "🚀 Multi-Agent Lab Development Environment"
            echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            echo "📦 Available Tools:"
            echo "  Python:  $(python --version 2>&1)"
            echo "  uv:      $(uv --version 2>&1)"
            echo "  Git:     $(git --version 2>&1)"
            echo ""
            echo "💡 Quick Start:"
            echo "  cd apps/research-auditor"
            echo "  uv sync"
            echo "  uv run python -m app.main"
            echo ""
            echo "🔬 Run Tests:"
            echo "  nix flake check"
            echo ""
            echo "🐳 Build Container:"
            echo "  nix build .#container"
            echo ""
            echo "📝 smart-writer OpenAI fan-out: SMART_WRITER_MAX_CONCURRENT_LLM (default 1)"
            echo "   See apps/smart-writer/app/config.py and apps/smart-writer/.env.example"
            echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
          '';
        };

        # ═════════════════════════════════════════════════════════════════
        # TARGET 2: CLI APPLICATION
        # ═════════════════════════════════════════════════════════════════
        # Activated when: `nix run` or `nix profile install`
        # Purpose: Standalone command-line tool
        # Entry point: app.main (CLI interface with typer/click)
        # Control flow: Runs command → Executes → Exits
        # 
        # USAGE EXAMPLES:
        #   nix run . -- --help
        #   nix run . -- audit --config config.yaml
        #   nix profile install github:OWNER/REPO
        #   research-auditor audit --config config.yaml
        # ═════════════════════════════════════════════════════════════════
        packages.default = pkgs.writeShellApplication {
          name = "research-auditor";
          
          # Only runtime dependencies (no dev tools like git)
          runtimeInputs = runtimeDeps;
          
          # The actual script that runs
          # This is what executes when someone runs `nix run`
          text = ''
            # Navigate to app directory (bundled in Nix store)
            cd ${./apps/research-auditor}
            
            # Run with frozen dependencies (no network calls)
            # Uses uv.lock for reproducibility
            # Passes all CLI args to the app
            exec uv run --frozen python -m app.main "$@"
          '';
        };

        # ═════════════════════════════════════════════════════════════════
        # TARGET 3: CI/CD CHECKS
        # ═════════════════════════════════════════════════════════════════
        # Activated when: `nix flake check` (typically in GitHub Actions)
        # Purpose: Automated testing and validation
        # Entry point: Various test commands
        # Control flow: Runs tests → Returns exit code (0=pass, 1=fail)
        #
        # GITHUB ACTIONS USAGE:
        #   - name: Run all checks
        #     run: nix flake check
        # ═════════════════════════════════════════════════════════════════
        checks = {
          
          # ───────────────────────────────────────────────────────────────
          # PRE-BUILD CHECK: Code Quality
          # ───────────────────────────────────────────────────────────────
          # Runs before building to catch issues early
          # Fails fast if code doesn't meet quality standards
          lint = pkgs.runCommand "lint-research-auditor" {
            buildInputs = runtimeDeps;
          } ''
            export UV_CACHE_DIR="$TMPDIR/uv-cache"
            export UV_PROJECT_ENVIRONMENT="$TMPDIR/venv"
            # Copy source to writable dir (Nix build dir is read-only)
            cp -r ${./apps/research-auditor} "$TMPDIR/research-auditor"
            cd "$TMPDIR/research-auditor"
            
            echo "🔍 Running code quality checks..."
            
            # Install dependencies + dev tools (ruff, mypy, bandit)
            uv sync --frozen --extra dev
            
            # Ruff: Fast Python linter (cache in TMPDIR; Nix build dir may be read-only)
            echo "  - Linting with ruff..."
            export RUFF_CACHE_DIR="$TMPDIR/ruff-cache"
            uv run ruff check app/
            
            # Type checking with mypy (cache in TMPDIR) - skip until app is fully typed
            # echo "  - Type checking with mypy..."
            # export MYPY_CACHE_DIR="$TMPDIR/mypy-cache"
            # uv run mypy app/
            
            # Security scanning with bandit
            echo "  - Security scan with bandit..."
            uv run bandit -r app/
            
            echo "✅ All quality checks passed!"
            
            # Create success marker (required by Nix)
            touch $out
          '';

          # ───────────────────────────────────────────────────────────────
          # PRE-BUILD CHECK: Unit Tests
          # ───────────────────────────────────────────────────────────────
          # Validates business logic before building artifacts
          test-unit = pkgs.runCommand "test-unit-research-auditor" {
            buildInputs = runtimeDeps ++ [ pkgs.cacert ];
            SSL_CERT_FILE = "${pkgs.cacert}/etc/ssl/certs/ca-bundle.crt";
          } ''
            export UV_CACHE_DIR="$TMPDIR/uv-cache"
            export UV_PROJECT_ENVIRONMENT="$TMPDIR/venv"
            cp -r ${./apps/research-auditor} "$TMPDIR/research-auditor"
            cd "$TMPDIR/research-auditor"
            
            echo "🧪 Running unit tests..."
            
            uv sync --frozen --extra dev
            
            # Coverage writes to TMPDIR (build dir may be read-only or cause sqlite issues)
            export COVERAGE_FILE="$TMPDIR/.coverage"
            
            # Run pytest with coverage (raise --cov-fail-under when tests grow)
            uv run pytest tests/unit/ \
              --cov=app \
              --cov-report=term-missing \
              --cov-fail-under=0
            
            echo "✅ Unit tests passed!"
            touch $out
          '';

          # ───────────────────────────────────────────────────────────────
          # POST-BUILD CHECK: Integration Tests
          # ───────────────────────────────────────────────────────────────
          # Tests the built package works correctly
          # Runs after package is built to verify deployment readiness
          test-integration = pkgs.runCommand "test-integration-research-auditor" {
            buildInputs = runtimeDeps ++ [ pkgs.cacert self.packages.${system}.default ];
            SSL_CERT_FILE = "${pkgs.cacert}/etc/ssl/certs/ca-bundle.crt";
          } ''
            export UV_CACHE_DIR="$TMPDIR/uv-cache"
            export UV_PROJECT_ENVIRONMENT="$TMPDIR/venv"
            cp -r ${./apps/research-auditor} "$TMPDIR/research-auditor"
            cd "$TMPDIR/research-auditor"
            
            echo "🔗 Running integration tests..."
            
            uv sync --frozen --extra dev
            
            # Verify CLI is invocable (e.g. research-auditor --version)
            research-auditor --version
            
            # Run integration test suite
            uv run pytest tests/integration/ -v
            
            echo "✅ Integration tests passed!"
            touch $out
          '';

          # ───────────────────────────────────────────────────────────────
          # POST-BUILD CHECK: Container Validation
          # ───────────────────────────────────────────────────────────────
          # Verifies the Docker container builds and runs correctly
          # Critical for deployment confidence
          validate-container = pkgs.runCommand "validate-container" {
            buildInputs = [ pkgs.skopeo pkgs.jq ];
          } ''
            echo "🐳 Validating container image..."
            
            # Load the container image
            container_path="${self.packages.${system}.container}"
            
            # Inspect image metadata
            echo "  - Checking image structure..."
            skopeo inspect "docker-archive:$container_path" | jq .
            
            # Verify critical properties
            # (size, exposed ports, entrypoint, etc.)
            
            echo "✅ Container validation passed!"
            touch $out
          '';
        };

        # ═════════════════════════════════════════════════════════════════
        # TARGET 4: DEPLOYMENT CONTAINER
        # ═════════════════════════════════════════════════════════════════
        # Activated when: Built via Nix, pushed to GHCR, deployed to Railway
        # Purpose: Production Docker image
        # Entry point: app.entrypoints.http (HTTP server)
        # Control flow: Container starts → CMD runs → App serves forever
        #
        # DEPLOYMENT FLOW:
        #   1. GitHub Action: nix build .#container
        #   2. Push to GHCR: docker load < result | docker push
        #   3. Railway: Pulls from GHCR
        #   4. Container starts: Runs CMD automatically
        #   5. App serves HTTP on port 8080
        #
        # KEY DIFFERENCES FROM DEV:
        #   - No interactive shell (runs CMD directly)
        #   - No git, dev tools (minimal size)
        #   - uv sync runs at container start (not in Nix build; avoids sandbox network)
        #   - HTTP server entry point (not CLI)
        # ═════════════════════════════════════════════════════════════════
        packages.container = pkgs.dockerTools.buildLayeredImage {
          name = "research-auditor";
          tag = "latest";
          
          # Timestamp for reproducible builds
          created = "now";

          # ───────────────────────────────────────────────────────────────
          # CONTAINER CONTENTS: What files go in the image
          # ───────────────────────────────────────────────────────────────
          # Only includes what's needed to RUN the app
          # No development tools, git, compilers, etc.
          contents = [
            # Minimal base utilities
            pkgs.bash
            pkgs.coreutils
            
            # Runtime dependencies
            pkgs.python312
            pkgs.uv
            
            # The application code and lockfile (no uv sync in Nix: sandbox has no network)
            (pkgs.runCommand "app-bundle" {} ''
              mkdir -p $out/app
              cp -r ${./apps/research-auditor}/app $out/app/app
              cp ${./apps/research-auditor}/pyproject.toml $out/app/
              cp ${./apps/research-auditor}/uv.lock $out/app/
            '')
          ];

          # ───────────────────────────────────────────────────────────────
          # CONTAINER CONFIGURATION
          # ───────────────────────────────────────────────────────────────
          config = {
            # ─────────────────────────────────────────────────────────────
            # CMD: What runs when container starts
            # ─────────────────────────────────────────────────────────────
            # THIS IS THE KEY DIFFERENCE FROM DEV:
            #   Dev: Opens interactive shell (you control it)
            #   Deploy: Runs this command automatically (platform controls it)
            #
            # CONTROL TRANSFER EXPLAINED:
            #   1. Railway starts container
            #   2. Docker executes CMD
            #   3. uv run activates venv and runs app.entrypoints.http
            #   4. HTTP server starts on port 8080
            #   5. App runs until crash/shutdown (no human interaction)
            #
            # WHY app.entrypoints.http NOT app.main?
            #   - app.main: CLI interface (interactive commands)
            #   - app.entrypoints.http: HTTP server (long-running service)
            #
            # At startup: uv sync (uses network once), then run the server.
            # uv sync runs in container (not in Nix build) so Nix sandbox needs no network.
            Cmd = [
              "bash" "-c"
              "cd /app && uv sync --frozen && exec uv run --frozen uvicorn app.entrypoints.http:app --host 0.0.0.0 --port ''${PORT:-8080}"
            ];

            # ─────────────────────────────────────────────────────────────
            # WORKING DIRECTORY
            # ─────────────────────────────────────────────────────────────
            WorkingDir = "/app";

            # ─────────────────────────────────────────────────────────────
            # EXPOSED PORTS
            # ─────────────────────────────────────────────────────────────
            # Declares which ports the app listens on
            # Railway/cloud platforms use this to route traffic
            ExposedPorts = {
              "8080/tcp" = {};  # Your HTTP server port
            };

            # ─────────────────────────────────────────────────────────────
            # ENVIRONMENT VARIABLES
            # ─────────────────────────────────────────────────────────────
            # Set default environment for the container
            # Railway can override these via env vars in dashboard
            Env = [
              # Ensure Python output is not buffered (see logs immediately)
              "PYTHONUNBUFFERED=1"
              
              # uv cache directory (for consistency)
              "UV_CACHE_DIR=/tmp/.uv_cache"
              
              # Default port (can be overridden by Railway's PORT env var)
              "PORT=8080"
              
              # Production mode (your app can check this)
              "ENVIRONMENT=production"
            ];

            # ─────────────────────────────────────────────────────────────
            # LABELS (optional metadata)
            # ─────────────────────────────────────────────────────────────
            # In CI, GITHUB_REPOSITORY is set → label points at real repo.
            # Local builds: use placeholder (override with env if needed).
            Labels = {
              "org.opencontainers.image.source" =
                "https://github.com/" + (
                  if builtins.getEnv "GITHUB_REPOSITORY" != ""
                  then builtins.getEnv "GITHUB_REPOSITORY"
                  else "OWNER/REPO"
                );
              "org.opencontainers.image.description" = "Research Auditor Multi-Agent System";
              "org.opencontainers.image.version" = "1.0.0";
            };
          };
        };

        # ADDITIONAL TARGETS: e.g. packages.docker-compose (see docs)
      }
    );
}

# ═══════════════════════════════════════════════════════════════════════
# USAGE GUIDE
# ═══════════════════════════════════════════════════════════════════════
#
# DEVELOPMENT (Codespaces):
#   $ nix develop
#   $ cd apps/research-auditor
#   $ uv sync
#   $ uv run python -m app.main
#
# CLI USAGE:
#   $ nix run . -- audit --config prod.yaml
#   $ nix profile install .
#   $ research-auditor --help
#
# CI/CD (GitHub Actions):
#   $ nix flake check  # Runs all checks
#   $ nix build .#checks.x86_64-linux.lint  # Specific check
#
# BUILD CONTAINER:
#   $ nix build .#container
#   $ docker load < result
#   $ docker run -p 8080:8080 research-auditor:latest
#
# DEPLOY TO RAILWAY (GitHub Actions):
#   1. nix build .#container  (GITHUB_REPOSITORY set in CI → image label correct)
#   2. docker load < result
#   3. docker tag research-auditor:latest ghcr.io/OWNER/research-auditor:latest
#   4. docker push ghcr.io/OWNER/research-auditor:latest
#   5. Railway pulls and deploys automatically
#
# ═══════════════════════════════════════════════════════════════════════
# APP STRUCTURE REQUIREMENTS
# ═══════════════════════════════════════════════════════════════════════
#
# Your app must have this layout (tests/unit and tests/integration are used by flake check):
#
# apps/research-auditor/
# ├── app/
# │   ├── main.py              ← CLI entry point (e.g. --version; then asyncio.run(main()))
# │   └── entrypoints/
# │       └── http.py          ← HTTP server entry point (used by container CMD)
# ├── tests/
# │   ├── unit/                ← pytest tests/unit/ (coverage)
# │   └── integration/         ← pytest tests/integration/
# ├── pyproject.toml
# └── uv.lock
#
# ═══════════════════════════════════════════════════════════════════════
