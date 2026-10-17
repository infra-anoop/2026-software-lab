#!/usr/bin/env python3
"""Deterministic controller for the design-review loop.

Every decision the workflow branches on is computed here, in code:
round numbering, schema validation, convergence, the round cap, escalation.
Agents only write files; this script judges them.

  python .factory/bin/factory.py schemas                       # regenerate JSON Schemas
  python .factory/bin/factory.py reset spec|plan               # archive old history
  python .factory/bin/factory.py prepare spec|plan             # start a round
  python .factory/bin/factory.py check spec|plan [--strict] [--record]

Prints one JSON object (LoopState) on stdout for the workflow's
`output_format: json`. Exits 0 unless --strict and something is invalid.
"""
import glob
import json
import sys
from pathlib import Path

from pydantic import ValidationError

ROOT = Path(__file__).resolve().parents[1]           # .factory/
sys.path.insert(0, str(ROOT / "schemas"))
from packets import LoopState, ReviewVerdict, RevisionReport  # noqa: E402

CONFIG = json.loads((ROOT / "config.json").read_text())


def stage_dir(stage: str) -> Path:
    return ROOT / "reviews" / stage


def rounds_done(stage: str) -> int:
    ledger = stage_dir(stage) / "ledger.jsonl"
    if not ledger.exists():
        return 0
    return sum(1 for line in ledger.read_text().splitlines() if line.strip())


def round_dir(stage: str, n: int) -> Path:
    return stage_dir(stage) / f"round-{n}"


def roles(stage: str) -> list[dict]:
    return CONFIG["stages"][stage]["roles"]


def load_verdicts(stage: str, n: int):
    """Validate every reviewer file for round n. Returns (valid, errors)."""
    valid, errors = {}, {}
    for role in roles(stage):
        path = round_dir(stage, n) / f"{role['name']}.json"
        if not path.exists():
            errors[str(path)] = "file missing"
            continue
        try:
            verdict = ReviewVerdict.model_validate_json(path.read_text())
            if verdict.role != role["name"] or verdict.stage != stage or verdict.round != n:
                raise ValueError(f"role/stage/round must be {role['name']}/{stage}/{n}")
            valid[role["name"]] = verdict
        except (ValidationError, ValueError) as exc:
            errors[str(path)] = str(exc)
    return valid, errors


def load_revision(stage: str, n: int, strict: bool):
    path = round_dir(stage, n) / "revision.json"
    if not path.exists():
        if strict:
            fail(f"{path} missing: the reviser did not write its report")
        return None
    try:
        return RevisionReport.model_validate_json(path.read_text())
    except ValidationError as exc:
        if strict:
            fail(f"{path} invalid: {exc}")
        return None


def blocking(verdicts) -> list:
    sev = set(CONFIG["blocking_severities"])
    floor = CONFIG["confidence_threshold"]
    return [f for v in verdicts.values() for f in v.findings
            if f.severity in sev and f.confidence >= floor]


def fail(message: str):
    print(json.dumps({"error": message}))
    sys.exit(1)


def emit(state: LoopState):
    print(state.model_dump_json())


def cmd_schemas():
    for model in (ReviewVerdict, RevisionReport):
        out = ROOT / "schemas" / f"{model.__name__}.schema.json"
        out.write_text(json.dumps(model.model_json_schema(), indent=2))
    print(json.dumps({"ok": True}))


def cmd_reset(stage: str):
    """Archive any previous review history for this stage, so round numbering restarts."""
    import time
    d = stage_dir(stage)
    if d.exists():
        d.rename(d.with_name(f"{stage}-archived-{time.strftime('%Y%m%d-%H%M%S')}"))
    print(json.dumps({"ok": True}))


def cmd_prepare(stage: str):
    n = rounds_done(stage) + 1
    rdir = round_dir(stage, n)
    rdir.mkdir(parents=True, exist_ok=True)

    artifacts = sorted({p for pat in CONFIG["stages"][stage]["artifacts"] for p in glob.glob(pat)})
    lines = [f"# Review context: stage `{stage}`, round {n}", "",
             "## Artifacts to review", *[f"- `{a}`" for a in artifacts], ""]

    if n > 1:
        prev, _ = load_verdicts(stage, n - 1)
        revision = load_revision(stage, n - 1, strict=True)
        lines += ["## Findings open after the previous round", ""]
        for v in prev.values():
            for f in v.findings:
                lines.append(f"- `{f.id}` ({f.severity}, {f.confidence}) {f.issue}")
        lines += ["", "## Reviser's dispositions", ""]
        for d in revision.dispositions:
            lines.append(f"- `{d.finding_id}`: **{d.action}**: {d.rationale}")
        lines += ["", "Re-check each previous finding. Put fixed ones in `resolved`.",
                  "Keep the same id if an issue persists. Do not re-raise a rejected",
                  "finding unless you can add new evidence.", ""]

    (rdir / "context.md").write_text("\n".join(lines))
    emit(LoopState(stage=stage, round=n, roles=roles(stage)))


def cmd_check(stage: str, strict: bool, record: bool):
    n = rounds_done(stage) + 1
    rdir = round_dir(stage, n)
    verdicts, errors = load_verdicts(stage, n)

    if errors:
        (rdir / "errors.md").write_text(
            "# Schema validation errors\n\n"
            + "\n".join(f"## `{p}`\n\n```\n{e}\n```\n" for p, e in errors.items()))
        state = LoopState(stage=stage, round=n, all_valid=False, invalid_files=sorted(errors))
        if strict:
            emit(state)
            sys.exit(1)
        emit(state)
        return

    open_blocking = blocking(verdicts)
    human = []
    if n > 1:
        rev = load_revision(stage, n - 1, strict=False)
        open_ids = {f.id for f in open_blocking}
        human = [d for d in (rev.dispositions if rev else [])
                 if d.action == "needs_human" and d.finding_id in open_ids]

    converged = not open_blocking
    cap_hit = n >= CONFIG["max_rounds"]
    continue_loop = not converged and not cap_hit and not human
    state = LoopState(stage=stage, round=n, open_blocking=len(open_blocking),
                      converged=converged, continue_loop=continue_loop,
                      needs_escalation=not converged and not continue_loop)

    if record:
        all_open = [f for v in verdicts.values() for f in v.findings]
        (rdir / "open-findings.md").write_text(
            "# Open findings to address\n\n"
            + "\n".join(f"- `{f.id}` [{f.severity}, confidence {f.confidence}] "
                        f"`{f.artifact}` > {f.section}: {f.issue}\n  - Recommendation: {f.recommendation}"
                        for f in all_open))
        with (stage_dir(stage) / "ledger.jsonl").open("a") as fh:
            fh.write(state.model_dump_json(exclude={"roles"}) + "\n")
        if state.needs_escalation:
            reason = ("the reviser asked for a human decision" if human
                      else f"not converged after {n} round(s)")
            rows = "\n".join(f"| `{f.id}` | {f.severity} | {f.confidence} | {f.issue} | {f.recommendation} |"
                             for f in open_blocking)
            asks = "\n".join(f"- `{d.finding_id}`: {d.rationale}" for d in human) or "- none"
            (stage_dir(stage) / "escalation.md").write_text(
                f"# Escalation: stage `{stage}`\n\nReason: {reason}.\n\n"
                "| Finding | Severity | Confidence | Issue | Recommendation |\n|---|---|---|---|---|\n"
                f"{rows}\n\n## Decisions the reviser needs from you\n\n{asks}\n\n"
                "Edit the artifacts or accept the risk, then approve to continue or reject to stop.\n")
    emit(state)


def main(argv):
    if not argv:
        fail("usage: factory.py schemas | reset <stage> | prepare <stage> | check <stage> [--strict] [--record]")
    cmd = argv[0]
    if cmd == "schemas":
        return cmd_schemas()
    if len(argv) < 2 or argv[1] not in CONFIG["stages"]:
        fail(f"stage must be one of {list(CONFIG['stages'])}")
    if cmd == "reset":
        return cmd_reset(argv[1])
    if cmd == "prepare":
        return cmd_prepare(argv[1])
    if cmd == "check":
        return cmd_check(argv[1], "--strict" in argv, "--record" in argv)
    fail(f"unknown command {cmd}")


if __name__ == "__main__":
    main(sys.argv[1:])
