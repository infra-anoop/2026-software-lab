import asyncio
import os
import sys

# CLI: --version / -V before any imports that need OPENAI_API_KEY (e.g. agents)
if "--version" in sys.argv or "-V" in sys.argv:
    from pathlib import Path
    import tomllib
    pyproject = Path(__file__).resolve().parent.parent / "pyproject.toml"
    with open(pyproject, "rb") as f:
        version = tomllib.load(f)["project"]["version"]
    print(version)
    sys.exit(0)

import logfire
from supabase import create_client, Client
from app.orchestrator.run import app

# 1. Environment & Observability (token from env e.g. GitHub Codespaces secrets, not .logfire)
if os.getenv("LOGFIRE_TOKEN"):
    logfire.configure()
    logfire.instrument_pydantic_ai()
else:
    print("Logfire disabled: LOGFIRE_TOKEN not set")


# Initialize Supabase
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_SECRET_KEY")
supabase: Client | None = None
if url and key and url.strip() and key.strip():
    try:
        supabase = create_client(url, key)
    except Exception as e:
        print("Supabase disabled: invalid SUPABASE_URL or SUPABASE_SECRET_KEY")
        print(f"Supabase error: {type(e).__name__}: {e}")
        supabase = None
else:
    print("Supabase disabled: missing SUPABASE_URL or SUPABASE_SECRET_KEY")


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
    initial_input = {
        "raw_input": "Project X-14 uses a Liquid Salt Cooling system. It operates at 700°C.",
        "iterations": 0
    }

    print("--- Starting Industrial Audit Workflow ---")
    
    try:
        # Execute the Graph
        final_state = await app.ainvoke(initial_input)

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