from typing import Protocol


class RunRepo(Protocol):
    """Protocol for run and turn persistence."""
    
    def create_run(self, topic: str) -> str:
        """Create a new run and return its ID."""
        ...
    
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
        ...
    
    def finalize_run(
        self,
        run_id: str,
        status: str,
        final_output: dict | None = None,
        error: str | None = None,
        trace_id: str | None = None,
    ) -> None:
        """Finalize a run with status and optional metadata."""
        ...
