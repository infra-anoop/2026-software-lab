"""T095 — PR-C2: the hook wrapper bootstraps through Nix and fails open quietly.

contracts/hooks.md § Invocation (Bootstrap, PR review PR-C2): when neither the project
venv (`scripts/factory/.venv/bin/factory-hook`) nor an ambient `uv` exists, the wrapper
runs `nix develop <repo root> -c uv run --project scripts/factory factory hook <name>`.
When no fallback can start or answer (no `nix`, or a `nix` that fails without output),
the wrapper itself prints that hook's quiet fail-open response, writes the reason to
stderr and exits 0. It never exits 127.

The real `.cursor/hooks/factory-hook.sh` is copied into a scratch project with no venv,
and run with a `PATH` holding only system directories (no `uv`, no `nix`) plus, per
test, a stub `nix`.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from tests.fixtures.repo_builder import REPO_ROOT

WRAPPER = ".cursor/hooks/factory-hook.sh"
SYSTEM_PATH = "/usr/bin:/bin"
FAIL_OPEN = {
    "spawn-guard": {"permission": "allow"},
    "shell-guard": {"permission": "allow"},
    "owned-path-warn": {},
    "decision-in-chat": {},
}
PAYLOAD = '{"hook_event_name": "probe", "workspace_roots": []}'
HOOKS = sorted(FAIL_OPEN)


def scratch_project(tmp_path: Path) -> Path:
    wrapper = REPO_ROOT / WRAPPER
    assert wrapper.is_file(), f"{wrapper} is missing"
    root = tmp_path / "project"
    target = root / WRAPPER
    target.parent.mkdir(parents=True)
    shutil.copy2(wrapper, target)
    (root / "scripts/factory").mkdir(parents=True)
    assert not (root / "scripts/factory/.venv").exists()
    return root


def stub_nix(bin_dir: Path, log: Path, *, stdout: str, exit_code: int) -> None:
    bin_dir.mkdir(parents=True, exist_ok=True)
    nix = bin_dir / "nix"
    nix.write_text(
        "#!/bin/sh\n"
        f'printf "%s\\n" "$*" >> "{log}"\n'
        f'cat > "{log}.stdin"\n'
        f"printf '%s' '{stdout}'\n"
        'echo "stub nix stderr" >&2\n'
        f"exit {exit_code}\n",
        encoding="utf-8",
    )
    nix.chmod(0o755)


def run_wrapper(
    root: Path, name: str, tmp_path: Path, extra_path: Path | None = None
) -> subprocess.CompletedProcess[str]:
    path = f"{extra_path}:{SYSTEM_PATH}" if extra_path else SYSTEM_PATH
    for tool in ("uv", "factory-hook"):
        assert shutil.which(tool, path=path) is None, f"{tool} is on the test PATH {path}"
    if extra_path is None:
        assert shutil.which("nix", path=path) is None, f"nix is on the test PATH {path}"
    return subprocess.run(
        f"{WRAPPER} {name}",
        shell=True,
        cwd=root,
        env={"PATH": path, "HOME": str(tmp_path)},
        input=PAYLOAD,
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )


def assert_fail_open(completed: subprocess.CompletedProcess[str], name: str) -> None:
    assert completed.returncode == 0, (completed.returncode, completed.stdout, completed.stderr)
    lines = completed.stdout.strip().splitlines()
    assert len(lines) == 1, completed.stdout
    assert json.loads(lines[0]) == FAIL_OPEN[name], completed.stdout
    assert completed.stderr.strip(), "the wrapper must say why it failed open (stderr)"


@pytest.mark.parametrize("name", HOOKS)
def test_wrapper_runs_the_slow_path_inside_nix_without_venv_or_uv(
    tmp_path: Path, name: str
) -> None:
    root = scratch_project(tmp_path)
    log = tmp_path / "nix.log"
    answer = json.dumps({"answered_by": "stub nix", "hook": name})
    stub_nix(tmp_path / "bin", log, stdout=answer, exit_code=0)
    completed = run_wrapper(root, name, tmp_path, tmp_path / "bin")
    assert completed.returncode == 0, (completed.returncode, completed.stdout, completed.stderr)
    assert log.is_file(), f"the wrapper did not call nix: {completed.stderr}"
    calls = log.read_text(encoding="utf-8").splitlines()
    assert len(calls) == 1, calls
    args = calls[0].split()
    assert args[0] == "develop" and Path(args[1]).resolve() == root.resolve(), args
    assert args[2:] == ["-c", "uv", "run", "--project", "scripts/factory", "factory", "hook", name]
    assert json.loads(completed.stdout) == json.loads(answer), completed.stdout
    assert Path(f"{log}.stdin").read_text(encoding="utf-8") == PAYLOAD


@pytest.mark.parametrize("name", HOOKS)
def test_wrapper_fails_open_without_venv_uv_or_nix(tmp_path: Path, name: str) -> None:
    """Integration: a fresh worktree with neither the venv, `uv` nor `nix`."""
    completed = run_wrapper(scratch_project(tmp_path), name, tmp_path)
    assert completed.returncode != 127, completed.stderr
    assert_fail_open(completed, name)


@pytest.mark.parametrize("name", HOOKS)
def test_wrapper_fails_open_when_nix_fails_without_output(tmp_path: Path, name: str) -> None:
    root = scratch_project(tmp_path)
    log = tmp_path / "nix.log"
    stub_nix(tmp_path / "bin", log, stdout="", exit_code=1)
    completed = run_wrapper(root, name, tmp_path, tmp_path / "bin")
    assert log.is_file(), f"the wrapper did not try nix: {completed.stderr}"
    assert_fail_open(completed, name)
