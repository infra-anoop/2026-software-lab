import logfire
from pydantic_ai import Agent
from app.agents.models import ResearchOutput

# OPENAI_API_KEY is read at runtime by pydantic_ai; enforced at CLI entrypoint (main.py).
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
    with logfire.span("llm.researcher", agent="researcher"):
        result = await researcher_agent.run(text_input)
    # The result.data is now a validated ResearchOutput object, NOT a string!
    return result.output
