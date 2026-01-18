import os
from dotenv import load_dotenv
from pydantic_ai import Agent
from models import ResearchOutput, AuditFeedback

load_dotenv()

# The Critic Agent: Bound to the AuditFeedback model
critic_agent = Agent(
    'openai:gpt-4o',
    result_type=AuditFeedback,
    system_prompt=(
        "You are an Industrial Auditor. You receive structured research "
        "and must verify if the findings are technically sound and well-supported "
        "by the provided quotes. Be strict. If the confidence_score is below 0.7, "
        "mark it as NEEDS_REVISION."
    ),
)


async def run_audit(research_data: ResearchOutput):
    # We pass the validated object directly to the agent
    result = await critic_agent.run(
        f"Review this research: {research_data.model_dump_json()}"
    )
    return result.data
