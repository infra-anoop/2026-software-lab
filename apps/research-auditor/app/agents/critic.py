import logfire
from pydantic_ai import Agent
from app.agents.models import ResearchOutput, AuditFeedback

# OPENAI_API_KEY is read at runtime by pydantic_ai; enforced at CLI entrypoint (main.py).
critic_agent = Agent(
    'openai:gpt-4o',
    output_type=AuditFeedback,
    system_prompt=(
        "You are an Industrial Auditor. You receive structured research "
        "and must verify if the findings are technically sound and well-supported "
        "by the provided quotes. Be strict. If the confidence_score is below 0.9, "
        "mark it as NEEDS_REVISION."
    ),
)


async def run_audit(research_data: ResearchOutput):
    with logfire.span("llm.critic", agent="critic"):
        result = await critic_agent.run(
            f"Review this research: {research_data.model_dump_json()}"
        )
    return result.output
