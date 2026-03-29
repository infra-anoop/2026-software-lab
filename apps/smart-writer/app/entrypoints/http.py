# app/entrypoints/http.py — FastAPI server for health checks, form UI, and workflow API (PORT, 0.0.0.0).
#
# Endpoints:
#   GET  /         — Workflow form (HTML)
#   GET  /health   — Health check
#   POST /audit    — Run values→rubrics→writer loop (body: writing prompt + limits)
#
# Server-side wall-clock limit for ``/audit``: ``SMART_WRITER_AUDIT_TIMEOUT_SEC`` (see ``app.config``).
# Browser and API clients should still use a long HTTP read timeout (workflows often take minutes).
#
import asyncio
import re
import os

from typing import List, Literal

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field, field_validator

from app.config import get_audit_timeout_sec, get_max_concurrent_llm, init_env
from app.db.null_repo import NullRepo

init_env()

app = FastAPI(title="Smart Writer", version="0.1.0")

# Input limits for injection/DoS mitigation
RAW_INPUT_MAX_LEN = 10_000
CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


class PromptParametersIn(BaseModel):
    """Optional overrides for default prompt parameters (merged with env and program defaults)."""

    audience: str | None = None
    writing_register: str | None = None
    length_target: str | None = None
    risk_tolerance: str | None = None
    formality: str | None = None


def sanitize_raw_input(value: str) -> str:
    """Remove control characters and excessive whitespace; enforce length."""
    s = CONTROL_CHARS.sub("", value).strip()
    if len(s) > RAW_INPUT_MAX_LEN:
        s = s[:RAW_INPUT_MAX_LEN]
    return s


class AuditRequest(BaseModel):
    """Request body for POST /audit (writing prompt + loop controls)."""

    raw_input: str = Field(
        ...,
        min_length=1,
        max_length=RAW_INPUT_MAX_LEN,
        description="Writing prompt: what to produce, audience, tone, length, etc.",
    )
    max_iterations: int = Field(
        default=10,
        ge=1,
        le=20,
        description="Max writer iterations (draft → assess → merge cycles).",
    )
    plateau_window: int = Field(default=2, ge=1, le=10, description="Plateau: compare aggregate to score this many rounds ago.")
    plateau_epsilon: float = Field(
        default=0.5,
        ge=0.0,
        le=50.0,
        description="Domain value-track plateau: min gain on A_domain (0–25 mean) over plateau_window.",
    )
    plateau_epsilon_craft: float = Field(
        default=0.5,
        ge=0.0,
        le=50.0,
        description="Craft value-track plateau: min gain on A_craft (0–25 mean) over plateau_window.",
    )
    assess_parallel: bool = Field(default=True, description="Run value assessors in parallel (async gather).")
    max_concurrent_llm: int = Field(
        default_factory=get_max_concurrent_llm,
        ge=1,
        le=16,
        description="Cap concurrent rubric/assessor LLM calls (reduces TPM rate-limit bursts).",
    )
    plateau_epsilon_grounding: float = Field(
        default=0.05,
        ge=0.0,
        le=1.0,
        description="Plateau epsilon for grounding_score (0–1), separate from value aggregate.",
    )
    grounding_enabled: bool = Field(
        default=True,
        description="When true, retrieve evidence (if routed), run grounding assessor, and use dual stop gates.",
    )
    reference_material: str | None = Field(
        default=None,
        max_length=RAW_INPUT_MAX_LEN,
        description="Optional user reference text (same pipeline as pasted facts); may overlap raw_input.",
    )
    retrieval_mode: Literal["auto", "urls_only", "search_only", "none"] = Field(
        default="auto",
        description="How to build the evidence bundle: URLs from text, optional search, or none.",
    )
    library_enabled: bool = Field(
        default=False,
        description="When true, intended to run match_canonical_library upstream of decode (see canonical library design §9).",
    )
    library_max_matches: int | None = Field(
        default=None,
        ge=1,
        le=32,
        description="Override SMART_WRITER_LIBRARY_MAX_MATCHES for this request (optional).",
    )
    library_match_threshold: float | None = Field(
        default=None,
        ge=-1.0,
        le=1.0,
        description="Override SMART_WRITER_LIBRARY_MATCH_THRESHOLD for this request (optional).",
    )
    prompt_program_id: str | None = Field(
        default=None,
        description="Prompt bundle id (folder under app/prompts/programs/); default smart_writer_default.",
    )
    prompt_profile_id: str | None = Field(
        default=None,
        description="Optional profile suffix file profiles/<id>.txt in the program directory.",
    )
    prompt_parameters: PromptParametersIn | None = Field(
        default=None,
        description="Override default writing parameters (audience, register, length, …).",
    )
    research_planning_enabled: bool | None = Field(
        default=None,
        description=(
            "When set, enables or disables the research/planning step before drafting. "
            "When omitted, profile defaults from manifest.toml and SMART_WRITER_RESEARCH_PLANNING_DEFAULT apply."
        ),
    )
    force_research_planning: bool = Field(
        default=False,
        description="When true, run research planning even if the short-prompt heuristic would skip it.",
    )

    @field_validator("raw_input", mode="before")
    @classmethod
    def validate_raw_input(cls, v: str) -> str:
        s = sanitize_raw_input(v)
        if not s:
            raise ValueError("raw_input cannot be empty after sanitization")
        return s


class ValueScoreLine(BaseModel):
    """Per-value rubric total from the last assessment round."""

    value_id: str
    name: str
    total: int


class AuditResponse(BaseModel):
    """Response from POST /audit."""

    stop_reason: str
    iterations: int
    aggregate_value_score: float = Field(
        description="Headline weighted mean A of per-value rubric totals (0–25; value rubrics only).",
    )
    draft: str
    run_id: str | None = Field(
        default=None,
        description="Workflow id from persistence layer; correlate with public.runs when enabled.",
    )
    persistence_enabled: bool = Field(
        default=False,
        description="True when Supabase env is set and run/turn rows are written.",
    )
    value_scores: List[ValueScoreLine] = Field(default_factory=list)
    merged_feedback_preview: str = Field(
        default="",
        description="First portion of merged assessor feedback (full text can be long).",
    )
    canonical_ids_used: List[str] = Field(
        default_factory=list,
        description="Canonical library ids selected this run (empty when library off or not wired).",
    )
    library_version_aggregate: str | None = Field(
        default=None,
        description="Optional combined catalog version string for observability.",
    )


@app.get("/health")
def health() -> dict:
    """Health check for load balancers and deployment probes."""
    return {"ok": True}


AUDIT_FORM_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Smart Writer</title>
  <style>
    body { font-family: system-ui, sans-serif; max-width: 640px; margin: 2rem auto; padding: 0 1rem; }
    h1 { font-size: 1.5rem; }
    fieldset { margin-bottom: 1.5rem; border: 1px solid #ccc; padding: 1rem; }
    legend { font-weight: 600; padding: 0 0.25rem; }
    label { display: block; margin-top: 0.5rem; color: #555; font-size: 0.9rem; }
    textarea { width: 100%; min-height: 120px; box-sizing: border-box; }
    input[type="number"] { width: 5rem; }
    button { padding: 0.5rem 1rem; cursor: pointer; }
    #result { margin-top: 1rem; padding: 1rem; border: 1px solid #ccc; display: none; }
    #result.visible { display: block; }
    #result h2 { font-size: 1.1rem; margin: 0 0 0.75rem 0; }
    #result .result-row { margin-bottom: 0.5rem; }
    #result .result-summary { margin: 0.5rem 0; white-space: pre-wrap; }
    #result ol { margin: 0.25rem 0 0 1.25rem; padding: 0; }
    #result pre.draft { white-space: pre-wrap; font-size: 0.9rem; max-height: 24rem; overflow: auto; }
    .error { color: #c00; }
    .meta { font-size: 0.85rem; color: #666; margin-top: 0.5rem; }
  </style>
</head>
<body>
  <h1>Smart Writer</h1>
  <p>Describe what you want written; the pipeline decodes values, builds rubrics, then revises until stop.</p>

  <form id="audit-form">
    <fieldset>
      <legend>Writing prompt</legend>
      <label for="raw_input">What should be written (goal, audience, format, length)?</label>
      <textarea id="raw_input" name="raw_input" required maxlength="10000"
        placeholder="e.g. A 150-word nonprofit grant paragraph on why after-school programs matter."></textarea>
      <p class="meta">Max 10,000 characters. Control characters are stripped.</p>
    </fieldset>

    <fieldset>
      <legend>Maximum writer iterations</legend>
      <label for="max_iterations">Draft → assess → merge cycles (1–20). Default 10; lower for cheaper runs.</label>
      <input type="number" id="max_iterations" name="max_iterations" value="10" min="1" max="20">
    </fieldset>

    <button type="submit">Run workflow</button>
  </form>

  <div id="result" role="region" aria-live="polite"></div>

  <p class="meta"><a href="/docs">API docs</a> · <a href="/health">Health</a></p>

  <script>
    const form = document.getElementById("audit-form");
    const result = document.getElementById("result");

    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      const rawInput = document.getElementById("raw_input").value.trim();
      const maxIter = parseInt(document.getElementById("max_iterations").value, 10);

      if (!rawInput) {
        showResult("Please enter text to process.", true);
        return;
      }
      if (rawInput.length > 10000) {
        showResult("Text exceeds 10,000 characters. Please shorten it.", true);
        return;
      }
      if (isNaN(maxIter) || maxIter < 1 || maxIter > 20) {
        showResult("Maximum iterations must be between 1 and 20.", true);
        return;
      }

      result.className = "visible";
      result.textContent = "Running workflow…";

      try {
        const resp = await fetch("/audit", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            raw_input: rawInput,
            max_iterations: maxIter,
            plateau_window: 2,
            plateau_epsilon: 0.5,
            plateau_epsilon_craft: 0.5,
            assess_parallel: true
          })
        });
        const data = await resp.json();
        if (!resp.ok) {
          showResult("Error: " + (data.detail || resp.statusText), true);
          return;
        }
        showResultSuccess(data);
      } catch (err) {
        showResult("Request failed: " + (err.message || "Unknown error"), true);
      }
    });

    function showResult(text, isError) {
      result.className = "visible" + (isError ? " error" : "");
      result.textContent = text;
    }

    function showResultSuccess(data) {
      result.className = "visible";
      result.innerHTML = "";
      const h2 = document.createElement("h2");
      h2.textContent = "Results";
      result.appendChild(h2);

      const metaRow = document.createElement("div");
      metaRow.className = "result-row";
      metaRow.textContent =
        "Stop: " + data.stop_reason +
        " · iterations: " + data.iterations +
        " · aggregate value score: " + data.aggregate_value_score;
      result.appendChild(metaRow);

      if (data.run_id) {
        const runRow = document.createElement("div");
        runRow.className = "result-row meta";
        runRow.textContent =
          "run_id: " + data.run_id +
          (data.persistence_enabled ? " (saved to Supabase)" : " (local id only — persistence off)");
        result.appendChild(runRow);
      }

      if (data.value_scores && data.value_scores.length > 0) {
        const scHead = document.createElement("p");
        scHead.className = "result-row";
        scHead.textContent = "Per-value totals (last round, max 25 each):";
        result.appendChild(scHead);
        const ol = document.createElement("ol");
        data.value_scores.forEach(function (s) {
          const li = document.createElement("li");
          li.textContent = s.value_id + " — " + s.name + ": " + s.total + "/25";
          ol.appendChild(li);
        });
        result.appendChild(ol);
      }

      const draftHead = document.createElement("h3");
      draftHead.style.fontSize = "1rem";
      draftHead.style.marginTop = "1rem";
      draftHead.textContent = "Final draft";
      result.appendChild(draftHead);
      const pre = document.createElement("pre");
      pre.className = "draft";
      pre.textContent = data.draft || "";
      result.appendChild(pre);

      if (data.merged_feedback_preview) {
        const fbHead = document.createElement("p");
        fbHead.className = "result-row";
        fbHead.textContent = "Merged feedback (preview):";
        result.appendChild(fbHead);
        const summaryP = document.createElement("p");
        summaryP.className = "result-summary";
        summaryP.textContent = data.merged_feedback_preview;
        result.appendChild(summaryP);
      }
    }
  </script>
</body>
</html>
"""


@app.get("/", response_class=HTMLResponse)
def form_page() -> str:
    """Serve the workflow form (HTML)."""
    return AUDIT_FORM_HTML


@app.post("/audit", response_model=AuditResponse)
async def audit(request: AuditRequest) -> AuditResponse:
    """Run the Smart Writer workflow. Requires OPENAI_API_KEY."""
    key = os.getenv("OPENAI_API_KEY")
    if not key or not key.strip():
        raise HTTPException(status_code=503, detail="OPENAI_API_KEY not configured")

    from app.orchestrator.run import get_repo, run_workflow

    initial_input: dict = {
        "raw_input": request.raw_input,
        "iterations": 0,
        "max_iterations": request.max_iterations,
        "plateau_window": request.plateau_window,
        "plateau_epsilon": request.plateau_epsilon,
        "plateau_epsilon_craft": request.plateau_epsilon_craft,
        "plateau_epsilon_grounding": request.plateau_epsilon_grounding,
        "assess_parallel": request.assess_parallel,
        "max_concurrent_llm": request.max_concurrent_llm,
        "grounding_enabled": request.grounding_enabled,
        "reference_material": request.reference_material,
        "retrieval_mode": request.retrieval_mode,
        "library_enabled": request.library_enabled,
        "library_max_matches": request.library_max_matches,
        "library_match_threshold": request.library_match_threshold,
    }
    if request.prompt_program_id is not None and request.prompt_program_id.strip():
        initial_input["prompt_program_id"] = request.prompt_program_id.strip()
    if request.prompt_profile_id is not None and request.prompt_profile_id.strip():
        initial_input["prompt_profile_id"] = request.prompt_profile_id.strip()
    if request.prompt_parameters is not None:
        initial_input["prompt_parameters"] = request.prompt_parameters.model_dump(exclude_none=True)
    if request.research_planning_enabled is not None:
        initial_input["research_planning_enabled"] = request.research_planning_enabled
    initial_input["force_research_planning"] = request.force_research_planning

    timeout_sec = get_audit_timeout_sec()
    try:
        if timeout_sec is not None:
            final_state = await asyncio.wait_for(
                run_workflow(initial_input),
                timeout=timeout_sec,
            )
        else:
            final_state = await run_workflow(initial_input)
    except asyncio.TimeoutError:
        raise HTTPException(
            status_code=504,
            detail=(
                f"Workflow exceeded server timeout ({timeout_sec}s). "
                "Increase SMART_WRITER_AUDIT_TIMEOUT_SEC, reduce max_iterations, or call from a job runner."
            ),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    from app.agents.models import AssessorResult, ComposedValues
    from app.orchestrator.run import _infer_stop_reason

    repo = get_repo()
    persistence_enabled = not isinstance(repo, NullRepo)

    stop_reason = _infer_stop_reason(final_state)
    raw_assess = final_state.get("last_assessments") or []
    assessments: list[AssessorResult] = [
        AssessorResult.model_validate(x) if isinstance(x, dict) else x for x in raw_assess
    ]
    composed_raw = final_state.get("composed_values")
    composed: ComposedValues | None
    if composed_raw is None:
        composed = None
    elif isinstance(composed_raw, dict):
        composed = ComposedValues.model_validate(composed_raw)
    else:
        composed = composed_raw
    name_by_id = {v.value_id: v.name for v in composed.values} if composed else {}
    value_scores = [
        ValueScoreLine(value_id=a.value_id, name=name_by_id.get(a.value_id, a.value_id), total=a.total)
        for a in assessments
    ]
    merged = final_state.get("merged_feedback") or ""

    cids = final_state.get("canonical_ids_used")
    if not isinstance(cids, list):
        cids = []
    canon_ids_used = [str(x) for x in cids]

    return AuditResponse(
        stop_reason=stop_reason,
        iterations=final_state.get("iterations", 0),
        aggregate_value_score=float(final_state.get("aggregate_value_score", 0.0)),
        draft=final_state.get("draft") or "",
        run_id=final_state.get("run_id"),
        persistence_enabled=persistence_enabled,
        value_scores=value_scores,
        merged_feedback_preview=merged[:1200] + ("…" if len(merged) > 1200 else ""),
        canonical_ids_used=canon_ids_used,
        library_version_aggregate=final_state.get("library_version_aggregate"),
    )


def main() -> None:
    import uvicorn

    port = int(os.environ.get("PORT", "8080"))
    uvicorn.run(app, host="0.0.0.0", port=port)  # nosec B104 — intentional for container deployment


if __name__ == "__main__":
    main()
