"""T039 — `order-fidelity-declared` + `lock.letter-tokens` (T046; FR-016; I-B5).

`order-fidelity-declared`: every named lock the effective order's owned paths or goal
touch has a Lock entry. The demo feature's locked letter decision D1 (host = Railway)
is touched by task T002, which is tagged `[OD:D1]` and names `deploy/railway/demo.toml`.

`lock.letter-tokens`: for each `fidelity: letter` lock, the PR's code lines honor
every token, no registered substitute appears in added code, and no token is removed
or weakened (data-model § WorkOrder, Lock; `git diff --no-renames`). The seeds in
`tests/seeds` hold the removal / weakening / near-miss matrix; this file covers
fidelity classes, several locks, comment styles, and missing inputs.
"""

from __future__ import annotations

from typing import Any

import pytest

from factory.api import GateContext
from tests.fixtures.repo_builder import RepoBuilder
from tests.unit.gates.drift.helpers import (
    ORDER_ID,
    amendment_for,
    assert_blocks,
    assert_passes,
    oid,
    order_ctx,
    order_for,
    order_pair,
)

DECLARED = "order-fidelity-declared"
TOKENS = "lock.letter-tokens"

RAILWAY_LOCK: dict[str, Any] = {"id": "D1", "letter_tokens": ["railway"], "fidelity": "letter"}
CAP_LOCK: dict[str, Any] = {"id": "D8", "letter_tokens": ["cap 3"], "fidelity": "letter"}
FLY_CONFIG = 'app = "demo"\nprimary_region = "iad"\n'
RAILWAY_DEPLOY = "#!/bin/sh\nrailway up --service demo\n"
CLAIM = "#!/bin/sh\nfactory claim --cap 3\n"


def declared_ctx(
    repo: RepoBuilder, *amendments: dict[str, Any], **order_fields: Any
) -> GateContext:
    repo.add_demo_feature()
    pair = order_pair(repo, {}, {}, order_for(**order_fields), *amendments)
    return order_ctx(repo, pair)


# --- order-fidelity-declared ----------------------------------------------------------------


def test_declared_blocks_touched_lock_without_entry(repo: RepoBuilder) -> None:
    ctx = declared_ctx(repo, tasks=["T002"], owned_paths=["deploy/railway/demo.toml"], locks=[])
    assert_blocks(DECLARED, ctx, "D1")


@pytest.mark.parametrize(
    "lock",
    [
        RAILWAY_LOCK,
        {"id": "D1", "letter_tokens": ["railway"], "fidelity": "intent"},
        {"id": "D1", "letter_tokens": [], "fidelity": "waived", "waiver_ref": "bus/decisions/x"},
    ],
    ids=["letter", "intent", "waived"],
)
def test_declared_passes_when_the_touched_lock_has_an_entry(
    repo: RepoBuilder, lock: dict[str, Any]
) -> None:
    ctx = declared_ctx(repo, tasks=["T002"], owned_paths=["deploy/railway/demo.toml"], locks=[lock])
    assert_passes(DECLARED, ctx)


def test_declared_passes_when_no_named_lock_is_touched(repo: RepoBuilder) -> None:
    ctx = declared_ctx(
        repo, tasks=["T001"], owned_paths=["apps/demo/app/calc.py"], goal="Add add().", locks=[]
    )
    assert_passes(DECLARED, ctx)


def test_declared_blocks_when_only_a_different_lock_is_declared(repo: RepoBuilder) -> None:
    """Any lock entry is not enough; the touched lock's id must be declared."""
    other = {"id": "D2", "letter_tokens": ["70%"], "fidelity": "letter"}
    ctx = declared_ctx(
        repo, tasks=["T002"], owned_paths=["deploy/railway/demo.toml"], locks=[other]
    )
    assert_blocks(DECLARED, ctx, "D1")


def test_declared_blocks_when_owned_paths_alone_touch_the_lock(repo: RepoBuilder) -> None:
    """The rule names owned paths: owning the file that the D1 task names touches D1,
    even when the order lists no task."""
    ctx = declared_ctx(repo, tasks=[], owned_paths=["deploy/railway/demo.toml"], locks=[])
    assert_blocks(DECLARED, ctx, "D1")


def test_declared_judges_the_effective_order_after_amendments(repo: RepoBuilder) -> None:
    amendment = amendment_for(
        ORDER_ID, 1, tasks=["T001", "T002"], owned_paths=["apps/demo/**", "deploy/railway/**"]
    )
    ctx = declared_ctx(
        repo, amendment, tasks=["T001"], owned_paths=["apps/demo/app/calc.py"], locks=[]
    )
    assert_blocks(DECLARED, ctx, "D1")


def test_declared_accepts_a_lock_added_by_amendment(repo: RepoBuilder) -> None:
    amendment = amendment_for(ORDER_ID, 1, locks=[RAILWAY_LOCK])
    ctx = declared_ctx(
        repo, amendment, tasks=["T002"], owned_paths=["deploy/railway/demo.toml"], locks=[]
    )
    assert_passes(DECLARED, ctx)


def test_declared_blocks_when_the_feature_folder_is_missing(repo: RepoBuilder) -> None:
    """Fail closed: locks cannot be discovered for a feature that does not exist."""
    ctx = declared_ctx(repo, feature="ghost-feature", tasks=["T002"], locks=[])
    assert_blocks(DECLARED, ctx, "ghost-feature")


def test_declared_blocks_when_the_order_is_missing_at_head(repo: RepoBuilder) -> None:
    repo.add_demo_feature()
    pair = repo.base_head_pair({}, {"README.md": "# edited\n"}, head_branch="wo/x")
    ctx = repo.gate_context(pair, order_id=oid("never-issued"), pr_number=1)
    assert_blocks(DECLARED, ctx, oid("never-issued"))


# --- lock.letter-tokens ---------------------------------------------------------------------


def tokens_ctx(
    repo: RepoBuilder,
    head_files: dict[str, str | None],
    *,
    locks: list[dict[str, Any]],
    base_files: dict[str, str] | None = None,
) -> GateContext:
    repo.add_demo_feature()
    data = order_for(
        tasks=["T002"], owned_paths=["deploy/**", "docs/**", "scripts/**"], locks=locks
    )
    pair = order_pair(repo, base_files or {}, head_files, data)
    return order_ctx(repo, pair)


@pytest.mark.parametrize(
    "lock",
    [
        {"id": "D1", "letter_tokens": ["railway"], "fidelity": "intent"},
        {"id": "D1", "letter_tokens": ["railway"], "fidelity": "waived", "waiver_ref": "bus/x"},
    ],
    ids=["intent", "waived"],
)
def test_tokens_only_enforce_letter_fidelity(repo: RepoBuilder, lock: dict[str, Any]) -> None:
    ctx = tokens_ctx(repo, {"deploy/fly/demo.toml": FLY_CONFIG}, locks=[lock])
    assert_passes(TOKENS, ctx)


def test_tokens_pass_when_every_letter_lock_is_honored(repo: RepoBuilder) -> None:
    ctx = tokens_ctx(
        repo,
        {"scripts/deploy.sh": RAILWAY_DEPLOY, "scripts/claim.sh": CLAIM},
        locks=[RAILWAY_LOCK, CAP_LOCK],
    )
    assert_passes(TOKENS, ctx)


def test_tokens_block_names_the_one_violated_lock(repo: RepoBuilder) -> None:
    ctx = tokens_ctx(
        repo,
        {
            "scripts/deploy.sh": RAILWAY_DEPLOY,
            "scripts/claim.sh": "#!/bin/sh\nfactory claim --cap 4\n",
        },
        locks=[RAILWAY_LOCK, CAP_LOCK],
        base_files={"scripts/claim.sh": CLAIM},
    )
    assert_blocks(TOKENS, ctx, "D8")


@pytest.mark.parametrize(
    ("path", "text"),
    [
        ("scripts/deploy.js", "// deploy with railway\nconst region = 'iad';\n"),
        ("scripts/deploy.js", "/* railway was the host */\nconst region = 'iad';\n"),
        ("scripts/deploy.js", "/**\n * railway host notes\n */\nconst region = 'iad';\n"),
        ("scripts/migrate.sql", "-- railway postgres\nSELECT 1;\n"),
    ],
    ids=["double-slash", "block-comment", "star-continuation", "double-dash"],
)
def test_tokens_in_comment_only_lines_do_not_honor(repo: RepoBuilder, path: str, text: str) -> None:
    ctx = tokens_ctx(repo, {path: text, "deploy/fly/demo.toml": FLY_CONFIG}, locks=[RAILWAY_LOCK])
    assert_blocks(TOKENS, ctx, "D1")


def test_tokens_are_honored_case_insensitively(repo: RepoBuilder) -> None:
    ctx = tokens_ctx(repo, {"deploy/demo.toml": 'provider = "RAILWAY"\n'}, locks=[RAILWAY_LOCK])
    assert_passes(TOKENS, ctx)


def test_tokens_in_an_unchanged_file_do_not_honor_the_diff(repo: RepoBuilder) -> None:
    """The PR's own code must honor the lock; Railway config already on base does not
    excuse a change that deploys to another host."""
    ctx = tokens_ctx(
        repo,
        {"deploy/fly/demo.toml": FLY_CONFIG},
        locks=[RAILWAY_LOCK],
        base_files={"deploy/railway/demo.toml": 'builder = "railway"\n'},
    )
    assert_blocks(TOKENS, ctx, "D1")


@pytest.mark.parametrize(
    ("head_files", "base_files"),
    [
        ({"scripts/deploy.sh": "#!/bin/sh\n# moved off flyctl in 2026\nrailway up\n"}, None),
        (
            {
                "scripts/deploy.sh": RAILWAY_DEPLOY,
                "docs/deploy.md": "# Deploy\n\nWe no longer use flyctl.\n",
            },
            None,
        ),
        (
            {"scripts/deploy.sh": RAILWAY_DEPLOY},
            {"scripts/deploy.sh": "#!/bin/sh\nflyctl deploy\n"},
        ),
    ],
    ids=["substitute-in-comment", "substitute-in-docs", "substitute-deleted"],
)
def test_substitute_outside_added_code_passes(
    repo: RepoBuilder, head_files: dict[str, str], base_files: dict[str, str] | None
) -> None:
    lock = {**RAILWAY_LOCK, "substitutes": ["fly", "flyctl"]}
    ctx = tokens_ctx(repo, head_files, locks=[lock], base_files=base_files)
    assert_passes(TOKENS, ctx)


def test_tokens_pass_for_an_order_without_letter_locks(repo: RepoBuilder) -> None:
    """Nothing to honor; whether the order should have declared a lock is
    `order-fidelity-declared`'s question."""
    ctx = tokens_ctx(repo, {"scripts/deploy.sh": RAILWAY_DEPLOY}, locks=[])
    assert_passes(TOKENS, ctx)


def test_tokens_block_when_the_order_is_missing_at_head(repo: RepoBuilder) -> None:
    repo.add_demo_feature()
    pair = repo.base_head_pair({}, {"scripts/deploy.sh": RAILWAY_DEPLOY}, head_branch="wo/x")
    ctx = repo.gate_context(pair, order_id=oid("never-issued"), pr_number=1)
    assert_blocks(TOKENS, ctx, oid("never-issued"))
