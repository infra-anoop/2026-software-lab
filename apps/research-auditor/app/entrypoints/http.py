# app/entrypoints/http.py — FastAPI server for health checks, form UI, and audit API (PORT, 0.0.0.0).
#
# Endpoints:
#   GET  /              — Audit form (HTML; public)
#   GET  /health        — Health check (public, no OpenAI)
#   GET  /ready         — Config present (OPENAI_API_KEY non-empty; no OpenAI call)
#   POST /audit         — Enqueue job (202 + job_id). Does not run the graph on this request.
#   GET  /jobs/{job_id} — Snapshot of job status / result (does not wait)
#
# Auth: header ``X-Audit-Secret`` must match ``RESEARCH_AUDITOR_AUDIT_SECRET`` (503 if unset).
# Jobs are in-memory: lost on process restart; not shared across Railway instances.
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
    get_settings,
    init_env,
)
from lab_shared.jobs import Job, JobRunner, QueueFullError, SlidingWindowRateLimiter

init_env()

AUDIT_SECRET_HEADER = "X-Audit-Secret"  # nosec B105 — HTTP header name, not a password


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


app = FastAPI(title="Research Auditor", version="0.3.4", lifespan=lifespan)

# Input limits for injection/DoS mitigation
RAW_INPUT_MAX_LEN = 10_000
CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def sanitize_raw_input(value: str) -> str:
    """Remove control characters and excessive whitespace; enforce length."""
    s = CONTROL_CHARS.sub("", value).strip()
    if len(s) > RAW_INPUT_MAX_LEN:
        s = s[:RAW_INPUT_MAX_LEN]
    return s


class AuditRequest(BaseModel):
    """Request body for POST /audit."""

    raw_input: str = Field(
        ...,
        min_length=1,
        max_length=RAW_INPUT_MAX_LEN,
        description="Raw text to audit (e.g. document excerpt, topic).",
    )
    max_iterations: int = Field(
        default=8,
        ge=1,
        le=HTTP_MAX_ITERATIONS,
        description="Max researcher-critic iterations. HTTP clamp 8.",
    )

    @field_validator("raw_input", mode="before")
    @classmethod
    def validate_raw_input(cls, v: str) -> str:
        s = sanitize_raw_input(v)
        if not s:
            raise ValueError("raw_input cannot be empty after sanitization")
        return s


class AuditResponse(BaseModel):
    """Terminal audit payload (nested under GET /jobs/{id}.result on success)."""

    verdict: str
    iterations: int
    title: str
    summary: str
    findings: List[str] = Field(default_factory=list, description="Key findings (executive summary).")


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
            detail="RESEARCH_AUDITOR_AUDIT_SECRET is not configured",
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


def _audit_response_from_state(final_state: dict) -> AuditResponse:
    """Map graph state to today's AuditResponse."""
    research = final_state["research"]
    feedback = final_state["feedback"]
    return AuditResponse(
        verdict=feedback.verdict,
        iterations=final_state["iterations"],
        title=research.source_material_title,
        summary=feedback.summary,
        findings=research.executive_summary,
    )


async def _execute_audit_job(payload: dict) -> AuditResponse:
    """Worker body: same ``run_workflow`` as CLI."""
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
  <title>Research Auditor</title>
  <style>
    body { font-family: system-ui, sans-serif; max-width: 640px; margin: 2rem auto; padding: 0 1rem; }
    h1 { font-size: 1.5rem; }
    fieldset { margin-bottom: 1.5rem; border: 1px solid #ccc; padding: 1rem; }
    legend { font-weight: 600; padding: 0 0.25rem; }
    label { display: block; margin-top: 0.5rem; color: #555; font-size: 0.9rem; }
    textarea { width: 100%; min-height: 120px; box-sizing: border-box; }
    input[type="number"] { width: 5rem; }
    input[type="password"] { width: 100%; box-sizing: border-box; padding: 0.35rem; }
    button { padding: 0.5rem 1rem; cursor: pointer; }
    #result { margin-top: 1rem; padding: 1rem; border: 1px solid #ccc; display: none; }
    #result.visible { display: block; }
    #result h2 { font-size: 1.1rem; margin: 0 0 0.75rem 0; }
    #result .result-row { margin-bottom: 0.5rem; }
    #result .result-summary { margin: 0.5rem 0; }
    #result ol { margin: 0.25rem 0 0 1.25rem; padding: 0; }
    .error { color: #c00; }
    .meta { font-size: 0.85rem; color: #666; margin-top: 0.5rem; }
  </style>
</head>
<body>
  <h1>Research Auditor</h1>
  <p>Submit text or a topic to run the research audit workflow.</p>

  <form id="audit-form">
    <fieldset>
      <legend>Text to audit</legend>
      <label for="raw_input">Paste or type the text you want audited (e.g. document excerpt, claim, or topic).</label>
      <textarea id="raw_input" name="raw_input" required maxlength="10000"
        placeholder="e.g. Indian Rupee will continue to fall against US dollar in 2026"></textarea>
      <p class="meta">Max 10,000 characters. Control characters are stripped.</p>
    </fieldset>

    <fieldset>
      <legend>Maximum iterations</legend>
      <label for="max_iterations">Researcher-critic rounds (1–8). Server clamps at 8.</label>
      <input type="number" id="max_iterations" name="max_iterations" value="8" min="1" max="8">
    </fieldset>

    <fieldset>
      <legend>API secret</legend>
      <label for="audit_secret">Preview gate only. The browser sends this as X-Audit-Secret. Anyone with the secret can run paid audits. This is not a login.</label>
      <input type="password" id="audit_secret" name="audit_secret" autocomplete="off" required>
    </fieldset>

    <button type="submit">Run audit</button>
  </form>

  <div id="result" role="region" aria-live="polite"></div>

  <p class="meta"><a href="/docs">API docs</a> · <a href="/health">Health</a></p>

  <script>
    const form = document.getElementById("audit-form");
    const result = document.getElementById("result");
    const SECRET_KEY = "research_auditor_audit_secret";
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
        showResult("Please enter text to audit.", true);
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
          body: JSON.stringify({ raw_input: rawInput, max_iterations: maxIter })
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
      h2.textContent = "Audit Results";
      result.appendChild(h2);

      const verdictRow = document.createElement("div");
      verdictRow.className = "result-row";
      verdictRow.textContent = "Verdict: " + data.verdict + " (" + data.iterations + " iterations)";
      result.appendChild(verdictRow);

      const titleRow = document.createElement("div");
      titleRow.className = "result-row";
      titleRow.textContent = "Title: " + data.title;
      result.appendChild(titleRow);

      const summaryP = document.createElement("p");
      summaryP.className = "result-summary";
      summaryP.textContent = data.summary;
      result.appendChild(summaryP);

      if (data.findings && data.findings.length > 0) {
        const findHead = document.createElement("p");
        findHead.className = "result-row";
        findHead.textContent = "Key findings:";
        result.appendChild(findHead);
        const ol = document.createElement("ol");
        data.findings.forEach(function (f) {
          const li = document.createElement("li");
          li.textContent = f;
          ol.appendChild(li);
        });
        result.appendChild(ol);
      }
    }
  </script>
</body>
</html>
"""


@app.get("/", response_class=HTMLResponse)
def form_page() -> str:
    """Serve the audit form (HTML)."""
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
    payload = {
        "raw_input": body.raw_input,
        "iterations": 0,
        "max_iterations": min(body.max_iterations, HTTP_MAX_ITERATIONS),
    }
    try:
        job = runner.enqueue(payload)
    except QueueFullError:
        raise HTTPException(status_code=429, detail="Job queue is full; try again shortly.")

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
