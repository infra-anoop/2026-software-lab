"""T039 — `order-fidelity-declared` + `lock.letter-tokens` (T046; FR-016; I-B5).

`order-fidelity-declared`: every named lock the effective order's owned paths or goal
touch has a Lock entry. The demo feature's locked letter decision D1 (host = Railway)
is touched by task T002, which is tagged `[OD:D1]` and names `deploy/railway/demo.toml`.
A goal touches D1 when it names the decision id or one of its lock tokens as a whole
word; `D10` and `trailways` do not (T-B1).

Lock tokens (T-B2-1, orchestrator 2026-10-05). Each bold span in a locked (or re-locked)
row's status cell is an independent token, matched as a whole phrase, case-insensitively,
on word boundaries; a multiword span is never split into words. These spans are not
tokens: purely numeric or unit-only spans (`3`, `70%`, `$10`, `60 minutes`), spans
shorter than 3 characters, single generic words (`yes`, `no`, `on`, `off`, `all`,
`none`), and the leading status keyword (`locked`, `re-locked`). Links, dates, code
spans and plain prose in the cell are ignored. Numeric locks are discovered only by
their OD id. Known limitation: a goal that changes a numeric lock without naming its id
goes undiscovered here (`lock.letter-tokens` still checks declared locks).

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


GOALS_TOUCHING_D1 = pytest.mark.parametrize(
    "goal",
    ["Deploy the demo app on Railway before Friday.", "Settle the deploy host per D1 this week."],
    ids=["names-locked-value", "names-decision-id"],
)


@GOALS_TOUCHING_D1
def test_declared_blocks_when_only_the_goal_touches_the_lock(repo: RepoBuilder, goal: str) -> None:
    """Neither the task list nor the owned paths touch D1; the goal alone does."""
    ctx = declared_ctx(
        repo, goal=goal, tasks=["T001"], owned_paths=["apps/demo/app/calc.py"], locks=[]
    )
    assert_blocks(DECLARED, ctx, "D1")


@GOALS_TOUCHING_D1
def test_declared_passes_when_the_goal_touched_lock_is_declared(
    repo: RepoBuilder, goal: str
) -> None:
    ctx = declared_ctx(
        repo, goal=goal, tasks=["T001"], owned_paths=["apps/demo/app/calc.py"], locks=[RAILWAY_LOCK]
    )
    assert_passes(DECLARED, ctx)


@pytest.mark.parametrize(
    "goal",
    ["Add the trailways() fare lookup to calc.py.", "Fix the D10 retry count in calc.py."],
    ids=["value-inside-a-word", "longer-decision-id"],
)
def test_declared_goal_near_miss_does_not_touch_the_lock(repo: RepoBuilder, goal: str) -> None:
    ctx = declared_ctx(
        repo, goal=goal, tasks=["T001"], owned_paths=["apps/demo/app/calc.py"], locks=[]
    )
    assert_passes(DECLARED, ctx)


SPEC = "specs/demo-feature/spec.md"
D1_ENTRY: dict[str, Any] = {"id": "D1", "letter_tokens": [], "fidelity": "intent"}
STATUS_CELLS = {
    # specs/001-factory-v2/spec.md D2: one numeric value.
    "factory-D2": (
        "**locked** (2026-10-03) — **70%** of mutants killed on changed lines; tune at"
        " post-mortem from override counts"
    ),
    # specs/smart-writer-v2/spec.md D2: several numeric values.
    "smart-writer-D2": (
        "**locked** (2026-09-20) — max **3** write jobs / conversation; max **10** clarify"
        " turns / conversation; max **8** inner writer↔assessor turns / write job. Fail"
        " closed when hit."
    ),
    # specs/002-swv2-durable-evals/spec.md D6: a currency value.
    "durable-evals-D6": (
        "**locked** (2026-10-03) — **$10** per model-change PR; beyond that the run waits"
        " for governor approval"
    ),
    # specs/002-swv2-durable-evals/spec.md D4: provider/family values, re-locked, with
    # code spans, plain-prose providers, a date and a link.
    "durable-evals-D4": (
        "**re-locked** (2026-10-03, governor) — **OpenAI** judges (judge + support"
        " checker); the **writer is Anthropic**; bake-off writer candidates exclude"
        " OpenAI. Vault/CI key for the writer side: `ANTHROPIC_API_KEY` (production,"
        " staging, eval CI); `OPENAI_API_KEY` stays (judge in eval CI). Superseded lock"
        " (2026-10-03): Google Gemini judges, writer candidates exclude Gemini. Reconcile"
        " → [`PLAN_DELTA.md`](./PLAN_DELTA.md)"
    ),
    # specs/001-factory-v2/spec.md D4: a multiword identity/tool lock.
    "factory-D4": (
        "**locked** (2026-10-03) — **agents get their own GitHub App identity, set up"
        " during Wave 1**; governor-only actions show as unverified until the App is live"
    ),
    # Synthetic: generic, short and unit-only spans only.
    "generic-spans": (
        "**locked** (2026-10-05) — **all** rows; **no** retries; **on** by default;"
        " **CI** only; **60 minutes** at most"
    ),
}

GOALS_TOUCHING_THE_ROW = pytest.mark.parametrize(
    ("shape", "goal"),
    [
        ("factory-D2", "Raise the D1 mutation threshold after the post-mortem."),
        ("smart-writer-D2", "Lower the D1 write-job cap to 2 per conversation."),
        ("durable-evals-D6", "Raise the D1 budget for model-change PRs."),
        ("durable-evals-D4", "Route the judge through OpenAI."),
        ("durable-evals-D4", "route the judge through openai."),
        ("durable-evals-D4", "Confirm the writer is Anthropic in settings."),
        ("factory-D4", "Make sure agents get their own GitHub App identity, set up during Wave 1."),
        ("factory-D4", "Finish the D1 identity work."),
        ("generic-spans", "Settle D1 before Friday."),
    ],
    ids=[
        "numeric-by-id",
        "numerics-by-id",
        "currency-by-id",
        "provider-span",
        "provider-span-lowercase",
        "multiword-provider-span",
        "multiword-identity-span",
        "identity-by-id",
        "generic-row-by-id",
    ],
)


def row_ctx(repo: RepoBuilder, shape: str, goal: str, locks: list[dict[str, Any]]) -> GateContext:
    """D1's status cell on base is the real cell `shape`; tasks and owned paths miss D1."""
    repo.add_demo_feature()
    spec = (repo.path / SPEC).read_text(encoding="utf-8")
    row = next(line for line in spec.splitlines() if line.startswith("| **D1** |"))
    cells = row.split(" | ")
    cells[5] = STATUS_CELLS[shape]
    data = order_for(goal=goal, tasks=["T001"], owned_paths=["apps/demo/app/calc.py"], locks=locks)
    pair = order_pair(repo, {SPEC: spec.replace(row, " | ".join(cells))}, {}, data)
    return order_ctx(repo, pair)


@GOALS_TOUCHING_THE_ROW
def test_declared_blocks_a_goal_touching_a_real_row_shape(
    repo: RepoBuilder, shape: str, goal: str
) -> None:
    assert_blocks(DECLARED, row_ctx(repo, shape, goal, locks=[]), "D1")


@GOALS_TOUCHING_THE_ROW
def test_declared_passes_a_goal_touching_a_real_row_shape_when_declared(
    repo: RepoBuilder, shape: str, goal: str
) -> None:
    assert_passes(DECLARED, row_ctx(repo, shape, goal, locks=[D1_ENTRY]))


@pytest.mark.parametrize(
    ("shape", "goal"),
    [
        ("factory-D2", "Lower the mutation threshold to 60% of mutants."),
        ("smart-writer-D2", "Run the calc.py suite on 3 workers."),
        ("smart-writer-D2", "Retry 10 times, 8 seconds apart."),
        ("durable-evals-D6", "Spend at most $10 on the calc.py evals."),
        ("durable-evals-D4", "Ask the writer to cite Anthropic docs."),
        ("durable-evals-D4", "Wrap the OpenAIClient in calc.py."),
        ("durable-evals-D4", "Drop Gemini and rotate ANTHROPIC_API_KEY."),
        ("durable-evals-D4", "Update PLAN_DELTA.md after the 2026-10-03 review."),
        ("factory-D4", "Set up the GitHub App identity for the demo during Wave 1."),
        ("factory-D4", "Keep the locked rows untouched."),
        ("generic-spans", "Use all of it; no retries; turn it on in CI within 60 minutes."),
    ],
    ids=[
        "numeric-value-without-id",
        "numeric-in-prose",
        "numerics-in-prose",
        "currency-in-prose",
        "multiword-span-split",
        "provider-inside-a-word",
        "plain-prose-and-code-span",
        "link-and-date",
        "words-of-a-multiword-span",
        "status-keyword",
        "generic-short-and-unit-spans",
    ],
)
def test_declared_goal_missing_every_token_of_a_real_row_passes(
    repo: RepoBuilder, shape: str, goal: str
) -> None:
    """The first case is the recorded limitation: numeric locks need their OD id."""
    assert_passes(DECLARED, row_ctx(repo, shape, goal, locks=[]))


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
