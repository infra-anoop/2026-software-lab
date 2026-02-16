from uuid import uuid4
from app.db.repo import RunRepo


class NullRepo:
    """No-op implementation of RunRepo for testing or when persistence is disabled."""
    
    def create_run(self, topic: str) -> str:
        """Create a new run and return a UUID."""
        return str(uuid4())
    
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
        """No-op: do nothing."""
        pass
    
    def finalize_run(
        self,
        run_id: str,
        status: str,
        final_output: dict | None = None,
        error: str | None = None,
        trace_id: str | None = None,
    ) -> None:
        """No-op: do nothing."""
        pass
