{
  description = "2026 Research Auditor Industrial Pipeline - Stable Stack";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-25.05"; 
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = import nixpkgs { inherit system; };
        
        # System-level dependencies - The "Immutable Foundation"
        runtimeDeps = [ 
          pkgs.python312Full 
          pkgs.uv 
          pkgs.libffi 
          pkgs.zlib 
        ];

        # Shared script logic for the Product and the Container
        run-app-script = pkgs.writeShellScriptBin "run-app" ''
        export PATH="${pkgs.python312Full}/bin:${pkgs.uv}/bin:$PATH"
        cd /apps/research-auditor
        exec uv run --frozen python3 -m app.entrypoints.http
      '';

       in
      {
        # 1. THE WORKSTATION: For local development in Cursor
        devShells.default = pkgs.mkShell {
          buildInputs = runtimeDeps;
          shellHook = ''
            export IN_NIX_SHELL=impure
            # Per-app venvs: sync default app so "nix develop" gives a ready env
            if [ -f "apps/research-auditor/pyproject.toml" ]; then
              (cd apps/research-auditor && uv sync --quiet)
              source apps/research-auditor/.venv/bin/activate
            fi
            echo "Research Auditor Lab Environment (Stable) Loaded"
          '';
        };

        # 2. THE PRODUCT: The application itself (CLI version)
        packages.default = pkgs.writeShellApplication {
          name = "research-auditor";
          runtimeInputs = runtimeDeps;
          text = ''
            # Runs the app using the locked dependencies
            cd apps/research-auditor
            exec uv run --frozen python3 -m app.main "$@"
          '';
        };

        # 3. THE CONTAINER: Milestone #3 - For Cloud Deployment (Railway)
        packages.container = pkgs.dockerTools.buildLayeredImage {
          name = "research-auditor";
          tag = "latest";
          created = "now";

          contents = [ 
            pkgs.bash 
            pkgs.coreutils 
            pkgs.python312Full
            pkgs.uv
            run-app-script 
            
            # THE CARGO: Copying local files into the container
            (pkgs.runCommand "app-src" {} ''
            mkdir -p $out/apps/research-auditor
            
            # Create stable app/ directory name
            cp -r ${./apps/research-auditor/app} $out/apps/research-auditor/app
            
            # Place manifest files with stable names
            cp ${./apps/research-auditor/pyproject.toml} $out/apps/research-auditor/pyproject.toml
            cp ${./apps/research-auditor/uv.lock} $out/apps/research-auditor/uv.lock
          '')

          ];

          config = {
            # THE FIXED ENTRYPOINT: Matches your original workflow
            Cmd = [ "run-app" ];
            WorkingDir = "/";
            ExposedPorts = { "8080/tcp" = {}; };
            Env = [
              "PYTHONUNBUFFERED=1"
              "UV_CACHE_DIR=/tmp/.uv_cache"
            ];
          };
        };

        # 4. THE INSPECTOR: Automated checks
        checks.test-audit = pkgs.runCommand "test-audit" { 
          buildInputs = runtimeDeps; 
        } ''
          # Sandbox setup: uv requires the project files to validate the run
          cp ${./apps/research-auditor/pyproject.toml} .
          cp ${./apps/research-auditor/uv.lock} .
          mkdir -p apps/research-auditor
          cp -r ${./apps/research-auditor/app} apps/research-auditor/
          cd apps/research-auditor
          uv run --frozen python3 -m app.entrypoints.http
          touch $out
        '';
      }
    );
}