{
  description = "2026 Research Lab Environment";

  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs/nixos-unstable";
  };

  outputs = { self, nixpkgs }:
    let
      system = "x86_64-linux"; # This matches your Codespace architecture
      pkgs = nixpkgs.legacyPackages.${system};
    in {
      devShells.${system}.default = pkgs.mkShell {
        buildInputs = with pkgs; [
          python312Packages.python
          python312Packages.pip
          git
          gh
        ];

        shellHook = ''
          echo "🛡️ Nix Shell Active: Python 3.12 Research Environment Loaded"
        '';
      };
    };
}