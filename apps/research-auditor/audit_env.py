import sys
import os


def audit_environment() -> None:
    """
    Audit the current Python environment:
    - Print Python version.
    - Detect presence of 'IN_NIX_SHELL' environment variable.

    Why: Ensures that scripts are executed in a reproducible, Nix-managed environment, critical for research and compliance.
    """
    python_version = sys.version.replace('\n', ' ')
    in_nix_shell = os.getenv("IN_NIX_SHELL")

    print("=== Environment Audit ===")
    print(f"Python version: {python_version}")
    if in_nix_shell is not None:
        print("IN_NIX_SHELL detected. Running inside a Nix shell.")
    else:
        print("WARNING: IN_NIX_SHELL not detected. Not running inside a Nix shell.")


if __name__ == "__main__":
    audit_environment()
