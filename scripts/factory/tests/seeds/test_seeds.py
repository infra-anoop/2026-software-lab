"""T014 — SC-002 seeded-violation suite: every sprint-01 drift seed is blocked.

Each test builds its violating fixture with `RepoBuilder` and asserts that
`run_gate(<gate-id>, ctx)` fails and names the gate. Red until slice B's gates land
(CP1): an unimplemented gate fails the "gate is implemented" assertion.
"""

from __future__ import annotations

from collections.abc import Mapping

import pytest

from factory.api import GateContext, GateEntrypointError, GateResult, run_gate
from tests.fixtures.repo_builder import REPO_JARGON, RepoBuilder, message, order, yaml_text

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
    head_files: Mapping[str, str | None],
    *,
    base_files: dict[str, str] | None = None,
    substitutes: list[str] | None = None,
    goal: str = "Deploy the demo app.",
    lock: dict[str, object] | None = None,
) -> GateContext:
    lock = dict(lock or {"id": "D1", "letter_tokens": ["railway"], "fidelity": "letter"})
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
    tool or host breaks it even when the token still appears somewhere. Thinner behavior
    is blocked mechanically by the removal and weaker-number seeds below (data-model Lock).
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
    ids=["comment", "deleted_line", "order_file", "docs"],
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


# Thinner behavior at letter fidelity (data-model Lock). The weakened seeds (except
# "in_place") and `other_file_still_has_it` keep each token present at head in a changed
# file, so a presence-only check misses them.

DEPLOY_ONE = "#!/bin/sh\nrailway up --service demo\n"
DEPLOY_TWO = DEPLOY_ONE + "railway up --service worker\n"
DEPLOY_THREE = "#!/bin/sh\nrailway link\n" + DEPLOY_TWO.removeprefix("#!/bin/sh\n")
RELEASE = "#!/bin/sh\nrailway up --service worker\n"
COVERAGE = "[report]\nfail_under = 70\n"
CLAIM = "#!/bin/sh\nfactory claim --cap 3\n"
FLOOR = {
    "id": "D2",
    "letter_tokens": ["fail_under = 70"],
    "fidelity": "letter",
    "direction": "min",
}
CEILING = {"id": "D7", "letter_tokens": ["$5"], "fidelity": "letter", "direction": "max"}
EXACT = {"id": "D8", "letter_tokens": ["cap 3"], "fidelity": "letter"}


@pytest.mark.parametrize(
    ("base_files", "head_files"),
    [
        (
            {"scripts/deploy.sh": DEPLOY_ONE},
            {"scripts/deploy.sh": '#!/bin/sh\necho "deploy skipped"\n'},
        ),
        (
            {"scripts/deploy.sh": DEPLOY_ONE},
            {"scripts/deploy.sh": "#!/bin/sh\n# railway up --service demo  (paused)\n"},
        ),
        (
            {"scripts/deploy.sh": DEPLOY_ONE, "scripts/release.sh": RELEASE},
            {"scripts/deploy.sh": "#!/bin/sh\n", "scripts/release.sh": RELEASE + "echo done\n"},
        ),
    ],
    ids=["only_file", "only_file_restated_in_comment", "other_file_still_has_it"],
)
def test_seed_lock_token_removed(
    repo: RepoBuilder, base_files: dict[str, str], head_files: dict[str, str]
) -> None:
    """Per file (governor 2026-10-04): a code file that honored the token at base no
    longer does at head, and no added code line elsewhere restores it (not a move)."""
    ctx = lock_context(repo, head_files, base_files=base_files)
    assert_blocked("lock.letter-tokens", ctx)


@pytest.mark.parametrize(
    ("lock", "path", "base", "head"),
    [
        (
            FLOOR,
            "scripts/coverage.toml",
            COVERAGE,
            COVERAGE + "\n[report.nightly]\nfail_under=60\n",
        ),
        (CEILING, "deploy/budget.toml", 'run_cap = "$5"\n', 'run_cap = "$5"\nnightly = "$12"\n'),
        (EXACT, "scripts/claim.sh", CLAIM, CLAIM + "factory claim --retry --cap 4\n"),
        (EXACT, "scripts/claim.sh", CLAIM, "#!/bin/sh\nfactory claim --cap 2\n"),
    ],
    ids=["min_floor_lowered", "max_ceiling_raised", "exact_changed", "exact_lowered_in_place"],
)
def test_seed_lock_numeric_token_weakened(
    repo: RepoBuilder, lock: dict[str, object], path: str, base: str, head: str
) -> None:
    """An added code line restates a numeric token's text with a weaker number."""
    ctx = lock_context(repo, {path: head}, base_files={path: base}, lock=lock)
    assert_blocked("lock.letter-tokens", ctx)


@pytest.mark.parametrize(
    ("lock", "base_files", "head_files"),
    [
        (
            FLOOR,
            {"scripts/coverage.toml": COVERAGE},
            {"scripts/coverage.toml": "[report]\nfail_under = 80\n"},
        ),
        (
            CEILING,
            {"deploy/budget.toml": 'run_cap = "$5"\n'},
            {"deploy/budget.toml": 'run_cap = "$3"\n'},
        ),
        (
            None,
            {"scripts/deploy.sh": DEPLOY_TWO},
            {"scripts/deploy.sh": DEPLOY_TWO.replace("worker\n", "worker --detach\n")},
        ),
        (
            EXACT,
            {"scripts/claim.sh": CLAIM},
            {"scripts/claim.sh": CLAIM.replace("--cap 3", "--cap 3 --json")},
        ),
        (
            None,
            {"scripts/deploy.sh": DEPLOY_TWO},
            {"scripts/deploy.sh": None, "scripts/release.sh": DEPLOY_TWO},
        ),
        (
            FLOOR,
            {"scripts/coverage.toml": COVERAGE},
            {"scripts/coverage.toml": COVERAGE + "port = 8080\nfail_under_ratio = 0.5\n"},
        ),
        (None, {"scripts/deploy.sh": DEPLOY_TWO}, {"scripts/deploy.sh": DEPLOY_ONE}),
        (None, {"scripts/deploy.sh": DEPLOY_THREE}, {"scripts/deploy.sh": DEPLOY_ONE}),
        (
            None,
            {"scripts/deploy.sh": DEPLOY_TWO},
            {"scripts/deploy.sh": DEPLOY_ONE + "# railway up --service worker  (paused)\n"},
        ),
    ],
    ids=[
        "min_floor_raised",
        "max_ceiling_lowered",
        "token_restated_in_edited_line",
        "numeric_token_restated_unchanged",
        "token_moved_to_another_file",
        "unrelated_numbers",
        "t8_repro_one_of_two_lines_deleted",
        "several_occurrences_deleted_file_still_has_token",
        "occurrence_commented_out_file_still_has_token",
    ],
)
def test_seed_lock_thinner_near_miss_passes(
    repo: RepoBuilder,
    lock: dict[str, object] | None,
    base_files: dict[str, str],
    head_files: dict[str, str | None],
) -> None:
    """False-positive guards: none of these is thinner than the lock."""
    ctx = lock_context(repo, head_files, base_files=base_files, lock=lock)
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


PLAIN_LABELS = ("Keep the current host", "Move to the cheaper host")


def decision_context(
    repo: RepoBuilder, prompt: str, labels: tuple[str, str] = PLAIN_LABELS
) -> GateContext:
    request = message(
        "decision_request",
        decision_id="pick-host",
        prompt=prompt,
        options=[{"label": label} for label in labels],
        recommended=labels[0],
        arch_impact=False,
    )
    pair = repo.base_head_pair({}, {"bus/decisions/pick-host/request.yaml": yaml_text(request)})
    return repo.gate_context(pair)


def assert_blocked_naming(gate_id: str, ctx: GateContext, offender: str) -> None:
    assert_blocked(gate_id, ctx)
    messages = run_seed(gate_id, ctx).messages
    assert any(offender.lower() in line.lower() for line in messages), (
        f"{gate_id} blocked but did not name {offender!r}: {messages}"
    )


@pytest.mark.parametrize(
    ("pattern", "offender", "prompt"),
    [
        (r"\b[TFRPD]\d+\b", "T042", "Should T042 ship before the demo on Friday?"),
        (r"\b[TFRPD]\d+\b", "F3", "Is F3 worth fixing before the demo on Friday?"),
        (r"\b[TFRPD]\d+\b", "R2", "Should we act on R2 before the demo on Friday?"),
        (r"\b[TFRPD]\d+\b", "P7", "Can P7 wait until after the demo on Friday?"),
        (r"\b[TFRPD]\d+\b", "D1", "Do you still want D1 for the demo on Friday?"),
        (r"FR-\d+", "FR-016", "Does FR-016 still hold for the demo on Friday?"),
        (r"SC-\d+", "SC-002", "Is SC-002 met well enough for the demo on Friday?"),
        (r"US\d+", "US3", "Should US3 be in the demo on Friday?"),
        ("§", "§", "Does constitution §G apply to the demo on Friday?"),
    ],
    ids=["T", "F", "R", "P", "D", "FR", "SC", "US", "section-sign"],
)
def test_seed_decision_request_quotes_an_id(
    repo: RepoBuilder, pattern: str, offender: str, prompt: str
) -> None:
    """One id pattern from contracts/messages.md per case, in otherwise plain language."""
    assert_blocked_naming("decision-request-no-ids", decision_context(repo, prompt), offender)


def test_seed_decision_request_id_in_option_label(repo: RepoBuilder) -> None:
    """Option labels are governor-facing text too."""
    ctx = decision_context(
        repo, "Which host should the demo use on Friday?", ("Keep the current host", "Do T042")
    )
    assert_blocked_naming("decision-request-no-ids", ctx, "T042")


@pytest.mark.parametrize("term", REPO_JARGON)
def test_seed_decision_request_uses_configured_jargon(repo: RepoBuilder, term: str) -> None:
    """Every term in the repo's `factory.toml [decision_lint].jargon` blocks on its own
    (governor accepted the eight-term list 2026-10-03; misses become corrections)."""
    ctx = decision_context(repo, f"Should the {term} be ready before the demo on Friday?")
    assert ctx.config.decision_lint.jargon == REPO_JARGON
    assert_blocked_naming("decision-request-no-ids", ctx, term)


def test_seed_decision_request_jargon_is_case_insensitive(repo: RepoBuilder) -> None:
    ctx = decision_context(repo, "Is the Worktree ready before the demo on Friday?")
    assert_blocked_naming("decision-request-no-ids", ctx, "worktree")


@pytest.mark.parametrize(
    "prompt",
    [
        "Should we finish packaging the release before the demo on Friday?",
        "Is a second host the best idea since sliced bread?",
        "Should the T-shirt order go out with Python 3.12 support?",
        "Keep peer-to-peer (P2P) sync on within the 2026 US budget?",
    ],
    ids=["packaging", "sliced-bread", "t-shirt-python-3.12", "p2p-us-budget"],
)
def test_seed_decision_request_near_miss_allowed(repo: RepoBuilder, prompt: str) -> None:
    """False-positive guard: words that merely resemble a term or an id pass."""
    result = run_seed("decision-request-no-ids", decision_context(repo, prompt))
    assert result.passed is True, result.messages


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
