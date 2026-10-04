"""T014 — SC-002 seeded-violation suite: every sprint-01 drift seed is blocked.

Each test builds its violating fixture with `RepoBuilder` and asserts that
`run_gate(<gate-id>, ctx)` fails and names the gate. Red until slice B's gates land
(CP1): an unimplemented gate fails the "gate is implemented" assertion.
"""

from __future__ import annotations

import pytest

from factory.api import GateContext, GateEntrypointError, GateResult, run_gate
from tests.fixtures.repo_builder import RepoBuilder, message, order, yaml_text

pytestmark = pytest.mark.seed

ORDER_ID = "wo-20261006-seed"
ORDER_DIR = f"bus/orders/{ORDER_ID}"


def run_seed(gate_id: str, ctx: GateContext) -> GateResult:
    try:
        result: GateResult | None = run_gate(gate_id, ctx)
    except GateEntrypointError as exc:
        result = None
        reason = str(exc)
    assert result is not None, f"gate {gate_id} is not implemented: {reason}"
    return result


def assert_blocked(gate_id: str, ctx: GateContext) -> None:
    result = run_seed(gate_id, ctx)
    assert result.gate_id == gate_id
    assert result.passed is False, f"{gate_id} let the seeded violation through"
    assert any(gate_id in line for line in result.messages), result.messages


def seed_order(**fields: object) -> str:
    return yaml_text(order(ORDER_ID, feature="demo-feature", **fields))


def test_seed_undeclared_substitution(repo: RepoBuilder) -> None:
    """Order covers a task tagged with locked letter decision D1 but declares no lock."""
    repo.add_demo_feature()
    pair = repo.base_head_pair(
        {},
        {
            f"{ORDER_DIR}/order.yaml": seed_order(
                goal="Deploy the demo app.",
                tasks=["T002"],
                owned_paths=["deploy/railway/demo.toml"],
                locks=[],
            )
        },
        head_branch=f"wo/{ORDER_ID}",
    )
    assert_blocked("order-fidelity-declared", repo.gate_context(pair, order_id=ORDER_ID))


FLY_CONFIG = 'app = "demo"\nprimary_region = "iad"\n'


def lock_context(
    repo: RepoBuilder,
    head_files: dict[str, str],
    *,
    base_files: dict[str, str] | None = None,
    substitutes: list[str] | None = None,
    goal: str = "Deploy the demo app.",
) -> GateContext:
    lock: dict[str, object] = {"id": "D1", "letter_tokens": ["railway"], "fidelity": "letter"}
    if substitutes is not None:
        lock["substitutes"] = substitutes
    repo.add_demo_feature()
    order_file = seed_order(
        goal=goal, tasks=["T002"], owned_paths=["deploy/**", "docs/**", "scripts/**"], locks=[lock]
    )
    pair = repo.base_head_pair(
        base_files or {},
        {f"{ORDER_DIR}/order.yaml": order_file, **head_files},
        head_branch=f"wo/{ORDER_ID}",
    )
    return repo.gate_context(pair, order_id=ORDER_ID, pr_number=1)


def test_seed_declared_lock_violated(repo: RepoBuilder) -> None:
    """Order declares letter fidelity to Railway; the diff deploys somewhere else.

    Letter fidelity is semantic (US3 #8, SC-002; governor lock 2026-10-03): a different
    tool or host breaks it even when the token still appears somewhere. "Thinner
    behavior" is judged by the independent reviewer's fidelity rubric, not by this gate;
    a reject verdict blocks merge.
    """
    ctx = lock_context(repo, {"deploy/fly/demo.toml": FLY_CONFIG})
    assert_blocked("lock.letter-tokens", ctx)


@pytest.mark.parametrize(
    ("where", "head_files", "base_files", "goal"),
    [
        (
            "comment",
            {"deploy/fly/demo.toml": "# was on railway before this change\n" + FLY_CONFIG},
            None,
            "Deploy the demo app.",
        ),
        (
            "deleted_line",
            {"deploy/demo.toml": 'provider = "fly"\n'},
            {"deploy/demo.toml": 'provider = "railway"\n'},
            "Deploy the demo app.",
        ),
        (
            "order_file",
            {"deploy/fly/demo.toml": FLY_CONFIG},
            None,
            "Deploy the demo app to Railway.",
        ),
        (
            "docs",
            {
                "docs/deploy.md": "# Deploy\n\nThe demo app deploys to Railway.\n",
                "deploy/fly/demo.toml": FLY_CONFIG,
            },
            None,
            "Deploy the demo app.",
        ),
    ],
)
def test_seed_lock_token_only_outside_code(
    repo: RepoBuilder,
    where: str,
    head_files: dict[str, str],
    base_files: dict[str, str] | None,
    goal: str,
) -> None:
    """The token appears only in a comment, a deleted line, the order file, or docs,
    while the added code deploys with a substitute host: still a letter violation."""
    ctx = lock_context(repo, head_files, base_files=base_files, goal=goal)
    assert_blocked("lock.letter-tokens", ctx)


def test_seed_lock_registered_substitute_in_added_code(repo: RepoBuilder) -> None:
    """The token is honored, but a substitute registered on the lock is added too."""
    ctx = lock_context(
        repo,
        {
            "deploy/railway/demo.toml": '[deploy]\nstartCommand = "uvicorn app:app"\n',
            "scripts/deploy.sh": "#!/bin/sh\nrailway up --service demo || flyctl deploy\n",
        },
        substitutes=["fly", "flyctl"],
    )
    assert_blocked("lock.letter-tokens", ctx)


def test_seed_lock_honored_passes(repo: RepoBuilder) -> None:
    """False-positive guard: the added code uses the named host and no substitute."""
    ctx = lock_context(
        repo,
        {"scripts/deploy.sh": "#!/bin/sh\nrailway up --service demo\n"},
        substitutes=["fly", "flyctl"],
    )
    result = run_seed("lock.letter-tokens", ctx)
    assert result.passed is True, result.messages


def test_seed_hidden_deferral(repo: RepoBuilder) -> None:
    """A spec line parks required work without a decision id, pointer, or governor tag."""
    repo.add_demo_feature()
    spec = (repo.path / "specs/demo-feature/spec.md").read_text(encoding="utf-8")
    pair = repo.base_head_pair(
        {},
        {
            "specs/demo-feature/spec.md": spec
            + "\n## Scope\n\n- Retry on deploy failure is deferred to a later sprint.\n"
        },
    )
    assert_blocked("deferral-words-need-od", repo.gate_context(pair))


def test_seed_not_red_first(repo: RepoBuilder) -> None:
    """The PR's new test already passes on base code."""
    repo.add_demo_feature()
    pair = repo.base_head_pair(
        {},
        {
            "apps/demo/tests/test_calc.py": (
                "from app.calc import add\n\n\ndef test_add() -> None:\n    assert add(1, 2) == 3\n"
            )
        },
        head_branch=f"wo/{ORDER_ID}",
    )
    assert_blocked("red-first-proof", repo.gate_context(pair, order_id=ORDER_ID, pr_number=1))


def test_seed_test_seam(repo: RepoBuilder) -> None:
    """App code adds a branch that only runs under pytest."""
    repo.add_demo_feature()
    pair = repo.base_head_pair(
        {"apps/demo/app/llm.py": "def ask(prompt: str) -> str:\n    return call_model(prompt)\n"},
        {
            "apps/demo/app/llm.py": (
                "import os\n\n\ndef ask(prompt: str) -> str:\n"
                '    if os.environ.get("PYTEST_CURRENT_TEST"):\n'
                '        return "canned answer"\n'
                "    return call_model(prompt)\n"
            )
        },
    )
    assert_blocked("test-seam-ban", repo.gate_context(pair, pr_number=1))


def test_seed_outside_owned_paths(repo: RepoBuilder) -> None:
    """The order owns one file; the diff also edits a deploy manifest."""
    repo.add_demo_feature()
    pair = repo.base_head_pair(
        {},
        {
            f"{ORDER_DIR}/order.yaml": seed_order(owned_paths=["apps/demo/app/calc.py"]),
            "apps/demo/app/calc.py": "def add(a: int, b: int) -> int:\n    return b + a\n",
            "deploy/railway/demo.toml": "[deploy]\nstartCommand = 'run'\n",
        },
        head_branch=f"wo/{ORDER_ID}",
    )
    assert_blocked(
        "diff-within-owned-paths", repo.gate_context(pair, order_id=ORDER_ID, pr_number=1)
    )


def test_seed_jargon_to_governor(repo: RepoBuilder) -> None:
    """A decision request quotes task, finding, and requirement ids at the governor."""
    request = message(
        "decision_request",
        decision_id="pick-host",
        prompt="Lock D1 per T042 and FR-016 before the slice B packet ships?",
        options=[{"label": "Keep P3 as is"}, {"label": "Pull SC-002 forward"}],
        recommended="Keep P3 as is",
        arch_impact=False,
    )
    pair = repo.base_head_pair({}, {"bus/decisions/pick-host/request.yaml": yaml_text(request)})
    assert_blocked("decision-request-no-ids", repo.gate_context(pair))


def test_seed_catalog_unlinked(repo: RepoBuilder) -> None:
    """The order's PR implements catalog row demo.adds, whose evidence is still `planned`."""
    repo.add_demo_feature()
    pair = repo.base_head_pair(
        {},
        {
            f"{ORDER_DIR}/order.yaml": seed_order(
                owned_paths=["apps/demo/**"], checks=["demo.adds"]
            ),
            "apps/demo/tests/test_calc.py": (
                "from app.calc import add\n\n\ndef test_add() -> None:\n    assert add(2, 2) == 4\n"
            ),
        },
        head_branch=f"wo/{ORDER_ID}",
    )
    assert_blocked("catalog-test-linkage", repo.gate_context(pair, order_id=ORDER_ID, pr_number=1))
