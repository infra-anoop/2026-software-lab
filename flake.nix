
{
  description = "2026 Research Auditor Industrial Pipeline";

  inputs = {
    # nixpkgs.url = "github:NixOS/nixpkgs/nixos-23.11";
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        # 'pkgs' is our toolbox for this specific system (e.g. Linux x86)
        pkgs = import nixpkgs { inherit system; };
        
        # Define our Python environment once so it's consistent everywhere
        pythonEnv = pkgs.python312.withPackages (ps: [
          ps.requests
          # Add more libraries here as we go
          ps.python-dotenv
          ps.pydantic
          ps.pydantic-ai-slim
          ps.openai
        ]);
      in
      {
        # 1. THE WORKSTATION: For local development in Cursor
        devShells.default = pkgs.mkShell {
          buildInputs = [ pythonEnv ];
          shellHook = ''
            export IN_NIX_SHELL=impure
            echo "Research Auditor Lab Environment Loaded (Python 3.12)"
          '';
        };

        # 2. THE PRODUCT: The application itself (CLI version)
        packages.default = pkgs.writeShellApplication {
          name = "research-auditor";
          runtimeInputs = [ pythonEnv ];
          text = ''
            python3 apps/research-auditor/app.py
          '';
        };

        # 3. THE CONTAINER: Milestone #3 - For Cloud Deployment
        packages.container = pkgs.dockerTools.buildLayeredImage {
          name = "research-auditor";
          tag = "latest";
          created = "now";

          contents = [ 
            pythonEnv 
            pkgs.bash 
            pkgs.coreutils
            # 1. THE ALIAS: Creates a fixed 'run-app' command in /bin
            (pkgs.writeShellScriptBin "run-app" ''
              export PATH="${pythonEnv}/bin:$PATH"
              # We point this to the permanent location of your script
              exec python3 /apps/research-auditor/audit_env.py
            '')
            # 2. THE CARGO: This actually copies your local files into the container
            (pkgs.runCommand "app-src" {} ''
              mkdir -p $out/apps/research-auditor
              # This pulls the file from your repo into the Nix store inside the image
              cp ${./apps/research-auditor/audit_env.py} $out/apps/research-auditor/audit_env.py
            '')
          ];

          config = {
            # 3. THE FIXED ENTRYPOINT: Railway will now just call 'run-app'
            Cmd = [ "run-app" ];
            WorkingDir = "/";
            ExposedPorts = {
              "8080/tcp" = {};
            };
            Env = [
              "PYTHONUNBUFFERED=1"
            ];
          };
        };
        
        # 4. THE INSPECTOR: Automated checks
        checks.test-audit = pkgs.runCommand "test-audit" { } ''
          ${pythonEnv}/bin/python3 ${./apps/research-auditor/audit_env.py}
          touch $out
        '';
      }
    );
}
