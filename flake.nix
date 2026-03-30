{
  # ═══════════════════════════════════════════════════════════════════════════
  # MULTI-TARGET NIX FLAKE (parameterized by apps/registry.json)
  # ═══════════════════════════════════════════════════════════════════════════
  #
  # This file used to hard-code a single app (research-auditor). It now reads
  # apps/registry.json (generated from apps/registry.yaml — see
  # scripts/validate_app_registry.py) so every registered application gets the
  # same *kinds* of build artifacts without duplicating Nix logic per app.
  #
  # ───────────────────────────────────────────────────────────────────────────
  # The “four deployment targets” (same mental model as before; see below)
  # ───────────────────────────────────────────────────────────────────────────
  #
  # Historically this flake described FOUR CATEGORIES of output — not “four
  # copies of the world per app.” Those categories are unchanged in meaning:
  #
  #   1. DEVELOPMENT SHELL — devShells.default
  #      - One shared interactive environment for the whole monorepo (uv, Python,
  #        git, compilers, …). You still `cd apps/<id>` for a specific app.
  #      - We do NOT emit one devShell per app: that would fragment tool versions
  #        and duplicate devcontainers; one shell matches how you actually work.
  #
  #   2. CLI APPLICATION — packages.<app-id>  (+ packages.default alias)
  #      - Per app: a small wrapper that runs `uv run … python -m app.main`.
  #      - `nix run .#<id>` picks the app by registry id (e.g. smart-writer).
  #      - `packages.default` points at the first app in the registry (stable
  #        entry for scripts and muscle memory); change registry order if the
  #        “primary” CLI should differ.
  #
  #   3. CI/CD CHECKS — checks.lint-<id>, checks.test-unit-<id>, …
  #      - Per app: ruff + bandit, pytest unit, pytest integration (same stages
  #        as the old single-app flake, now duplicated per registry entry).
  #      - `nix flake check` runs the matrix for every app + validate-container.
  #      - Integration checks still pull in that app’s CLI package so
  #        `<id> --version` exercises the same wrapper as local use.
  #
  #   4. DEPLOYMENT CONTAINER — packages.container-<id>  (+ packages.container)
  #      - Per app with ship.publish_container: a layered Docker image (HTTP
  #        entrypoint: uvicorn app.entrypoints.http:app). Image name comes from
  #        registry oci.image_name (for GHCR / Railway tagging).
  #      - `packages.container` is an alias for the *first* ship app in registry
  #        order (backward-compatible default for `nix build .#container`).
  #      - Nix requires flat `packages.<system>.<name>` values to be derivations;
  #        we cannot nest `packages.apps.<id>` — hence names like
  #        `container-smart-writer` instead of `containers.<id>`.
  #
  # So: you still have four *target types*; types 2–4 *fan out* per application.
  # Type 1 stays singular on purpose.
  #
  # ───────────────────────────────────────────────────────────────────────────
  # Common commands
  # ───────────────────────────────────────────────────────────────────────────
  #   nix develop
  #   nix flake check
  #   nix run .#default -- --help
  #   nix run .#smart-writer -- --help
  #   nix build .#container
  #   nix build .#container-smart-writer
  #
  # ═══════════════════════════════════════════════════════════════════════════

  description = "2026 Multi-Agent Lab - Complete Build Pipeline";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-24.11";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = import nixpkgs { inherit system; };
        lib = pkgs.lib;

        # ─────────────────────────────────────────────────────────────────────
        # Registry (single source of truth for app list + metadata)
        # ─────────────────────────────────────────────────────────────────────
        # JSON is committed next to YAML so Nix can read it with builtins.fromJSON
        # without YAML tooling at eval time. Regenerate after editing YAML:
        #   uv run scripts/validate_app_registry.py --write-json
        registry = builtins.fromJSON (builtins.readFile ./apps/registry.json);
        applications = registry.applications;
        # Subset used for OCI builds (you can turn publish_container off per app).
        shipApps = builtins.filter (a: a.ship.publish_container) applications;

        # ─────────────────────────────────────────────────────────────────────
        # SHARED RUNTIME / DEV INPUTS (reused across CLI, checks, containers)
        # ─────────────────────────────────────────────────────────────────────
        runtimeDeps = with pkgs; [
          python312
          uv
          libffi
          zlib
          openssl
        ];

        devOnlyTools = with pkgs; [
          git
          gh
          gcc
          pkg-config
        ];

        # Resolve apps/<id> from flake root; `app.path` must match registry (validated in YAML).
        appSrc = app: ./. + "/${app.path}";

        # Dev dependencies differ per app: optional-dependencies use --extra dev;
        # dependency-groups use --group dev. Declared in registry JSON as
        # python.uv.sync_dev_args (shell-escaped for use in runCommand scripts).
        uvSyncDevArgsStr = app:
          lib.concatStringsSep " " (map lib.escapeShellArg app.python.uv.sync_dev_args);

        # ═════════════════════════════════════════════════════════════════════
        # TARGET 2 (per app): CLI — writeShellApplication wrapping app.main
        # ═════════════════════════════════════════════════════════════════════
        mkCliPackage = app:
          pkgs.writeShellApplication {
            name = app.id;
            runtimeInputs = runtimeDeps;
            text = ''
              cd ${appSrc app}
              exec uv run --frozen python -m app.main "$@"
            '';
          };

        # Attrset: { research-auditor = <drv>; smart-writer = <drv>; ... }
        cliPackages = lib.listToAttrs (
          map (app: lib.nameValuePair app.id (mkCliPackage app)) applications
        );

        # ═════════════════════════════════════════════════════════════════════
        # TARGET 4 (per app): CONTAINER — dockerTools.buildLayeredImage
        # ═════════════════════════════════════════════════════════════════════
        # Defined before per-app package names so we can reuse mkContainer in
        # both `container-<id>` (explicit) and `container` (default alias).
        mkContainer = app:
          pkgs.dockerTools.buildLayeredImage {
            name = app.oci.image_name;
            tag = "latest";
            created = "now";

            contents = [
              pkgs.bash
              pkgs.coreutils
              pkgs.python312
              pkgs.uv
              # Bundle only what the running service needs (app tree + lockfile).
              (pkgs.runCommand "${app.id}-app-bundle" { } ''
                mkdir -p $out/app
                cp -r ${appSrc app}/app $out/app/app
                cp ${appSrc app}/pyproject.toml $out/app/
                cp ${appSrc app}/uv.lock $out/app/
              '')
            ];

            config = {
              # Same production story as before: uv sync at container start (network
              # allowed there; Nix sandbox stays hermetic), then uvicorn on PORT.
              Cmd = [
                "bash" "-c"
                "cd /app && uv sync --frozen && exec uv run --frozen uvicorn app.entrypoints.http:app --host 0.0.0.0 --port ''${PORT:-8080}"
              ];
              WorkingDir = "/app";
              ExposedPorts = { "8080/tcp" = { }; };
              Env = [
                "PYTHONUNBUFFERED=1"
                "UV_CACHE_DIR=/tmp/.uv_cache"
                "PORT=8080"
                "ENVIRONMENT=production"
              ];
              Labels = {
                "org.opencontainers.image.source" =
                  "https://github.com/" + (
                    if builtins.getEnv "GITHUB_REPOSITORY" != ""
                    then builtins.getEnv "GITHUB_REPOSITORY"
                    else "OWNER/REPO"
                  );
                "org.opencontainers.image.description" = app.title;
                "org.opencontainers.image.version" = "1.0.0";
              };
            };
          };

        # Map app.id → image drv (used by validate-container and packages.container alias).
        containerPkgs = lib.listToAttrs (
          map (app: lib.nameValuePair app.id (mkContainer app)) shipApps
        );

        # Human-friendly flake attribute names: container-<id> (e.g. container-smart-writer).
        containerNamedPkgs = lib.listToAttrs (
          map (app: lib.nameValuePair "container-${app.id}" (mkContainer app)) shipApps
        );

        # ═════════════════════════════════════════════════════════════════════
        # TARGET 3 (per app): CHECKS — lint, unit tests, integration tests
        # ═════════════════════════════════════════════════════════════════════
        # Same stages as the original single-app flake; only the app source and
        # uv sync line vary via registry (sync_dev_args).

        mkLint = app:
          let
            syncArgs = uvSyncDevArgsStr app;
          in
          pkgs.runCommand "lint-${app.id}" {
            buildInputs = runtimeDeps;
          } ''
            export UV_CACHE_DIR="$TMPDIR/uv-cache"
            export UV_PROJECT_ENVIRONMENT="$TMPDIR/venv"
            cp -r ${appSrc app} "$TMPDIR/${app.id}"
            cd "$TMPDIR/${app.id}"

            echo "🔍 Running code quality checks (${app.id})..."

            uv sync --frozen ${syncArgs}

            export RUFF_CACHE_DIR="$TMPDIR/ruff-cache"
            echo "  - Linting with ruff..."
            uv run ruff check app/

            echo "  - Security scan with bandit..."
            uv run bandit -r app/

            echo "✅ All quality checks passed for ${app.id}!"
            touch $out
          '';

        mkTestUnit = app:
          let
            syncArgs = uvSyncDevArgsStr app;
          in
          pkgs.runCommand "test-unit-${app.id}" {
            buildInputs = runtimeDeps ++ [ pkgs.cacert ];
            SSL_CERT_FILE = "${pkgs.cacert}/etc/ssl/certs/ca-bundle.crt";
          } ''
            export UV_CACHE_DIR="$TMPDIR/uv-cache"
            export UV_PROJECT_ENVIRONMENT="$TMPDIR/venv"
            cp -r ${appSrc app} "$TMPDIR/${app.id}"
            cd "$TMPDIR/${app.id}"

            echo "🧪 Running unit tests (${app.id})..."

            uv sync --frozen ${syncArgs}

            export COVERAGE_FILE="$TMPDIR/.coverage"

            uv run pytest tests/unit/ \
              --cov=app \
              --cov-report=term-missing \
              --cov-fail-under=0

            echo "✅ Unit tests passed for ${app.id}!"
            touch $out
          '';

        # Pass the corresponding CLI derivation so `nix run`-style behavior is on PATH
        # as the binary named `app.id` (matches writeShellApplication name).
        mkTestIntegration = app: cliPkg:
          let
            syncArgs = uvSyncDevArgsStr app;
          in
          pkgs.runCommand "test-integration-${app.id}" {
            buildInputs = runtimeDeps ++ [ pkgs.cacert cliPkg ];
            SSL_CERT_FILE = "${pkgs.cacert}/etc/ssl/certs/ca-bundle.crt";
          } ''
            export UV_CACHE_DIR="$TMPDIR/uv-cache"
            export UV_PROJECT_ENVIRONMENT="$TMPDIR/venv"
            cp -r ${appSrc app} "$TMPDIR/${app.id}"
            cd "$TMPDIR/${app.id}"

            echo "🔗 Running integration tests (${app.id})..."

            uv sync --frozen ${syncArgs}

            ${app.id} --version

            uv run pytest tests/integration/ -v

            echo "✅ Integration tests passed for ${app.id}!"
            touch $out
          '';

        perAppChecks =
          lib.foldl' (
            acc: app:
            acc // {
              "lint-${app.id}" = mkLint app;
              "test-unit-${app.id}" = mkTestUnit app;
              "test-integration-${app.id}" = mkTestIntegration app cliPackages.${app.id};
            }
          ) { } applications;

        # One aggregate check: skopeo inspect each built image tarball (per ship app).
        validateContainers = pkgs.runCommand "validate-containers" {
          buildInputs = [ pkgs.skopeo pkgs.jq ];
        } (
          let
            inspectOne = app: ''
              echo "🐳 Validating container ${app.id}..."
              skopeo inspect "docker-archive:${containerPkgs.${app.id}}" | jq .
            '';
            body = lib.concatStringsSep "\n" (map inspectOne shipApps);
          in
          ''
            ${body}
            echo "✅ Container validation passed!"
            touch $out
          ''
        );

        # Registry order picks “default” CLI and default container (first ship-enabled app).
        firstApp = builtins.head applications;
        firstShip = builtins.head shipApps;
      in
      {
        # ═════════════════════════════════════════════════════════════════════
        # TARGET 1: DEVELOPMENT SHELL (one for the repo)
        # ═════════════════════════════════════════════════════════════════════
        devShells.default = pkgs.mkShell {
          buildInputs = runtimeDeps ++ devOnlyTools;

          shellHook = ''
            export UV_PYTHON="''${UV_PYTHON:-$(command -v python)}"

            echo "🚀 Multi-Agent Lab Development Environment"
            echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            echo "📦 Available Tools:"
            echo "  Python:  $(python --version 2>&1)"
            echo "  uv:      $(uv --version 2>&1)"
            echo "  Git:     $(git --version 2>&1)"
            echo ""
            echo "💡 Applications (see apps/registry.yaml):"
            echo "  cd apps/<name> && uv sync && uv run python -m app.main"
            echo ""
            echo "🔬 Run Tests:  nix flake check"
            echo "🐳 Containers: nix build .#container   # default: ${firstShip.id}"
            echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
          '';
        };

        # ═════════════════════════════════════════════════════════════════════
        # TARGETS 2 + 4: PACKAGES (flat attrset — Nix flake schema requirement)
        # ═════════════════════════════════════════════════════════════════════
        # Merged: per-app CLI attrs, per-app container-* attrs, and legacy aliases
        # `default` + `container` for the first registry / first ship app.
        packages =
          cliPackages
          // containerNamedPkgs
          // {
            default = cliPackages.${firstApp.id};
            container = containerPkgs.${firstShip.id};
          };

        # ═════════════════════════════════════════════════════════════════════
        # TARGET 3: CHECKS (per-app checks + validate-container)
        # ═════════════════════════════════════════════════════════════════════
        checks = perAppChecks // {
          validate-container = validateContainers;
        };
      }
    );
}

# ═══════════════════════════════════════════════════════════════════════════
# USAGE REMINDERS
# ═══════════════════════════════════════════════════════════════════════════
#
# Development:
#   nix develop
#   cd apps/<id> && uv sync && uv run python -m app.main
#
# CLI:
#   nix run .#<id> -- --help
#
# CI (local):
#   nix flake check
#
# Container images:
#   nix build .#container
#   nix build .#container-<id>
#   docker load < result
#
# Each app expects (same as before parameterization):
#   apps/<id>/
#     app/main.py
#     app/entrypoints/http.py
#     tests/unit/   tests/integration/
#     pyproject.toml  uv.lock
#
# ═══════════════════════════════════════════════════════════════════════════
