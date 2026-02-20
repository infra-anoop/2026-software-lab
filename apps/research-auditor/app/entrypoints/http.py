# app/entrypoints/http.py — FastAPI server for health checks, form UI, and audit API (PORT, 0.0.0.0).
#
# Endpoints:
#   GET  /         — Audit form (HTML)
#   GET  /health   — Health check
#   POST /audit    — Run the research audit workflow (body: {"raw_input": "..."})
#
import re
import os

from typing import List

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field, field_validator

from app.config import init_env

init_env()

app = FastAPI(title="Research Auditor", version="0.3.4")

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
    max_iterations: int = Field(default=8, ge=1, le=20, description="Max researcher-critic iterations.")

    @field_validator("raw_input", mode="before")
    @classmethod
    def validate_raw_input(cls, v: str) -> str:
        s = sanitize_raw_input(v)
        if not s:
            raise ValueError("raw_input cannot be empty after sanitization")
        return s


class AuditResponse(BaseModel):
    """Response from POST /audit."""

    verdict: str
    iterations: int
    title: str
    summary: str
    findings: List[str] = Field(default_factory=list, description="Key findings (executive summary).")


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
  <title>Research Auditor</title>
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
      <label for="max_iterations">Number of researcher-critic rounds (1–20). More iterations may improve quality.</label>
      <input type="number" id="max_iterations" name="max_iterations" value="8" min="1" max="20">
    </fieldset>

    <button type="submit">Run audit</button>
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
        showResult("Please enter text to audit.", true);
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
      result.textContent = "Running audit…";

      try {
        const resp = await fetch("/audit", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ raw_input: rawInput, max_iterations: maxIter })
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
        findings=research.executive_summary,
    )


def main() -> None:
    import uvicorn

    port = int(os.environ.get("PORT", "8080"))
    uvicorn.run(app, host="0.0.0.0", port=port)  # nosec B104 — intentional for container deployment


if __name__ == "__main__":
    main()
