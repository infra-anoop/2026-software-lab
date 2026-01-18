import os
from dotenv import load_dotenv
from pydantic_ai import Agent
from models import ResearchOutput

load_dotenv()

# We define the agent and tell it exactly what its "Result Type" must be.
researcher_agent = Agent(
    'openai:gpt-4o',  # Or your preferred model
    result_type=ResearchOutput,
    system_prompt=(
        "You are a Senior Industrial Researcher. Your job is to extract "
        "technical facts from raw text. You must provide quotes for every claim."
    ),
)

# This is a test function to verify the "Contract" works.


async def run_research(text_input: str):
    result = await researcher_agent.run(text_input)
    # The result.data is now a validated ResearchOutput object, NOT a string!
    return result.data
