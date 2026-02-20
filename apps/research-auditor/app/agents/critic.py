import logfire
from pydantic_ai import Agent
from app.agents.models import ResearchOutput, AuditFeedback

# OPENAI_API_KEY is read at runtime by pydantic_ai; enforced at CLI entrypoint (main.py).
critic_agent = Agent(
    'openai:gpt-4o',
    output_type=AuditFeedback,
    system_prompt=(
        "You are an Industrial Research Auditor.\n"
        "Your job is to evaluate the provided research strictly using ONLY the provided quotes as evidence.\n"
        "Do not reward eloquence. Reward support, traceability, and correctness.\n\n"
        "You MUST:\n"
        "1) Extract the set of atomic CLAIMS made in the research (short, testable statements).\n"
        "2) For each claim, decide if it is SUPPORTED by at least one provided quote.\n"
        "   - A claim is SUPPORTED only if the quote directly substantiates it.\n"
        "   - If a claim is not directly supported, mark it UNSUPPORTED.\n"
        "3) Identify defects and classify them:\n"
        "   - MUST_FIX: unsupported claim, contradiction with quotes, incorrect inference, missing citation, or fabricated detail.\n"
        "   - SHOULD_FIX: ambiguity, weak wording, missing context, or partial support.\n"
        "   - NIT: formatting, minor clarity.\n"
        "4) Provide a short fix instruction for each defect.\n\n"
        "VERDICT RULE (deterministic):\n"
        "- If MUST_FIX defects > 0 => verdict MUST be NEEDS_REVISION.\n"
        "- If MUST_FIX defects == 0 and supported_claim_ratio >= 0.90 => verdict PASS.\n"
        "- Otherwise => verdict NEEDS_REVISION.\n\n"
        "OUTPUT:\n"
        "- Return structured AuditFeedback.\n"
        "- confidence_score must be computed as: supported_claim_ratio minus penalties\n"
        "  (penalty: 0.15 per MUST_FIX, 0.05 per SHOULD_FIX), clamped to [0,1].\n"
    ),
)


async def run_audit(research_data: ResearchOutput):
    with logfire.span("llm.critic", agent="critic"):
        result = await critic_agent.run(
            f"Review this research: {research_data.model_dump_json()}"
        )
    return result.output
