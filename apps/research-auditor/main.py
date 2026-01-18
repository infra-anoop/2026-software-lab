import asyncio
from researcher import run_research
from critic import run_audit


async def main():
    # Simulated raw technical text
    raw_input = """
    Project X-14 uses a Liquid Salt Cooling system. 
    It operates at 700 degrees Celsius. 
    The primary safety risk is pipe corrosion.
    """

    print("--- 1. Researcher is working... ---")
    research_result = await run_research(raw_input)
    print(f"Researcher found: {research_result.source_material_title}")
    print(f"Confidence: {research_result.confidence_score}")

    print("\n--- 2. Critic is auditing... ---")
    audit_result = await run_audit(research_result)
    print(f"Verdict: {audit_result.verdict}")
    print(f"Critique: {audit_result.critique_points}")

if __name__ == "__main__":
    asyncio.run(main())
