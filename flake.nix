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
          # --frozen ensures we use the exact uv.lock without trying to update it
          exec uv run --frozen python3 /apps/research-auditor/audit_env.py
        '';
      in
      {
        # 1. THE WORKSTATION: For local development in Cursor
        devShells.default = pkgs.mkShell {
          buildInputs = runtimeDeps;
          shellHook = ''
            export IN_NIX_SHELL=impure
            # Initialize uv environment if pyproject.toml exists
            if [ -f "pyproject.toml" ]; then 
              uv sync --quiet
              source .venv/bin/activate
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
            exec uv run --frozen python3 apps/research-auditor/app.py "$@"
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
              cp ${./apps/research-auditor/audit_env.py} $out/apps/research-auditor/audit_env.py
              # MUST include these for 'uv run' to function in the container
              cp ${./pyproject.toml} $out/pyproject.toml
              cp ${./uv.lock} $out/uv.lock
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
          cp ${./pyproject.toml} .
          cp ${./uv.lock} .
          uv run --frozen python3 ${./apps/research-auditor/audit_env.py}
          touch $out
        '';
      }
    );
}