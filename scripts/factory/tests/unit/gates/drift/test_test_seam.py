"""T039 — `test-seam-ban` (T043; FR-013; I-A8).

Added lines of application code under `app_roots` must not branch on test-only
signals: `PYTEST_CURRENT_TEST`, `"pytest" in sys.modules`, `TESTING` / `IS_TEST`
flags, or fake-key sniffing such as `startswith("sk-test")`. Only changed lines count,
so a seam already on the base is not this PR's violation. Test code is not
application code (FR-013).
"""

from __future__ import annotations

import pytest

from factory.api import GateContext
from tests.fixtures.repo_builder import RepoBuilder
from tests.unit.gates.drift.helpers import assert_blocks, assert_passes

GATE = "test-seam-ban"
LLM = "apps/demo/app/llm.py"
BASE_LLM = "def ask(prompt: str) -> str:\n    return call_model(prompt)\n"

# The sprint-01 seam (apps/smart-writer-v2/app/agents/assessor.py, research.md).
SNIFFING_BASE = (
    "def live_model_enabled() -> bool:\n"
    "    key = get_openai_api_key()\n"
    "    if key is None:\n"
    "        return False\n"
    "    lowered = key.lower()\n"
    '    return not (lowered.startswith("sk-test") or "fake" in lowered)\n'
)


def seam_ctx(
    repo: RepoBuilder, head_files: dict[str, str], base_files: dict[str, str] | None = None
) -> GateContext:
    repo.add_demo_feature()
    pair = repo.base_head_pair(base_files or {LLM: BASE_LLM}, head_files)
    return repo.gate_context(pair, pr_number=1)


def with_branch(condition: str, *, imports: str = "import os\nimport sys\n") -> str:
    return (
        f"{imports}\n\ndef ask(prompt: str) -> str:\n"
        f"    if {condition}:\n"
        '        return "canned answer"\n'
        "    return call_model(prompt)\n"
    )


@pytest.mark.parametrize(
    "condition",
    [
        'os.environ.get("PYTEST_CURRENT_TEST")',
        '"PYTEST_CURRENT_TEST" in os.environ',
        '"pytest" in sys.modules',
        "'pytest' in sys.modules",
        "settings.TESTING",
        'os.environ.get("TESTING") == "1"',
        "IS_TEST",
        'os.getenv("IS_TEST")',
        'api_key.startswith("sk-test")',
        "api_key.startswith('sk-test-')",
        '"fake" in api_key.lower()',
    ],
    ids=[
        "pytest-current-test-get",
        "pytest-current-test-in-environ",
        "pytest-in-sys-modules",
        "pytest-in-sys-modules-single-quotes",
        "testing-setting",
        "testing-env",
        "is-test-flag",
        "is-test-env",
        "key-sniffing",
        "key-sniffing-single-quotes",
        "fake-key-sniffing",
    ],
)
def test_blocks_each_test_only_branch_in_app_code(repo: RepoBuilder, condition: str) -> None:
    ctx = seam_ctx(repo, {LLM: with_branch(condition)})
    assert_blocks(GATE, ctx, LLM)


def test_blocks_a_seam_in_a_new_app_file(repo: RepoBuilder) -> None:
    path = "apps/demo/app/agents/assessor.py"
    ctx = seam_ctx(repo, {path: SNIFFING_BASE})
    assert_blocks(GATE, ctx, path)


def test_passes_clean_app_change(repo: RepoBuilder) -> None:
    ctx = seam_ctx(
        repo,
        {
            LLM: BASE_LLM
            + "\n\ndef ask_twice(prompt: str) -> list[str]:\n    return [ask(prompt)] * 2\n"
        },
    )
    assert_passes(GATE, ctx)


def test_seam_already_on_base_is_not_this_prs_violation(repo: RepoBuilder) -> None:
    """Changed lines only: an unrelated edit to a file that already sniffs keys passes."""
    path = "apps/demo/app/agents/assessor.py"
    head = SNIFFING_BASE + "\n\ndef model_name() -> str:\n    return 'gpt-5'\n"
    ctx = seam_ctx(repo, {path: head}, base_files={path: SNIFFING_BASE})
    assert_passes(GATE, ctx)


def test_removing_a_seam_passes(repo: RepoBuilder) -> None:
    path = "apps/demo/app/agents/assessor.py"
    head = "def live_model_enabled() -> bool:\n    return get_openai_api_key() is not None\n"
    ctx = seam_ctx(repo, {path: head}, base_files={path: SNIFFING_BASE})
    assert_passes(GATE, ctx)


@pytest.mark.parametrize(
    "line",
    [
        "TESTING_DOCS_URL = 'https://example.test/docs'",
        "def summarize_ab_testing(results: list[float]) -> float:\n    return sum(results)",
        "# Run the suite with pytest before shipping.",
        "def check_key(api_key: str) -> None:\n"
        '    if not api_key.startswith("sk-"):\n'
        '        raise ValueError("not an OpenAI key")',
    ],
    ids=[
        "identifier-containing-testing",
        "ab-testing-feature",
        "pytest-in-comment",
        "key-format-validation",
    ],
)
def test_near_miss_lines_pass(repo: RepoBuilder, line: str) -> None:
    """False-positive guards: these mention test-like words but do not branch on tests."""
    ctx = seam_ctx(repo, {LLM: BASE_LLM + "\n\n" + line + "\n"})
    assert_passes(GATE, ctx)


def test_outside_app_roots_passes(repo: RepoBuilder) -> None:
    """Scope is `app_roots` (fixture config: `apps`)."""
    path = "scripts/smoke.py"
    ctx = seam_ctx(repo, {path: with_branch('os.environ.get("PYTEST_CURRENT_TEST")')})
    assert_passes(GATE, ctx)


def test_test_code_inside_an_app_passes(repo: RepoBuilder) -> None:
    """Tests may set test flags; only application code is banned (FR-013)."""
    path = "apps/demo/tests/test_llm.py"
    test_code = (
        "import pytest\n\n\n"
        "def test_canned(monkeypatch: pytest.MonkeyPatch) -> None:\n"
        '    monkeypatch.setenv("TESTING", "1")\n'
        '    assert "PYTEST_CURRENT_TEST" in __import__("os").environ\n'
    )
    ctx = seam_ctx(repo, {path: test_code})
    assert_passes(GATE, ctx)
