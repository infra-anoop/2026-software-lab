"""PR review PR-B1 — `deferral-words-need-od` pointer targets (FR-015; amendment-05).

Rule (contracts/gates.md § Deferral-words rule, orchestrator triage of verdict-04): a
pointer `→ <artifact>` counts only when the artifact is a regular file blob at head
(tree mode `100644` or `100755`) or a named phase (`→ plan`). A tracked directory
(`040000`), a tracked symlink (`120000`, whatever it points at) and a gitlink
(`160000`) do not count, consistent with eval evidence in `catalog-test-linkage`.
Pointers resolve from the repository root or from the citing file's directory.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from factory.api import GateContext
from tests.fixtures.repo_builder import BaseHeadPair, RepoBuilder
from tests.unit.gates.drift.helpers import assert_blocks, assert_passes

GATE = "deferral-words-need-od"
PLAN = "specs/demo-feature/plan.md"
BASE_PLAN = "# Plan: demo\n\n## Scope\n\n- Add `add()`.\n"
HEAD_BRANCH = "feature/head"


def plan_pair(repo: RepoBuilder, added: str) -> BaseHeadPair:
    """Base has the plan; head appends `added` to it."""
    repo.add_demo_feature()
    return repo.base_head_pair({PLAN: BASE_PLAN}, {PLAN: BASE_PLAN + added})


def plan_ctx(repo: RepoBuilder, added: str) -> GateContext:
    return repo.gate_context(plan_pair(repo, added), pr_number=1)


def commit_on_head(repo: RepoBuilder, pair: BaseHeadPair, subject: str) -> GateContext:
    """Commit the working-tree change already made on the head branch; push; context."""
    head_sha = repo.commit(subject)
    repo.push(HEAD_BRANCH)
    repo.checkout("main")
    return repo.gate_context(BaseHeadPair(pair.base_sha, head_sha, HEAD_BRANCH), pr_number=1)


@pytest.mark.parametrize(
    "line",
    [
        "- Export is deferred → apps/demo\n",
        "- Export is deferred → apps/demo/\n",
        "- Export is deferred → specs/demo-feature\n",
        "- Export is deferred → [the demo app](apps/demo)\n",
        "- Export is deferred → ../demo-feature\n",
    ],
    ids=["root-relative", "trailing-slash", "feature-dir", "markdown-link", "file-relative"],
)
def test_blocks_a_pointer_to_a_tracked_directory(repo: RepoBuilder, line: str) -> None:
    ctx = plan_ctx(repo, line)
    assert repo.git("ls-tree", ctx.head_sha, "apps/demo").startswith("040000 ")
    assert_blocks(GATE, ctx, "deferred", PLAN)


@pytest.mark.parametrize(
    "line",
    [
        "- Export is deferred → specs/demo-feature/tasks.md\n",
        "- Export is deferred → [tasks](specs/demo-feature/tasks.md)\n",
        "- Export is deferred → tasks.md\n",
    ],
    ids=["root-relative", "markdown-link", "file-relative"],
)
def test_passes_with_a_pointer_to_a_regular_file(repo: RepoBuilder, line: str) -> None:
    ctx = plan_ctx(repo, line)
    assert repo.git("ls-tree", ctx.head_sha, "specs/demo-feature/tasks.md").startswith("100644 ")
    assert_passes(GATE, ctx)


def test_passes_with_a_pointer_to_an_executable_file(repo: RepoBuilder) -> None:
    script = "scripts/follow_up.sh"
    pair = plan_pair(repo, f"- Export is deferred → {script}\n")
    repo.checkout(HEAD_BRANCH)
    repo.write(script, "#!/bin/sh\necho follow-up\n").chmod(0o755)
    ctx = commit_on_head(repo, pair, "executable follow-up")
    assert repo.git("ls-tree", ctx.head_sha, script).startswith("100755 ")
    assert_passes(GATE, ctx)


def test_passes_with_a_named_phase_pointer(repo: RepoBuilder) -> None:
    assert_passes(GATE, plan_ctx(repo, "- Export is deferred → plan\n"))


@pytest.mark.parametrize(
    ("link", "target"),
    [
        ("notes/follow-up.md", "../specs/demo-feature/tasks.md"),
        ("notes/demo-app", "../apps/demo"),
        ("notes/outside.md", "{outside}"),
    ],
    ids=["to-a-tracked-file", "to-a-tracked-directory", "outside-the-repo"],
)
def test_blocks_a_pointer_to_a_tracked_symlink(
    repo: RepoBuilder, tmp_path: Path, link: str, target: str
) -> None:
    """The link resolves to something that exists; the tracked mode decides."""
    outside = tmp_path / "outside.md"
    outside.write_text("# Follow-up\n", encoding="utf-8")
    pair = plan_pair(repo, f"- Export is deferred → {link}\n")
    repo.checkout(HEAD_BRANCH)
    (repo.path / link).parent.mkdir(parents=True, exist_ok=True)
    os.symlink(target.format(outside=outside), repo.path / link)
    assert (repo.path / link).exists()
    ctx = commit_on_head(repo, pair, "symlinked follow-up")
    assert repo.git("ls-tree", ctx.head_sha, link).startswith("120000 ")
    assert_blocks(GATE, ctx, "deferred", PLAN)


def test_blocks_a_pointer_to_a_gitlink(repo: RepoBuilder) -> None:
    gitlink = "vendor/follow-up"
    pair = plan_pair(repo, f"- Export is deferred → {gitlink}\n")
    repo.checkout(HEAD_BRANCH)
    repo.git("update-index", "--add", "--cacheinfo", f"160000,{pair.base_sha},{gitlink}")
    repo.git("commit", "-q", "-m", "gitlink follow-up")
    head_sha = repo.head_sha()
    repo.push(HEAD_BRANCH)
    repo.checkout("main")
    assert repo.git("ls-tree", head_sha, gitlink).startswith("160000 ")
    ctx = repo.gate_context(BaseHeadPair(pair.base_sha, head_sha, HEAD_BRANCH), pr_number=1)
    assert_blocks(GATE, ctx, "deferred", PLAN)
