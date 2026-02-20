# app/entrypoints/http.py — FastAPI server for health checks and audit API (PORT, 0.0.0.0).
#
# Endpoints:
#   GET  /health  — Health check
#   POST /audit   — Run the research audit workflow (body: {"raw_input": "..."})
#
import os

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from app.config import init_env

init_env()

app = FastAPI(title="Research Auditor", version="0.1.0")


class AuditRequest(BaseModel):
    """Request body for POST /audit."""

    raw_input: str = Field(..., description="Raw text to audit (e.g. document excerpt, topic).")
    max_iterations: int = Field(default=8, ge=1, le=20, description="Max researcher-critic iterations.")


class AuditResponse(BaseModel):
    """Response from POST /audit."""

    verdict: str
    iterations: int
    title: str
    summary: str


@app.get("/health")
def health() -> dict:
    """Health check for load balancers and deployment probes."""
    return {"ok": True}


@app.get("/")
def root() -> dict:
    """Root: simple status."""
    return {"status": "Research Auditor server is running", "docs": "/docs"}


@app.post("/audit", response_model=AuditResponse)
async def audit(request: AuditRequest) -> AuditResponse:
    """Run the research audit workflow. Requires OPENAI_API_KEY."""
    key = os.getenv("OPENAI_API_KEY")
    if not key or not key.strip():
        raise HTTPException(status_code=503, detail="OPENAI_API_KEY not configured")

    from app.orchestrator.run import run_workflow

    initial_input = {
        "raw_input": request.raw_input,
        "iterations": 0,
        "max_iterations": request.max_iterations,
    }

    try:
        final_state = await run_workflow(initial_input)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    research = final_state["research"]
    feedback = final_state["feedback"]

    return AuditResponse(
        verdict=feedback.verdict,
        iterations=final_state["iterations"],
        title=research.source_material_title,
        summary=feedback.summary,
    )


def main() -> None:
    import uvicorn

    port = int(os.environ.get("PORT", "8080"))
    uvicorn.run(app, host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()
