import os
import sys
from dotenv import load_dotenv
from pydantic_ai import Agent
from app.agents.models import ResearchOutput, AuditFeedback


# We no longer strictly need load_dotenv() if using platform secrets,
# but keeping it doesn't hurt for local fallback.
load_dotenv()

api_key = os.getenv("OPENAI_API_KEY")

if not api_key:
    print("❌ ERROR: OPENAI_API_KEY not found in environment variables.")
    sys.exit(1)


# The Critic Agent: Bound to the AuditFeedback model
critic_agent = Agent(
    'openai:gpt-4o',
    output_type=AuditFeedback,
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
    return result.output
