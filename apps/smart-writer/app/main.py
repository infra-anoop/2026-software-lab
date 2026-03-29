import argparse
import asyncio
import json
import os
import sys
import tomllib
from pathlib import Path

import logfire

from app.config import get_max_concurrent_llm, init_env, require_openai_api_key
from app.db.null_repo import NullRepo

_APP_ROOT = Path(__file__).resolve().parent.parent


def _print_version() -> None:
    pyproject = _APP_ROOT / "pyproject.toml"
    with open(pyproject, "rb") as f:
        version = tomllib.load(f)["project"]["version"]
    print(version)


DEFAULT_DEMO_PROMPT = (
    "Write a short persuasive two paragraphs for a nonprofit annual report: "
    "why literacy programs deserve continued funding."
)


def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Smart Writer CLI: decode values → rubrics → writer ↔ assess loop.",
    )
    p.add_argument("--version", "-V", action="store_true", help="Print version and exit")
    p.add_argument(
        "--prompt",
        "-p",
        type=str,
        default=None,
        metavar="TEXT",
        help="Writing prompt (task, audience, tone, length).",
    )
    p.add_argument(
        "--prompt-file",
        "-f",
        type=Path,
        default=None,
        metavar="PATH",
        help="Read prompt from a UTF-8 text file.",
    )
    p.add_argument(
        "--max-iterations",
        "-n",
        type=int,
        default=2,
        metavar="N",
        help="Max writer iterations (draft → assess → merge cycles). Default: 2.",
    )
    p.add_argument(
        "--output",
        "-o",
        type=Path,
        default=None,
        metavar="PATH",
        help="Write final draft and metadata as Markdown to this file.",
    )
    p.add_argument(
        "--print-draft",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Print the final draft to stdout after the summary (default: yes).",
    )
    p.add_argument(
        "--grounding/--no-grounding",
        dest="grounding",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Enable retrieval + grounding assessor (default: on). Use --no-grounding for rubric-only loop.",
    )
    p.add_argument(
        "--reference-file",
        type=Path,
        default=None,
        metavar="PATH",
        help="Optional UTF-8 file appended as reference_material for evidence (same as HTTP field).",
    )
    p.add_argument(
        "--prompt-profile",
        type=str,
        default=None,
        metavar="ID",
        help="Optional prompt profile (profiles/<id>.txt under the prompt program directory).",
    )
    p.add_argument(
        "--prompt-params",
        type=Path,
        default=None,
        metavar="PATH",
        help="JSON file with keys audience, writing_register, length_target, risk_tolerance, formality (optional).",
    )
    p.add_argument(
        "--prompt-program",
        type=str,
        default=None,
        metavar="ID",
        help="Prompt program directory name under app/prompts/programs/ (default: smart_writer_default).",
    )
    p.add_argument(
        "--research-planning/--no-research-planning",
        dest="research_planning",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Enable or disable the research/planning step after rubrics (default: profile manifest + env).",
    )
    p.add_argument(
        "--force-research-planning",
        action="store_true",
        help="Run planning even when the short-prompt heuristic would skip it.",
    )
    return p


def _resolve_raw_input(args: argparse.Namespace) -> str:
    if args.prompt_file is not None and args.prompt is not None:
        print("❌ Use either --prompt or --prompt-file, not both.", file=sys.stderr)
        sys.exit(2)
    if args.prompt_file is not None:
        path = args.prompt_file.expanduser()
        if not path.is_file():
            print(f"❌ Not a file: {path}", file=sys.stderr)
            sys.exit(2)
        return path.read_text(encoding="utf-8").strip()
    if args.prompt is not None:
        return args.prompt.strip()
    print(
        "(No --prompt or --prompt-file; using built-in demo prompt.)",
        file=sys.stderr,
    )
    return DEFAULT_DEMO_PROMPT


def _markdown_output(
    stop: str,
    iterations: int,
    aggregate: float | None,
    draft: str,
    run_id: str | None,
) -> str:
    agg = aggregate if aggregate is not None else 0.0
    rid = run_id or ""
    lines = [
        "# Smart Writer — output",
        "",
        f"- **Stop:** {stop}",
        f"- **Writer iterations:** {iterations}",
        f"- **Aggregate value score:** {agg}",
    ]
    if rid:
        lines.append(f"- **run_id:** `{rid}`")
    lines.extend(["", "## Draft", "", draft, ""])
    return "\n".join(lines)


def print_supabase_cli_note(final_state: dict) -> None:
    """Explain whether DB persistence actually ran (``NullRepo`` = nothing written)."""
    from app.orchestrator.run import get_repo

    repo = get_repo()
    if isinstance(repo, NullRepo):
        print(
            "Supabase: persistence disabled — no rows written. "
            "Set SUPABASE_URL and SUPABASE_SECRET_KEY in apps/smart-writer/.env "
            "(or export them). Check startup for: Supabase disabled: missing …"
        )
        return
    rid = final_state.get("run_id")
    if rid:
        print(
            f"✅ Supabase: trace stored in `public.runs` and `public.turns` (run_id={rid}). "
            "Open Table Editor → runs.final_output for the draft summary."
        )
    else:
        print(
            "✅ Supabase: trace stored in `public.runs` and `public.turns` "
            "(see runs.final_output)."
        )


async def async_main(args: argparse.Namespace) -> None:
    require_openai_api_key()

    from app.orchestrator.run import run_workflow, _infer_stop_reason

    raw_input = _resolve_raw_input(args)
    if args.max_iterations < 1:
        print("❌ --max-iterations must be at least 1.", file=sys.stderr)
        sys.exit(2)

    ref_text: str | None = None
    if args.reference_file is not None:
        rf = args.reference_file.expanduser()
        if not rf.is_file():
            print(f"❌ Not a file: {rf}", file=sys.stderr)
            sys.exit(2)
        ref_text = rf.read_text(encoding="utf-8").strip() or None

    initial_input: dict = {
        "raw_input": raw_input,
        "iterations": 0,
        "max_iterations": args.max_iterations,
        "max_concurrent_llm": get_max_concurrent_llm(),
        "grounding_enabled": args.grounding,
        "reference_material": ref_text,
    }
    if args.prompt_program:
        initial_input["prompt_program_id"] = args.prompt_program.strip()
    if args.prompt_profile:
        initial_input["prompt_profile_id"] = args.prompt_profile.strip()
    if args.prompt_params is not None:
        pp_path = args.prompt_params.expanduser()
        if not pp_path.is_file():
            print(f"❌ Not a file: {pp_path}", file=sys.stderr)
            sys.exit(2)
        try:
            initial_input["prompt_parameters"] = json.loads(pp_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            print(f"❌ Invalid JSON in --prompt-params: {e}", file=sys.stderr)
            sys.exit(2)
    if args.research_planning is not None:
        initial_input["research_planning_enabled"] = args.research_planning
    if args.force_research_planning:
        initial_input["force_research_planning"] = True

    print("--- Starting Smart Writer workflow ---")

    try:
        final_state = await run_workflow(initial_input)

        print("\n--- Workflow Complete ---")
        stop = _infer_stop_reason(final_state)
        iterations = final_state.get("iterations", 0)
        aggregate = final_state.get("aggregate_value_score")
        draft = final_state.get("draft") or ""

        print(
            f"Stop: {stop} ({iterations} writer iterations, aggregate={aggregate})"
        )
        rid = final_state.get("run_id")
        if rid:
            print(f"run_id: {rid}")

        print_supabase_cli_note(final_state)

        if args.output is not None:
            args.output.expanduser().write_text(
                _markdown_output(stop, iterations, aggregate, draft, rid),
                encoding="utf-8",
            )
            print(f"\nWrote Markdown to {args.output.resolve()}")

        if args.print_draft:
            print("\n--- Final draft ---\n")
            print(draft)
    except Exception as e:
        error_msg = str(e)

        if "429" in error_msg or "RateLimitError" in str(type(e).__name__):
            if (
                "rate_limit" in error_msg.lower()
                or "tokens per min" in error_msg.lower()
                or "tpm" in error_msg.lower()
            ):
                print("\n❌ OpenAI rate limit (TPM/RPM)")
                print("   Too many tokens or requests per minute for your org tier.")
                print("   Try: export SMART_WRITER_MAX_CONCURRENT_LLM=1")
                print("   Or lower max_iterations; wait a minute; see account rate limits.")
            else:
                print("\n❌ OpenAI API Error: Quota / billing")
                print("   Check billing and usage limits on your OpenAI account.")
            print(f"   Error details: {error_msg}")
        elif "ModelHTTPError" in str(type(e).__name__) or "openai" in error_msg.lower():
            print("\n❌ OpenAI API Error")
            print("   Failed to communicate with OpenAI API.")
            print(f"   Error: {error_msg}")
        else:
            print(f"\n❌ Workflow Error: {error_msg}")

        raise


def main() -> None:
    init_env()
    args = build_arg_parser().parse_args()
    if args.version:
        _print_version()
        return

    if os.getenv("LOGFIRE_TOKEN"):
        logfire.configure()
        logfire.instrument_pydantic_ai()
    else:
        print("Logfire disabled: LOGFIRE_TOKEN not set")

    asyncio.run(async_main(args))


if __name__ == "__main__":
    main()
