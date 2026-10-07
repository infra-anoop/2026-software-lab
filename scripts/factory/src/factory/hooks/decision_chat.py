"""`decision-in-chat` (stop; CI twin `decision-request-no-ids`).

Warn-only: when the final assistant turn asks a question (outside code) and the working
tree holds no new `bus/decisions/*/request.yaml` (one not yet on `main` or
`origin/main`), a `followup_message` asks for a git decision request instead.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from factory.hooks._repo import MAIN_REFS, bus_dir, config, git_root, present

FENCED = re.compile(r"```.*?(?:```|\Z)|~~~.*?(?:~~~|\Z)", re.DOTALL)
INLINE = re.compile(r"`[^`\n]*`")
QUESTION = re.compile(r"\?(?=\s|$)")
FOLLOWUP = (
    "decision-in-chat: your last message asks the governor a question, but no new decision "
    "request is in git. Write bus/decisions/<decision-id>/request.yaml (plain A/B options, "
    "no internal ids) and point the governor at it, instead of asking in chat."
)


def _texts(content: object) -> list[str]:
    if isinstance(content, str):
        return [content]
    if not isinstance(content, list):
        return []
    return [
        part["text"]
        for part in content
        if isinstance(part, dict)
        and part.get("type") == "text"
        and isinstance(part.get("text"), str)
    ]


def final_assistant_text(transcript: Path) -> str:
    """Text the assistant wrote after the last user entry of a JSONL transcript."""
    turn: list[str] = []
    with transcript.open(encoding="utf-8") as handle:
        for line in handle:
            try:
                entry = json.loads(line)
            except ValueError:
                continue
            if not isinstance(entry, dict):
                continue
            role = entry.get("role")
            message = entry.get("message")
            content = message.get("content") if isinstance(message, dict) else None
            if role == "user":
                turn = []
            elif role == "assistant":
                turn.extend(_texts(content))
    return "\n".join(turn)


def asks_question(text: str) -> bool:
    return bool(QUESTION.search(INLINE.sub("", FENCED.sub("", text))))


def has_new_request(root: Path) -> bool:
    decisions = root / bus_dir(config(root)) / "decisions"
    if not decisions.is_dir():
        return False
    requests = sorted(
        path.relative_to(root).as_posix() for path in decisions.glob("*/request.yaml")
    )
    if not requests:
        return False
    specs = [f"{ref}:{request}" for request in requests for ref in MAIN_REFS]
    found = present(root, specs)
    return any(
        not any(found[i * len(MAIN_REFS) : (i + 1) * len(MAIN_REFS)]) for i in range(len(requests))
    )


def handle(payload: dict[str, object], root: Path) -> tuple[int, dict[str, str]]:
    status = payload.get("status")
    raw = payload.get("transcript_path")
    if status not in (None, "completed") or not isinstance(raw, str) or not raw:
        return 0, {}
    transcript = Path(raw)
    if not transcript.is_file() or not asks_question(final_assistant_text(transcript)):
        return 0, {}
    repo = git_root(root) or root
    if has_new_request(repo):
        return 0, {}
    return 0, {"followup_message": FOLLOWUP}
