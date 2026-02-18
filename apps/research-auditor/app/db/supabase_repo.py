import os
from datetime import datetime
from supabase import create_client, Client
class SupabaseRepo:
    """Supabase implementation of RunRepo."""
    
    def __init__(self):
        url = os.environ.get("SUPABASE_URL")
        key = os.environ.get("SUPABASE_SECRET_KEY")
        if not url or not key:
            raise ValueError("SUPABASE_URL and SUPABASE_SECRET_KEY must be set")
        self.client: Client = create_client(url, key)
    
    def create_run(self, topic: str) -> str:
        """Create a new run and return its ID."""
        result = self.client.table("runs").insert({
            "topic": topic,
            "status": "running",
            "created_at": datetime.utcnow().isoformat(),
        }).execute()
        return result.data[0]["id"]
    
    def append_turn(
        self,
        run_id: str,
        step: int,
        agent: str,
        input: dict,
        output: dict | None,
        ok: bool,
        error: str | None,
    ) -> None:
        """Append a turn to a run."""
        self.client.table("turns").insert({
            "run_id": run_id,
            "step": step,
            "agent": agent,
            "input": input,
            "output": output,
            "ok": ok,
            "error": error,
            "created_at": datetime.utcnow().isoformat(),
        }).execute()
    
    def finalize_run(
        self,
        run_id: str,
        status: str,
        final_output: dict | None = None,
        error: str | None = None,
        trace_id: str | None = None,
    ) -> None:
        """Finalize a run with status and optional metadata."""
        update_data = {"status": status}
        
        if status in ("completed", "failed"):
            update_data["completed_at"] = datetime.utcnow().isoformat()
        
        if final_output is not None:
            update_data["final_output"] = final_output
        
        if error is not None:
            update_data["error"] = error
        
        if trace_id is not None:
            update_data["trace_id"] = trace_id
        
        self.client.table("runs").update(update_data).eq("id", run_id).execute()
