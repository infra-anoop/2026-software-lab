import asyncio
import os
import sys
import tomllib
from pathlib import Path

from dotenv import load_dotenv
import logfire

from app.db.client import get_supabase_client
from app.orchestrator.run import run_workflow

# CLI: --version / -V (exit before running workflow, which needs OPENAI_API_KEY)
if "--version" in sys.argv or "-V" in sys.argv:
    pyproject = Path(__file__).resolve().parent.parent / "pyproject.toml"
    with open(pyproject, "rb") as f:
        version = tomllib.load(f)["project"]["version"]
    print(version)
    sys.exit(0)

load_dotenv()

# 1. Environment & Observability (token from env e.g. GitHub Codespaces secrets, not .logfire)
if os.getenv("LOGFIRE_TOKEN"):
    logfire.configure()
    logfire.instrument_pydantic_ai()
else:
    print("Logfire disabled: LOGFIRE_TOKEN not set")

# Single shared Supabase client (used for research_audits here; runs/turns via orchestrator repo)
supabase = get_supabase_client()


def save_to_supabase(final_state):
    """Saves the agent's final state to the research_audits table."""
    if supabase is None:
        return
    
    try:
        # Map our Pydantic/TypedDict state to the SQL table structure
        data = {
            "title": final_state['research'].source_material_title,
            # "findings": [f.model_dump() for f in final_state['research'].key_findings],
            "findings": final_state['research'].key_findings,
            "verdict": final_state['feedback'].verdict,
            "critique": final_state['feedback'].critique_points,
            "iterations": final_state['iterations']
        }
        
        result = supabase.table("research_audits").insert(data).execute()
        print(f"✅ State successfully persisted to Supabase (ID: {result.data[0]['id']})")
    except Exception as e:
        print(f"❌ Supabase Error: {e}")

async def main():
    key = os.getenv("OPENAI_API_KEY")
    if not key or not key.strip():
        print("❌ ERROR: OPENAI_API_KEY not found in environment variables.")
        sys.exit(1)

    initial_input = {
        "raw_input": "Project X-14 uses a Liquid Salt Cooling system. It operates at 700°C.",
        "iterations": 0
    }

    print("--- Starting Industrial Audit Workflow ---")
    
    try:
        # Execute the Graph (run_workflow persists runs/turns; returns same state shape)
        final_state = await run_workflow(initial_input)

        print("\n--- Workflow Complete ---")
        print(f"Final Verdict: {final_state['feedback'].verdict} ({final_state['iterations']} iterations)")
        
        # 2. Persist the results
        save_to_supabase(final_state)
    except Exception as e:
        error_msg = str(e)
        
        # Check for OpenAI API errors
        if "429" in error_msg or "quota" in error_msg.lower() or "RateLimitError" in str(type(e).__name__):
            print("\n❌ OpenAI API Error: Quota Exceeded")
            print("   Your OpenAI API key has exceeded its quota limit.")
            print("   Please check your OpenAI account billing and usage limits.")
            print(f"   Error details: {error_msg}")
        elif "ModelHTTPError" in str(type(e).__name__) or "openai" in error_msg.lower():
            print("\n❌ OpenAI API Error")
            print("   Failed to communicate with OpenAI API.")
            print(f"   Error: {error_msg}")
        else:
            print(f"\n❌ Workflow Error: {error_msg}")
        
        raise

if __name__ == "__main__":
    asyncio.run(main())