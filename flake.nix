{
  description = "2026 Research Auditor Industrial Pipeline";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-23.11";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        # 'pkgs' is our toolbox for this specific system (e.g. Linux x86)
        pkgs = import nixpkgs { inherit system; };
        
        # Define our Python environment once so it's consistent everywhere
        pythonEnv = pkgs.python312.withPackages (ps: with ps; [
          requests
          # Add more libraries here as we go
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
        # Access this by running: nix build .#container
        packages.container = pkgs.dockerTools.buildLayeredImage {
          name = "research-auditor";
          tag = "latest";
          created = "now";

          contents = [ 
            pythonEnv 
            pkgs.bash 
            pkgs.coreutils 
          ];

          config = {
            # Note: We use the absolute path within the container
            Cmd = [ "${pythonEnv}/bin/python3" "apps/research-auditor/app.py" ];
            WorkingDir = "/";
            ExposedPorts = {
              "8080/tcp" = {};
            };
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