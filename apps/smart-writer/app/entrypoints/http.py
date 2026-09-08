# app/entrypoints/http.py — FastAPI server for health checks, form UI, and workflow API (PORT, 0.0.0.0).
#
# Endpoints:
#   GET  /              — Workflow form (HTML; public)
#   GET  /health        — Health check (public, no OpenAI)
#   GET  /ready         — Config present (OPENAI_API_KEY non-empty; no OpenAI call)
#   POST /audit         — Enqueue job (202 + job_id). Does not run the graph on this request.
#   GET  /jobs/{job_id} — Snapshot of job status / result (does not wait)
#
# Auth: header ``X-Audit-Secret`` must match ``SMART_WRITER_AUDIT_SECRET`` (503 if unset).
# Jobs are in-memory: lost on process restart; not shared across Railway instances.
# Worker wall-clock: ``SMART_WRITER_AUDIT_TIMEOUT_SEC`` (default 300; 0 = no limit).
# In-flight graphs: ``SMART_WRITER_JOB_CONCURRENCY`` (default 1). Queue: ``SMART_WRITER_JOB_QUEUE_MAX`` (default 4).
#
from __future__ import annotations

import hmac
import os
import re
from contextlib import asynccontextmanager
from typing import List, Literal

from fastapi import Depends, FastAPI, Header, HTTPException, Request, Response
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, Field, field_validator

from app.config import (
    HTTP_MAX_ITERATIONS,
    get_audit_rate_limit_per_min,
    get_audit_secret,
    get_audit_timeout_sec,
    get_job_concurrency,
    get_job_queue_max,
    get_max_concurrent_llm,
    get_settings,
    init_env,
)
from lab_shared.db.null_repo import NullRepo
from lab_shared.jobs import Job, JobRunner, QueueFullError, SlidingWindowRateLimiter

init_env()

AUDIT_SECRET_HEADER = "X-Audit-Secret"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Start the in-process job worker. Health does not touch this."""
    runner = JobRunner(
        execute=_execute_audit_job,
        timeout_sec=get_audit_timeout_sec,
        concurrency=get_job_concurrency(),
        queue_max=get_job_queue_max(),
    )
    app.state.job_runner = runner
    app.state.rate_limiter = SlidingWindowRateLimiter()
    await runner.start()
    yield
    await runner.stop()


app = FastAPI(title="Smart Writer", version="0.1.0", lifespan=lifespan)

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
        default=8,
        ge=1,
        le=HTTP_MAX_ITERATIONS,
        description="Max writer iterations (draft → assess → merge cycles). HTTP clamp 8.",
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
    """Terminal audit payload (nested under GET /jobs/{id}.result on success)."""

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


class EnqueueResponse(BaseModel):
    """202 body for POST /audit."""

    job_id: str
    status: Literal["queued"] = "queued"
    location: str


class JobView(BaseModel):
    """Snapshot from GET /jobs/{job_id}. Does not wait for completion."""

    job_id: str
    status: Literal["queued", "running", "succeeded", "failed", "timed_out"]
    created_at: str
    started_at: str | None = None
    finished_at: str | None = None
    error: str | None = None
    result: AuditResponse | None = None


def require_audit_secret(
    x_audit_secret: str | None = Header(default=None, alias="X-Audit-Secret"),
) -> None:
    """Reject missing/wrong secret with 401; unset env with 503 (fail closed)."""
    expected = get_audit_secret()
    if expected is None:
        raise HTTPException(
            status_code=503,
            detail="SMART_WRITER_AUDIT_SECRET is not configured",
        )
    provided = x_audit_secret or ""
    try:
        matched = hmac.compare_digest(provided, expected)
    except (TypeError, ValueError):
        matched = False
    if not matched:
        raise HTTPException(status_code=401, detail="Invalid or missing X-Audit-Secret")


def _job_to_view(job: Job) -> JobView:
    """Map an in-memory job to the public snapshot."""
    result: AuditResponse | None = None
    if job.result is not None:
        result = (
            job.result
            if isinstance(job.result, AuditResponse)
            else AuditResponse.model_validate(job.result)
        )
    return JobView(
        job_id=job.job_id,
        status=job.status,
        created_at=job.created_at,
        started_at=job.started_at,
        finished_at=job.finished_at,
        error=job.error,
        result=result,
    )


def _payload_from_request(body: AuditRequest) -> dict:
    """Build the orchestrator input dict from the HTTP request (graph unchanged)."""
    initial_input: dict = {
        "raw_input": body.raw_input,
        "iterations": 0,
        "max_iterations": min(body.max_iterations, HTTP_MAX_ITERATIONS),
        "plateau_window": body.plateau_window,
        "plateau_epsilon": body.plateau_epsilon,
        "plateau_epsilon_craft": body.plateau_epsilon_craft,
        "plateau_epsilon_grounding": body.plateau_epsilon_grounding,
        "assess_parallel": body.assess_parallel,
        "max_concurrent_llm": body.max_concurrent_llm,
        "grounding_enabled": body.grounding_enabled,
        "reference_material": body.reference_material,
        "retrieval_mode": body.retrieval_mode,
        "library_enabled": body.library_enabled,
        "library_max_matches": body.library_max_matches,
        "library_match_threshold": body.library_match_threshold,
    }
    if body.prompt_program_id is not None and body.prompt_program_id.strip():
        initial_input["prompt_program_id"] = body.prompt_program_id.strip()
    if body.prompt_profile_id is not None and body.prompt_profile_id.strip():
        initial_input["prompt_profile_id"] = body.prompt_profile_id.strip()
    if body.prompt_parameters is not None:
        initial_input["prompt_parameters"] = body.prompt_parameters.model_dump(exclude_none=True)
    if body.research_planning_enabled is not None:
        initial_input["research_planning_enabled"] = body.research_planning_enabled
    initial_input["force_research_planning"] = body.force_research_planning
    return initial_input


def _audit_response_from_state(final_state: dict) -> AuditResponse:
    """Map graph state to today's AuditResponse (no second public schema)."""
    from app.agents.models import AssessorResult, ComposedValues
    from app.orchestrator.run import _infer_stop_reason, get_repo

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
    return AuditResponse(
        stop_reason=stop_reason,
        iterations=final_state.get("iterations", 0),
        aggregate_value_score=float(final_state.get("aggregate_value_score", 0.0)),
        draft=final_state.get("draft") or "",
        run_id=final_state.get("run_id"),
        persistence_enabled=persistence_enabled,
        value_scores=value_scores,
        merged_feedback_preview=merged[:1200] + ("…" if len(merged) > 1200 else ""),
        canonical_ids_used=[str(x) for x in cids],
        library_version_aggregate=final_state.get("library_version_aggregate"),
    )


async def _execute_audit_job(payload: dict) -> AuditResponse:
    """Worker body: same ``run_workflow`` as CLI. Import inside so tests can patch it."""
    from app.orchestrator.run import run_workflow

    final_state = await run_workflow(payload)
    return _audit_response_from_state(final_state)


@app.get("/health")
def health() -> dict:
    """Health check for load balancers and deployment probes."""
    return {"ok": True}


@app.get("/ready")
def ready() -> JSONResponse:
    """Readiness: required secrets present. Does not call OpenAI or run the graph."""
    key_ok = bool(get_settings().openai_api_key.strip())
    body = {"ok": key_ok, "openai_api_key": "set" if key_ok else "missing"}
    return JSONResponse(status_code=200 if key_ok else 503, content=body)


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
    input[type="password"], input[type="text"] { width: 100%; box-sizing: border-box; padding: 0.35rem; }
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
      <label for="max_iterations">Draft → assess → merge cycles (1–8). Server clamps at 8.</label>
      <input type="number" id="max_iterations" name="max_iterations" value="8" min="1" max="8">
    </fieldset>

    <fieldset>
      <legend>API secret</legend>
      <label for="audit_secret">Preview gate only. The browser sends this as X-Audit-Secret. Anyone with the secret can run paid audits. This is not a login.</label>
      <input type="password" id="audit_secret" name="audit_secret" autocomplete="off" required>
    </fieldset>

    <button type="submit">Run workflow</button>
  </form>

  <div id="result" role="region" aria-live="polite"></div>

  <p class="meta"><a href="/docs">API docs</a> · <a href="/health">Health</a></p>

  <script>
    const form = document.getElementById("audit-form");
    const result = document.getElementById("result");
    const SECRET_KEY = "smart_writer_audit_secret";
    const secretInput = document.getElementById("audit_secret");
    const stored = sessionStorage.getItem(SECRET_KEY);
    if (stored) secretInput.value = stored;

    function detailText(data, fallback) {
      if (!data) return fallback;
      const d = data.detail;
      if (typeof d === "string") return d;
      if (Array.isArray(d)) return d.map(function (x) { return x.msg || JSON.stringify(x); }).join("; ");
      return fallback;
    }

    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      const rawInput = document.getElementById("raw_input").value.trim();
      const maxIter = parseInt(document.getElementById("max_iterations").value, 10);
      const secret = secretInput.value;

      if (!rawInput) {
        showResult("Please enter text to process.", true);
        return;
      }
      if (rawInput.length > 10000) {
        showResult("Text exceeds 10,000 characters. Please shorten it.", true);
        return;
      }
      if (isNaN(maxIter) || maxIter < 1 || maxIter > 8) {
        showResult("Maximum iterations must be between 1 and 8.", true);
        return;
      }
      if (!secret) {
        showResult("API secret is required.", true);
        return;
      }
      sessionStorage.setItem(SECRET_KEY, secret);

      result.className = "visible";
      result.textContent = "Submitting job…";

      try {
        const resp = await fetch("/audit", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-Audit-Secret": secret
          },
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
          showResult("Error: " + detailText(data, resp.statusText), true);
          return;
        }
        await pollJob(data.job_id, secret);
      } catch (err) {
        showResult("Request failed: " + (err.message || "Unknown error"), true);
      }
    });

    async function pollJob(jobId, secret) {
      result.textContent = "Job " + jobId + " queued…";
      while (true) {
        const jr = await fetch("/jobs/" + jobId, {
          headers: { "X-Audit-Secret": secret }
        });
        const job = await jr.json();
        if (!jr.ok) {
          showResult("Error: " + detailText(job, jr.statusText), true);
          return;
        }
        if (job.status === "queued" || job.status === "running") {
          result.textContent = "Job " + job.status + " (" + jobId + ")…";
          await new Promise(function (r) { setTimeout(r, 1000); });
          continue;
        }
        if (job.status === "succeeded") {
          showResultSuccess(job.result);
          return;
        }
        showResult("Job " + job.status + (job.error ? ": " + job.error : ""), true);
        return;
      }
    }

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


@app.post("/audit", response_model=EnqueueResponse, status_code=202)
async def audit(
    body: AuditRequest,
    request: Request,
    response: Response,
    _: None = Depends(require_audit_secret),
) -> EnqueueResponse:
    """Enqueue an audit job. Returns 202 immediately; poll GET /jobs/{job_id}."""
    key = get_settings().openai_api_key
    if not key or not key.strip():
        raise HTTPException(status_code=503, detail="OPENAI_API_KEY not configured")

    limiter: SlidingWindowRateLimiter = request.app.state.rate_limiter
    if not limiter.allow(get_audit_rate_limit_per_min()):
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded; max POST /audit per minute on this instance.",
        )

    runner: JobRunner = request.app.state.job_runner
    try:
        job = runner.enqueue(_payload_from_request(body))
    except QueueFullError:
        raise HTTPException(
            status_code=429,
            detail="Job queue is full; try again shortly.",
        )

    location = f"/jobs/{job.job_id}"
    response.headers["Location"] = location
    return EnqueueResponse(job_id=job.job_id, status="queued", location=location)


@app.get("/jobs/{job_id}", response_model=JobView)
def get_job(
    job_id: str,
    request: Request,
    _: None = Depends(require_audit_secret),
) -> JobView:
    """Snapshot of a job. Never waits for the graph."""
    runner: JobRunner = request.app.state.job_runner
    job = runner.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Unknown job_id")
    return _job_to_view(job)


def main() -> None:
    import uvicorn

    port = int(os.environ.get("PORT", "8080"))
    uvicorn.run(app, host="0.0.0.0", port=port)  # nosec B104 — intentional for container deployment


if __name__ == "__main__":
    main()
