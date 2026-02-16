import os
import sys
from dotenv import load_dotenv
from pydantic_ai import Agent
from app.agents.models import ResearchOutput

# We no longer strictly need load_dotenv() if using platform secrets,
# but keeping it doesn't hurt for local fallback.
from dotenv import load_dotenv
load_dotenv()


api_key = os.getenv("OPENAI_API_KEY")

if not api_key:
    print("❌ ERROR: OPENAI_API_KEY not found in environment variables.")
    sys.exit(1)


# We define the agent and tell it exactly what its "Result Type" must be.
researcher_agent = Agent(
    'openai:gpt-4o',  # Or your preferred model
    output_type=ResearchOutput,
    system_prompt=(
        "You are a Senior Industrial Researcher. Your job is to extract "
        "technical facts from raw text. You must provide quotes for every claim."
    ),
)

# This is a test function to verify the "Contract" works.


async def run_research(text_input: str):
    result = await researcher_agent.run(text_input)
    # The result.data is now a validated ResearchOutput object, NOT a string!
    return result.output
