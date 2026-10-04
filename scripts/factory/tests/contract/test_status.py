"""T017 — `factory status --json` board sections match derived lifecycle reality.

Catalog: `board.matches_reality`. Red until slice A implements status (CP1).
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
import yaml

from factory.bus.models import FORBIDDEN_KEYS, find_forbidden_key
from factory.cli import exit_codes
from tests.fixtures.cli_runner import CliResult, FactoryCli
from tests.fixtures.fake_github import FakeGitHub
from tests.fixtures.repo_builder import GOVERNOR_LOGIN, RepoBuilder, message, order

pytestmark = pytest.mark.contract

DAY = "20261007"
OPEN_DECISION = "pick-host"
BOARD_SECTIONS = (
    "in_flight",
    "blocked",
    "waiting_on_governor",
    "ready",
    "overrides_per_gate",
    "unverified_governor_actions",
)


def oid(slug: str) -> str:
    return f"wo-{DAY}-{slug}"


def _ids(section: object) -> set[str]:
    assert isinstance(section, list), section
    out: set[str] = set()
    for item in section:
        assert isinstance(item, dict), item
        order_id = item.get("order_id") or item.get("id")
        assert isinstance(order_id, str) and order_id, item
        out.add(order_id)
    return out


def _card(section: object, order_id: str) -> dict[str, Any]:
    assert isinstance(section, list), section
    for item in section:
        if isinstance(item, dict) and order_id in {item.get("order_id"), item.get("id")}:
            return item
    raise AssertionError(f"{order_id} not in {section}")


def parse_board(result: CliResult) -> dict[str, Any]:
    assert result.exit_code == exit_codes.OK, (
        f"expected exit 0, got {result.exit_code}\nstdout: {result.stdout}\nstderr: {result.stderr}"
    )
    envelope = json.loads(result.stdout)
    assert envelope.get("ok") is True and envelope.get("command") == "status", envelope
    data = envelope.get("data")
    assert isinstance(data, dict), envelope
    missing = [name for name in BOARD_SECTIONS if name not in data]
    assert not missing, f"board JSON missing sections {missing}: {sorted(data)}"
    return data


def _seed_board(repo: RepoBuilder, github: FakeGitHub) -> dict[str, str]:
    """One order per lifecycle state named in T017. Returns slug → order id."""
    ids = {
        slug: oid(slug)
        for slug in (
            "issued",
            "claimed",
            "review",
            "accepted",
            "rejected",
            "merged",
            "released",
            "stale",
            "blocked",
        )
    }

    repo.checkout("main")
    repo.write_message(
        message(
            "decision_request",
            decision_id=OPEN_DECISION,
            blocking=True,
            prompt="Which host should the demo deploy to?",
        )
    )
    repo.commit("board fixture: open human decision")
    repo.push("main")

    repo.issue_order(order(ids["issued"], owned_paths=[f"apps/demo/{ids['issued']}/**"]))

    repo.issue_order(order(ids["claimed"], owned_paths=[f"apps/demo/{ids['claimed']}/**"]))
    repo.add_event(ids["claimed"], message("claim", order_id=ids["claimed"]))

    review = ids["review"]
    repo.issue_order(order(review, owned_paths=[f"apps/demo/{review}/**"]))
    repo.add_event(review, message("claim", order_id=review))
    review_pr = repo.make_pr(f"wo/{review}", title=review)
    github.add_check_run(
        review_pr.head_sha, "factory-tests", run_status="in_progress", conclusion=None
    )

    accepted = ids["accepted"]
    repo.issue_order(order(accepted, owned_paths=[f"apps/demo/{accepted}/**"]))
    repo.add_event(accepted, message("claim", order_id=accepted))
    repo.add_event(accepted, message("handoff", order_id=accepted))
    repo.add_event(accepted, message("run_complete", order_id=accepted))
    accepted_pr = repo.make_pr(f"wo/{accepted}", title=accepted)
    github.add_check_run(accepted_pr.head_sha, "factory-tests", conclusion="success")
    repo.add_event(
        accepted,
        message(
            "verdict",
            order_id=accepted,
            decision="accept",
            inputs=[{"path": f"bus/orders/{accepted}/order.yaml", "sha": accepted_pr.head_sha}],
        ),
    )
    repo.add_event(
        accepted,
        message(
            "override",
            order_id=accepted,
            actor="governor",
            actor_model=None,
            gate="red-first-proof",
            pr=accepted_pr.number,
            reason="Base suite broken by an unrelated module; new tests verified red by hand.",
            gate_class="drift",
        ),
    )

    rejected = ids["rejected"]
    repo.issue_order(order(rejected, owned_paths=[f"apps/demo/{rejected}/**"]))
    repo.add_event(rejected, message("claim", order_id=rejected))
    repo.add_event(rejected, message("handoff", order_id=rejected))
    rejected_pr = repo.make_pr(f"wo/{rejected}", title=rejected)
    github.add_check_run(rejected_pr.head_sha, "factory-tests", conclusion="success")
    repo.add_event(
        rejected,
        message(
            "verdict",
            order_id=rejected,
            decision="reject",
            inputs=[{"path": f"bus/orders/{rejected}/order.yaml", "sha": rejected_pr.head_sha}],
        ),
    )

    merged = ids["merged"]
    repo.issue_order(order(merged, owned_paths=[f"apps/demo/{merged}/**"]))
    repo.add_event(merged, message("claim", order_id=merged))
    repo.add_event(merged, message("handoff", order_id=merged))
    merged_pr = repo.make_pr(f"wo/{merged}", title=merged, open=False, merged=True)
    github.add_check_run(merged_pr.head_sha, "factory-tests", conclusion="success")
    repo.add_event(
        merged,
        message(
            "verdict",
            order_id=merged,
            decision="accept",
            inputs=[{"path": f"bus/orders/{merged}/order.yaml", "sha": merged_pr.head_sha}],
        ),
    )
    github.merge_pr(merged_pr.number)

    released = ids["released"]
    repo.issue_order(order(released, owned_paths=[f"apps/demo/{released}/**"]))
    repo.add_event(released, message("claim", order_id=released))
    repo.add_event(released, message("release", order_id=released, reason="abandoned"))

    stale = ids["stale"]
    claimed_at = datetime(2026, 10, 1, 12, 0, tzinfo=UTC)
    repo.issue_order(
        order(stale, owned_paths=[f"apps/demo/{stale}/**"], size_minutes=10),
        when=claimed_at - timedelta(minutes=5),
    )
    repo.add_event(
        stale,
        message("claim", order_id=stale, claimed_at=claimed_at.isoformat().replace("+00:00", "Z")),
        when=claimed_at,
    )

    blocked = ids["blocked"]
    repo.issue_order(
        order(
            blocked,
            owned_paths=[f"apps/demo/{blocked}/**"],
            depends_on_decisions=[OPEN_DECISION],
        )
    )
    return ids


def test_status_json_sections_match_each_lifecycle_state(
    repo: RepoBuilder, factory_cli: FactoryCli, fake_github: FakeGitHub
) -> None:
    ids = _seed_board(repo, fake_github)
    refs = repo.git("for-each-ref", "--format=%(refname:short)", "refs/heads").splitlines()
    for ref in refs:
        for path in repo.git("ls-tree", "-r", "--name-only", ref).splitlines():
            if not (path.startswith("bus/") and path.endswith((".yaml", ".yml"))):
                continue
            payload = yaml.safe_load(repo.git("show", f"{ref}:{path}"))
            where = find_forbidden_key(payload)
            assert where is None, f"{ref}:{path} has forbidden key {where} ({FORBIDDEN_KEYS})"
    board = parse_board(factory_cli("status", "--json", repo=repo.path))

    assert ids["issued"] in _ids(board["ready"])
    assert ids["claimed"] in _ids(board["in_flight"])
    review_card = _card(board["in_flight"], ids["review"])
    assert review_card.get("state") == "in_review"
    checks = review_card.get("checks") or review_card.get("check_progress")
    assert checks, f"in_review card must show running checks: {review_card}"

    assert ids["accepted"] in _ids(board["in_flight"])
    assert ids["rejected"] in (_ids(board["blocked"]) | _ids(board["in_flight"]))
    assert ids["merged"] not in _ids(board["ready"])
    assert ids["released"] not in _ids(board["in_flight"])
    assert ids["released"] not in _ids(board["ready"])

    stale_home = _ids(board["in_flight"]) | _ids(board["blocked"])
    assert ids["stale"] in stale_home
    stale_card = (
        _card(board["in_flight"], ids["stale"])
        if ids["stale"] in _ids(board["in_flight"])
        else _card(board["blocked"], ids["stale"])
    )
    overlays = stale_card.get("overlays") or []
    assert "stale" in overlays or stale_card.get("state") == "stale"

    waiting = board["waiting_on_governor"]
    assert ids["blocked"] in _ids(waiting)
    prompt = json.dumps(waiting)
    assert "Which host should the demo deploy to?" in prompt
    assert "T017" not in prompt and "FR-007" not in prompt

    overrides = board["overrides_per_gate"]
    assert isinstance(overrides, dict), overrides
    assert overrides.get("red-first-proof") == 1

    unverified = board["unverified_governor_actions"]
    assert isinstance(unverified, list) and unverified, unverified
    blob = json.dumps(unverified)
    assert GOVERNOR_LOGIN in blob or "override" in blob.lower() or ids["accepted"] in blob
