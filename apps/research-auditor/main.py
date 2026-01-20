import asyncio
import logfire
from graph import app  # Import the compiled LangGraph app

# Initialize observability
logfire.configure()
logfire.instrument_pydantic_ai()

async def main():
    # 1. Prepare the initial state
    # We provide the raw text and initialize iterations to 0
    initial_input = {
        "raw_input": """
        Project X-14 uses a Liquid Salt Cooling system. 
        It operates at 700 degrees Celsius. 
        The primary safety risk is pipe corrosion.
        """,
        "iterations": 0
    }

    print("--- Starting Industrial Audit Workflow ---")

    # 2. Invoke the Graph
    # This will automatically handle the loops between Researcher and Critic
    final_state = await app.ainvoke(initial_input)

    # 3. Output the final 'Durable' result
    print("\n--- Workflow Complete ---")
    print(f"Final Verdict: {final_state['feedback'].verdict}")
    print(f"Total Iterations: {final_state['iterations']}")
    
    if final_state['feedback'].verdict == "PASS":
        print(f"Verified Title: {final_state['research'].source_material_title}")
    else:
        print(f"Audit Failed. Reasons: {final_state['feedback'].critique_points}")

if __name__ == "__main__":
    asyncio.run(main())