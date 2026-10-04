"""T029 — `pr open` and `verdict` family + isolation rules.

Catalogs: `handoff.reviewer_family`, `handoff.reviewer_isolated` (machine half).
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from factory.cli import exit_codes
from tests.fixtures.cli_runner import FactoryCli
from tests.fixtures.repo_builder import RepoBuilder, message, order, yaml_text

pytestmark = pytest.mark.contract

DAY = "20261007"


def oid(slug: str) -> str:
    return f"wo-{DAY}-{slug}"


def claimed_with_handoff(repo: RepoBuilder, slug: str, *, valid: bool = True) -> str:
    order_id = oid(slug)
    repo.add_demo_feature()
    repo.issue_order(order(order_id, owned_paths=["apps/demo/app/calc.py"], checks=[]))
    repo.add_event(order_id, message("claim", order_id=order_id))
    extra = {"apps/demo/app/calc.py": "def add(a, b):\n    return a + b\n"}
    handoff = message("handoff", order_id=order_id)
    if not valid:
        del handoff["deviations"]
    repo.add_event(order_id, handoff, validate=valid, extra_files=extra)
    repo.add_event(order_id, message("run_complete", order_id=order_id))
    return order_id


def verdict_path(repo: RepoBuilder, order_id: str, **overrides: object) -> Path:
    head = repo.head_sha(f"wo/{order_id}")
    fields: dict[str, object] = {
        "inputs": [{"path": f"bus/orders/{order_id}/order.yaml", "sha": head}],
        **overrides,
    }
    path = repo.root / "verdict.yaml"
    path.write_text(yaml_text(message("verdict", order_id=order_id, **fields)), encoding="utf-8")
    return path


def test_pr_open_refuses_without_handoff(repo: RepoBuilder, factory_cli: FactoryCli) -> None:
    order_id = oid("nohandoff")
    repo.issue_order(order(order_id, owned_paths=[f"apps/demo/{order_id}/**"]))
    repo.add_event(order_id, message("claim", order_id=order_id))
    repo.checkout(f"wo/{order_id}")
    result = factory_cli("pr", "open", order_id, repo=repo.path)
    assert result.exit_code == exit_codes.REFUSED


def test_pr_open_refuses_invalid_handoff(repo: RepoBuilder, factory_cli: FactoryCli) -> None:
    order_id = claimed_with_handoff(repo, "badhandoff", valid=False)
    repo.checkout(f"wo/{order_id}")
    result = factory_cli("pr", "open", order_id, repo=repo.path)
    assert result.exit_code == exit_codes.REFUSED


def test_pr_open_body_links_order_and_intents(repo: RepoBuilder, factory_cli: FactoryCli) -> None:
    order_id = claimed_with_handoff(repo, "pr-body")
    repo.checkout(f"wo/{order_id}")
    result = factory_cli("pr", "open", order_id, repo=repo.path)
    assert result.exit_code == exit_codes.OK, (
        f"expected exit 0, got {result.exit_code}\n{result.stdout}\n{result.stderr}"
    )
    prs = repo.github.list_prs_by_head(f"wo/{order_id}")
    assert prs, "pr open must create a PR via GitHubPort"
    body = prs[0].body
    assert order_id in body
    assert "I-B7" in body or "I-P2" in body or "intent" in body.lower()


def test_verdict_refuses_same_family_reviewer(repo: RepoBuilder, factory_cli: FactoryCli) -> None:
    order_id = claimed_with_handoff(repo, "samefamily")
    path = verdict_path(
        repo,
        order_id,
        actor_model="claude-opus-5.5",
        reviewer_model="claude-opus-5.5",
        reviewer_family="anthropic",
    )
    repo.checkout(f"wo/{order_id}")
    result = factory_cli("verdict", order_id, "--file", str(path), repo=repo.path)
    assert result.exit_code == exit_codes.REFUSED
    combined = result.stdout + result.stderr
    assert "family" in combined.lower() or "anthropic" in combined


def test_verdict_refuses_input_that_is_not_a_git_path(
    repo: RepoBuilder, factory_cli: FactoryCli
) -> None:
    order_id = claimed_with_handoff(repo, "transcript")
    head = repo.head_sha(f"wo/{order_id}")
    path = verdict_path(
        repo,
        order_id,
        inputs=[{"path": "notes/chat-transcript-2026-10-07.md", "sha": head}],
    )
    repo.checkout(f"wo/{order_id}")
    result = factory_cli("verdict", order_id, "--file", str(path), repo=repo.path)
    assert result.exit_code == exit_codes.REFUSED
    combined = result.stdout + result.stderr
    lowered = combined.lower()
    assert "git" in lowered or "transcript" in lowered or "input" in lowered


VERDICT_FIELDS = (
    "id",
    "decision",
    "findings",
    "reviewer_model",
    "reviewer_family",
    "inputs",
    "bootstrap",
)


def test_verdict_commits_valid_different_family_verdict(
    repo: RepoBuilder, factory_cli: FactoryCli
) -> None:
    order_id = claimed_with_handoff(repo, "accepted-verdict")
    head = repo.head_sha(f"wo/{order_id}")
    path = verdict_path(
        repo,
        order_id,
        actor_model="gpt-5.6-sol",
        reviewer_model="gpt-5.6-sol",
        reviewer_family="openai",
        inputs=[
            {"path": f"bus/orders/{order_id}/order.yaml", "sha": head},
            {"path": "apps/demo/app/calc.py", "sha": head},
        ],
    )
    submitted = yaml.safe_load(path.read_text(encoding="utf-8"))
    repo.checkout(f"wo/{order_id}")
    result = factory_cli("verdict", order_id, "--file", str(path), repo=repo.path)
    assert result.exit_code == exit_codes.OK, (
        f"expected exit 0, got {result.exit_code}\n{result.stdout}\n{result.stderr}"
    )
    new_commits = repo.git("rev-list", f"{head}..wo/{order_id}").splitlines()
    assert len(new_commits) == 1, f"verdict must be exactly one commit on the branch: {new_commits}"
    verdict_file = f"bus/orders/{order_id}/verdict-01.yaml"
    changes = repo.git("diff-tree", "--no-commit-id", "--name-status", "-r", new_commits[0])
    assert changes.splitlines() == [f"A\t{verdict_file}"], changes
    committed = yaml.safe_load(repo.git("show", f"wo/{order_id}:{verdict_file}"))
    for field in VERDICT_FIELDS:
        assert committed.get(field) == submitted.get(field), f"{field}: {committed.get(field)!r}"


@pytest.mark.parametrize(
    "bad_input",
    ["missing-path", "missing-sha"],
)
def test_verdict_refuses_input_absent_from_git(
    repo: RepoBuilder, factory_cli: FactoryCli, bad_input: str
) -> None:
    order_id = claimed_with_handoff(repo, f"absent-{bad_input}")
    head = repo.head_sha(f"wo/{order_id}")
    if bad_input == "missing-path":
        missing = {"path": "apps/demo/app/missing.py", "sha": head}
        named = missing["path"]
    else:
        missing = {"path": f"bus/orders/{order_id}/order.yaml", "sha": "f" * 40}
        named = "f" * 7
    path = verdict_path(
        repo,
        order_id,
        inputs=[{"path": f"bus/orders/{order_id}/order.yaml", "sha": head}, missing],
    )
    repo.checkout(f"wo/{order_id}")
    result = factory_cli("verdict", order_id, "--file", str(path), repo=repo.path)
    assert result.exit_code == exit_codes.REFUSED, (
        f"expected exit 2, got {result.exit_code}\n{result.stdout}\n{result.stderr}"
    )
    assert named in result.stdout + result.stderr, "refusal must name the absent input"
    assert repo.head_sha(f"wo/{order_id}") == head, "refused verdict must commit nothing"
