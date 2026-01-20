import asyncio
import os
import logfire
from supabase import create_client, Client
from graph import app

# 1. Environment & Observability
logfire.configure()
logfire.instrument_pydantic_ai()

# Initialize Supabase
url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(url, key)

async def save_to_supabase(final_state):
    """Saves the agent's final state to the research_audits table."""
    try:
        # Map our Pydantic/TypedDict state to the SQL table structure
        data = {
            "title": final_state['research'].source_material_title,
            "findings": [f.model_dump() for f in final_state['research'].key_findings],
            "verdict": final_state['feedback'].verdict,
            "critique": final_state['feedback'].critique_points,
            "iterations": final_state['iterations']
        }
        
        result = supabase.table("research_audits").insert(data).execute()
        print(f"✅ State successfully persisted to Supabase (ID: {result.data[0]['id']})")
    except Exception as e:
        print(f"❌ Supabase Error: {e}")

async def main():
    initial_input = {
        "raw_input": "Project X-14 uses a Liquid Salt Cooling system. It operates at 700°C.",
        "iterations": 0
    }

    print("--- Starting Industrial Audit Workflow ---")
    
    # Execute the Graph
    final_state = await app.ainvoke(initial_input)

    print("\n--- Workflow Complete ---")
    print(f"Final Verdict: {final_state['feedback'].verdict} ({final_state['iterations']} iterations)")
    
    # 2. Persist the results
    await save_to_supabase(final_state)

if __name__ == "__main__":
    asyncio.run(main())