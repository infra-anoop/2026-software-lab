"""PR review PR-B4 — `red-first-proof` child environment (I-A3; D5; amendment-05).

The child interpreter that runs PR test code gets an environment built from an explicit
minimal allowlist at the typed config boundary (`factory.config`), never the caller's
environment minus a few names. Credentials, `GITHUB_*` / Actions tokens, any variable
the allowlist does not name, and ambient pytest / Python controls never reach it.
Slice B code holds no environment access of its own, including inside child source.

Fixture app as in test_red_first.py: `app/clamp.py` is buggy on base and fixed on head,
so the new test is red on base by assertion. On head it also asserts that no variable
in its environment carries a canary value; a leak makes it fail on head and the gate
block, so the gate passes only when the child environment is clean.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

import factory
from factory.api import GateContext
from tests.fixtures.repo_builder import RepoBuilder
from tests.unit.gates.drift.helpers import assert_passes

GATE = "red-first-proof"
TESTS = "apps/demo/tests/test_clamp.py"
CLAMP = "apps/demo/app/clamp.py"
CLAMP_BUGGY = "def clamp(x: int, lo: int, hi: int) -> int:\n    return x\n"
CLAMP_FIXED = "def clamp(x: int, lo: int, hi: int) -> int:\n    return max(lo, min(x, hi))\n"
CANARY = "canary-ambient-"
LEAK_CHECK = (
    "import os\n\n"
    "from app.clamp import clamp\n\n\n"
    "def test_clamp_caps_high_in_a_clean_environment() -> None:\n"
    f"    leaked = sorted(k for k, v in os.environ.items() if {CANARY!r} in v)\n"
    "    assert clamp(5, 0, 3) == 3\n"
    "    assert leaked == []\n"
)
NEVER_IN_CHILD = [
    "GITHUB_TOKEN",
    "GH_TOKEN",
    "GITHUB_PAT",
    "ACTIONS_RUNTIME_TOKEN",
    "ACTIONS_ID_TOKEN_REQUEST_TOKEN",
    "ACTIONS_ID_TOKEN_REQUEST_URL",
    "FACTORY_GITHUB_APP_PRIVATE_KEY",
    "INFISICAL_TOKEN",
    "LAB_SERVICE_API_KEY",
    "PYTEST_ADDOPTS",
    "PYTEST_PLUGINS",
    "PYTHONPATH",
    "PYTHONSTARTUP",
    "PYTHONWARNINGS",
]
SLICE_B_CODE = ["gates/drift", "intent", "cli/intent.py"]
ENV_ACCESS = re.compile(r"\b(environb?|getenvb?|putenv|unsetenv)\b")


def clamp_ctx(repo: RepoBuilder) -> GateContext:
    repo.add_demo_feature()
    pair = repo.base_head_pair({CLAMP: CLAMP_BUGGY}, {CLAMP: CLAMP_FIXED, TESTS: LEAK_CHECK})
    return repo.gate_context(pair, pr_number=1)


def test_control_passes_with_no_canary_in_the_caller_environment(repo: RepoBuilder) -> None:
    assert_passes(GATE, clamp_ctx(repo))


@pytest.mark.parametrize("name", NEVER_IN_CHILD)
def test_caller_variable_never_reaches_the_child(
    repo: RepoBuilder, monkeypatch: pytest.MonkeyPatch, name: str
) -> None:
    """`LAB_SERVICE_API_KEY` is a name no list knows: only an allowlist excludes it."""
    ctx = clamp_ctx(repo)
    monkeypatch.setenv(name, f"{CANARY}{name.lower()}")
    assert_passes(GATE, ctx)


def test_slice_b_code_has_no_environment_access_outside_config() -> None:
    """Text scan, so source handed to a child interpreter counts too."""
    package = Path(factory.__file__).parent
    offenders = []
    for root in SLICE_B_CODE:
        target = package / root
        assert target.exists(), f"factory/{root} is missing"
        files = sorted(target.rglob("*.py")) if target.is_dir() else [target]
        for path in files:
            for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                if ENV_ACCESS.search(line):
                    offenders.append(f"{path.relative_to(package)}:{number}: {line.strip()}")
    assert offenders == [], "environment access outside factory.config:\n" + "\n".join(offenders)
