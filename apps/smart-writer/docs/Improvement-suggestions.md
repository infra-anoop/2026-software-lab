# Smart Writer — improvement suggestions (prioritized)

Review snapshot: first-draft pipeline is working (decode → rubrics → writer ↔ assess → merge), with Supabase/`runs` persistence, HTTP form, TPM throttling, and env loading fixes. Below are **five** improvements in **descending order of importance** for making the system durable, observable, and production-appropriate.

---

## 1. Automated evals and broader test coverage — **addressed** (ongoing)

**Status:** Unit tests cover routing, merge, config defaults, and mocked `run_workflow` integration; see `apps/smart-writer/tests/`. Expand as you add features.

**Why it matters:** Most behavior lives in LLM calls and LangGraph routing. Without fixture-based tests, regressions (plateau logic, merge ordering, `NullRepo` vs Supabase, request shaping) only show up in expensive manual runs.

**Directions:**

- Add **unit tests** for pure logic: `_infer_stop_reason`, plateau edge cases (short history, `plateau_window` boundaries), `merge_assessor_feedback` ordering (already partially covered).
- Add **integration tests** with **mocked** `Agent.run` / HTTP responses so CI does not call OpenAI, but still validates schema and graph wiring.
- Optional **golden** JSON snapshots for small frozen `DecodedValues` / `BuiltRubrics` shapes when you later add deterministic fixtures.

**Touches:** `app/orchestrator/run.py`, `tests/`, possibly `pytest` plugins or `respx` / mocks for `pydantic_ai`.

---

## 2. Model and generation settings as configuration (not hardcoded) — **addressed**

**Status:** Per-role model ids and optional `temperature` / `max_tokens` come from env via `app/agents/llm_settings.py`; defaults and var names are documented in `app/config.py` (next to `DEFAULT_MAX_CONCURRENT_LLM`) and `.env.example`.

**Why it mattered:** A single hardcoded model id blocked cost control (cheaper assessor model), A/B tests, and region-specific deployments without code edits — now configurable via env (see above).

**Directions:**

- Centralize `MODEL_WRITER`, `MODEL_ASSESSOR`, `MODEL_RUBRIC`, etc., via **environment variables** or a small `app/agents/settings.py` read at import time.
- Optionally separate **temperature** and **max_tokens** per role.
- Document defaults next to `DEFAULT_MAX_CONCURRENT_LLM` in `app/config.py`.

**Touches:** `app/agents/value_decoder.py`, `rubric_builder.py`, `writer.py`, `assessor.py`, `app/config.py`, `.env.example`.

---

## 3. CLI and HTTP API ergonomics (input, output, long runs) — **addressed** (core)

**Status:** CLI uses `argparse` (`--prompt`, `--prompt-file`, `--max-iterations`, `--output` Markdown, `--print-draft` / `--no-print-draft`). `AuditResponse` includes `run_id`, `persistence_enabled`, and `stop_reason` (unchanged). Server-side `SMART_WRITER_AUDIT_TIMEOUT_SEC` wraps `run_workflow` with `asyncio.wait_for` (504 on expiry). **Not done:** async job + poll / SSE (still blocking `POST /audit`).

**Why it matters:** `app/main.py` embeds a fixed `raw_input` and `MAX_ITERATIONS`; the CLI does not print the **final draft** to stdout. `POST /audit` blocks until the full workflow finishes—no `run_id` in the JSON response for easy correlation with Supabase, and no progress for multi-minute runs.

**Directions:**

- **CLI:** `argparse` (or `--prompt-file`) for `raw_input`, flags for `max_iterations`, optional print of **full draft** (or path to write Markdown output).
- **HTTP:** Include **`run_id`** (and optionally `stop_reason` details) in `AuditResponse` when persistence is enabled; consider **202 + background job** + poll endpoint for long runs, or **SSE** streaming of phase updates (larger effort).
- Add **request timeout** configuration on the server side and document client timeouts.

**Touches:** `app/main.py`, `app/entrypoints/http.py`, response models.

---

## 4. Resilience: retries and backoff on transient OpenAI errors — **addressed**

**Status:** `app/llm/retry.py` wraps each `Agent.run` via `with_transient_llm_retry` (decode, rubric, writer, assess). Retries on 429 / 500 / 502 / 503, connection and timeout errors; exponential backoff with jitter; honors `Retry-After` when present. Logfire span `llm.retry_backoff` includes `run_id` from a context var set in `run_workflow`. Knobs: `SMART_WRITER_LLM_RETRY_MAX_ATTEMPTS`, `_BASE_SEC`, `_MAX_SEC`.

**Why it matters:** Users already hit **429 TPM** limits; pydantic-ai retries validation but not all API-level backoff is uniform. Network blips and 429s mid-graph should retry with jitter without failing the whole run when a short wait would succeed.

**Directions:**

- Configure **OpenAI client retry policy** where supported, or wrap `agent.run` in a small helper with exponential backoff for `429` / `503` (respect `Retry-After` when present).
- Log retry attempts to Logfire with `run_id` for debugging.

**Touches:** `app/agents/*`, optional shared `app/llm/retry.py`, Logfire spans.

---

## 5. HTTP hardening for any public or shared deployment

**Why it matters:** The form and `/audit` are unauthenticated. A public URL allows **unbounded cost** (your OpenAI key) and **DoS** (long prompts, many requests). Fine for local dev; not for production without guardrails.

**Directions:**

- **Authentication** (API key header, OAuth, or reverse-proxy auth) for `/audit`.
- **Rate limiting** per IP or API key (e.g. middleware or edge gateway).
- **CORS** policy if the UI is served from a different origin than the API.
- Optional: cap `max_iterations` and `raw_input` length stricter on public tiers (partially done via `RAW_INPUT_MAX_LEN`).

**Touches:** `app/entrypoints/http.py`, deployment docs, Railway/nginx if applicable.

---

## Benchmark: Smart Writer vs. chat UIs and adjacent tools (qualitative)

This is not a numeric benchmark (no public leaderboard for “values-grounded revision loops”). It is a **product/architecture comparison** to clarify where Smart Writer is already differentiated and where “better than chat” is still **aspirational**.

| Dimension | Typical chat LLM UI | Smart Writer (current) | Notes |
|-----------|---------------------|---------------------------|--------|
| **Success criteria** | Implicit; user must restate goals each turn | **Decoded values + per-value rubrics**; critique is structured | Strong differentiator: criteria are explicit and comparable across iterations. |
| **Critique** | One general reviewer; easy to get vague praise | **Parallel assessors per value** + merged feedback | Reduces “average out” failure modes; surfaces tradeoffs. |
| **Revision discipline** | User manually asks for another pass | **Bounded loop** (max iterations + plateau) | More systematic than ad-hoc “try again.” |
| **Auditability** | Thread history only | **Run/turn traces** (optional Supabase), schema-first outputs | Better for debugging and evals than raw chat logs. |
| **Grounding / facts** | Optional; user must paste context or use plugins ad hoc | **Not built in yet** | Chat + browsing plugins can *feel* more “researchy” unless Smart Writer adds retrieval + citations. |
| **Latency / cost** | One-shot cheap; multi-step chat expensive but user-controlled | **Many LLM calls** (decode + rubrics + writer + N assessors × rounds) | Structural cost; optimizable (reuse rubrics, cheaper models, fewer values). |

**Rough peer buckets (not 1:1 competitors):** “AI writing assistants” (style/grammar), “document copilots” (inline edits), “answer engines” (retrieval-heavy). Smart Writer is closest to a **criteria-driven editor**; it wins on **decomposed quality** and **repeatable revision**. It does not yet automatically beat chat on **factual depth** unless you add **grounding** and **source discipline** (see semantic priorities below).

---

## Semantic output quality — five priorities (recommended order)

These are ordered by **impact on the substance of the text** (not only engineering hygiene). They intentionally overlap with notes in `docs/TODO-smart-writer.md`; see that file for mapping.

1. **Retrieval grounding, citations, and fact discipline (anti-hallucination)**  
   **Why first:** Chat users can paste sources manually; a dedicated product must *systematically* tie claims to evidence—search/RAG over trusted corpora, quoted excerpts, optional “fact-check” or “unsupported claim” pass, and explicit “unknown” behavior. This is the largest semantic gap vs. “fluent generic English.”  
   **Touches:** new retrieval layer, writer/assessor prompts, optional tools, evals with gold sources.

2. **Weighted values + fixed “craft / hygiene” dimensions (designer + user)**  
   **Why second:** Equal weight across all values is rarely what humans want; grammar, clarity, length, and structure should not compete equally with domain goals unless the task demands it. Split **designer-defined baseline criteria** (always on) from **task-derived values**, and apply **weights** in merge logic and stopping rules so revision chases what matters most.  
   **Touches:** `DecodedValues` / merge / `aggregate_score`, assessor weighting, prompt templates.

3. **Canonical value & rubric library with similarity matching (finite, reusable)**  
   **Why third:** Re-discovering similar “values” every run wastes time and money and lets rubrics drift. A **bounded library** (e.g. 15–20 canonical values with stored rubrics), plus **embedding similarity** to map new prompts onto existing entries, improves **consistency of judgment** and cuts duplicate LLM work—directly improving semantic stability over many runs.  
   **Touches:** persistence beyond `runs`/`turns`, vector store or pgvector, decoder + rubric builder branching.

4. **Versioned “prompt program”: parameterized system prompts + few-shots per genre**  
   **Why fourth:** First-iteration quality dominates perceived usefulness. Centralize **role prompts** (decoder, rubric, writer, assessor) as versioned artifacts with **parameters** (audience, register, length, risk tolerance) defaulted even when the user omits them. Iterate prompts offline using eval sets—this is how the service gets **uniquely good voice and constraints** without users hand-authoring mega-prompts.  
   **Touches:** `llm_settings` / prompt modules, config, eval fixtures.

5. **Explicit research / planning phase before long-form drafting**  
   **Why fifth:** A single pass from blank page to polished text encourages generic prose. A **plan → gather → outline → draft** subgraph (even lightweight: bullet “facts to include,” questions, then draft) nudges the system toward **substance-first** writing and pairs naturally with item 1.  
   **Touches:** LangGraph nodes, optional tool calls, writer input shape.

---

*Original checklist footer: adjust order if your near-term goal is shipping a public demo (then move structural item 5 — HTTP hardening — up) or cutting cost (then model/config and rubric reuse). The **semantic** list above is the primary guide for “better content than chat.”*
