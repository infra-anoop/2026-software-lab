{
  description = "2026 Research Auditor Industrial Pipeline";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-23.11";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = import nixpkgs { inherit system; };
        pythonEnv = pkgs.python312;
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

        # 2. THE PRODUCT: The application itself
        packages.default = pkgs.writeShellApplication {
          name = "research-auditor";
          runtimeInputs = [ pythonEnv ];
          text = ''
            export IN_NIX_SHELL=impure
            python3 apps/research-auditor/audit_env.py
          '';
        };

        # 3. THE INSPECTOR: Automated checks for GitHub Actions
        checks.test-audit = pkgs.runCommand "test-audit" { } ''
          export IN_NIX_SHELL=impure
          # We run the script; if it returns non-zero, the build fails
          ${pythonEnv}/bin/python3 ${./apps/research-auditor/audit_env.py}
          touch $out
        '';
      }
    );
}