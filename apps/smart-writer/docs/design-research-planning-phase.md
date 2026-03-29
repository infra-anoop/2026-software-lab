# Design: Explicit research / planning phase before long-form drafting

**Status:** Draft for review  
**App:** `apps/smart-writer`  
**Related:** `Improvement-suggestions.md` (semantic priority #5), `docs/TODO-smart-writer.md`, `docs/ARCHITECTURE.md`, `docs/design-retrieval-grounding.md` (semantic priority #1), `app/orchestrator/run.py`, `app/agents/writer.py`, `app/retrieval/bundle_builder.py`

---

## 1. Purpose

Today the pipeline moves from **built rubrics** directly to the **first writer call** (`run_writer`). The model is asked to “produce the best possible first draft” with values, rubrics, and (when grounding is on) an **evidence bundle**—but **without** an intermediate artifact that forces **substance-first** thinking: what facts matter, what is unknown, how the piece should be structured, and what must be covered before prose.

Semantic priority **#5** addresses that gap: introduce a **lightweight research / planning subgraph**—**plan → (optional deepen retrieval) → outline → draft**—so long-form outputs are nudged toward **organized, content-driven** writing instead of fluent generic text. It **pairs naturally** with retrieval grounding: planning can **steer queries and coverage**; the evidence bundle still **anchors** the draft (see **§3**).

This document specifies **data shapes**, **graph placement**, **agent contracts**, and **configuration** so an engineer can implement without re-deriving product intent from chat logs.

---

## 2. Goals and non-goals

### 2.1 Goals

- **G1 — Structured pre-draft artifact:** Persist a **first-class** `ResearchPlan` (Pydantic) in workflow state: thesis / intent, **sections or beats**, **facts to verify or include**, **open questions**, optional **risks** (e.g. stale stats, contested claims).  
- **G2 — Outline before prose:** A concise **document outline** (headings + bullets) is produced **before** iteration 1 of the writer and passed into **every** writer call for that run (revisions may update outline only if explicitly designed—default: **outline fixed after planning** to keep assessor comparability stable).  
- **G3 — Graph integration:** New LangGraph node(s) after **`build_rubrics`** and **before** the first **`writer`** invocation, compatible with existing **`retrieve_evidence`** routing (see **§5**).  
- **G4 — Writer input shape:** Extend the writer’s JSON context (`_writer_user_message` in `app/agents/writer.py`) with `research_plan` and `outline` so the model **cannot** ignore the plan without leaving structured fields empty.  
- **G5 — Observability:** Logfire spans and `RunRepo.append_turn` records for **`research_plan`** (and optional **`outline_only`** if split), with schema-stable JSON for evals.  
- **G6 — Configurable cost:** **Profile-aware defaults** (research-heavy profiles **on**, minimal profiles **off**) plus optional **heuristics** (e.g. skip planning for very short tasks) and request overrides so an extra LLM call is not imposed when inappropriate.

### 2.2 Non-goals (initial release)

- **NG1 — Autonomous web browsing** inside the planning agent (no tool loop per token). Controlled retrieval stays in **`retrieve_evidence`** / `build_bundle_from_prompt` per `design-retrieval-grounding.md`.  
- **NG2 — User-visible mandatory “research report”** as the **primary** product deliverable in v1; the plan/outline are **steering artifacts**—persisted for observability (§8) but **no default UI** that promises a separate “research report” unless product adds it (§11 P2).  
- **NG3 — Replacing** the value decoder or rubrics; planning **assumes** values and rubrics already exist.  
- **NG4 — Multi-hour research sessions** or human-in-the-loop approval gates in v1.  
- **NG5 — Separate plateau / stop rules** for “plan quality”; stopping remains **writer ↔ assess**-only unless future metrics justify it.

---

## 3. Relationship to retrieval grounding and the current pipeline

| Concern | Role of this design | Role of `design-retrieval-grounding.md` |
|--------|---------------------|----------------------------------------|
| **Facts** | Planning lists **what to look for** and **questions**; may suggest **search sub-queries**. | **Retrieval** fetches/snippets, builds **`EvidenceBundle`**, grounding assessor checks alignment. |
| **Order** | Recommended: **rubrics → research_plan → retrieve_evidence → writer** when grounding is on, so **retrieval can use** plan-derived queries (see **§5.2**). | Unchanged: fetch budgets, modes (`auto`, `urls_only`, …). |
| **Writer** | Sees **plan + outline + bundle** (if any). | Writer already accepts **`evidence_bundle`** when `grounding_enabled`. |

### 3.1 Grounding assessor vs research plan (`facts_to_include`)

**Decision (v1):** The **grounding assessor** (`run_grounding_assess`, `design-retrieval-grounding.md` §4.3) continues to receive only **`raw_input`** (clipped), **`evidence_bundle`**, and **`draft`**—the same JSON shape as today (`grounding_assessor.py` user message). **Do not** inject **`ResearchPlan`**, **`facts_to_include`**, or **`document_outline`** into the grounding assessor payload.

**Rationale:**

- **Avoid double-counting:** The **writer** is already instructed (§7.2) to prefer **chunks** over plan-sourced “facts.” If the grounding model also saw **`facts_to_include`**, it might flag “unsupported” for the same tension the writer was told to surface—duplicate issues in **`merge`** and noisy **`writer_instructions`**.  
- **Single locus for “plan vs evidence” tension:** Conflict between planner guesses and retrieval stays a **writer** responsibility; **grounding** remains **draft vs bundle** editorial QA.  
- **Future (optional MINOR):** A separate field **`user_intended_facts: list[str]`** (subset of `facts_to_include`) could be added to the grounding payload if product needs “draft ignored user-stated facts” detection without full plan context—out of scope for v1.

**Value assessors** are unchanged: they score **draft vs rubrics** only; they do not receive the research plan.

**Important:** If **`grounding_enabled`** is false, **`retrieve_evidence`** may still be skipped (current `route_after_rubrics` behavior). Planning **still runs** when the feature flag is on: the user gets outline-driven drafting without automatic web fetch—useful for purely creative or confidential tasks.

**Overlap with `ARCHITECTURE.md`:** The architecture diagram labels an early phase “Planning” for the **value decoder**. This design adds a **second** planning layer—**task content planning**—after **values and rubrics** exist. Naming in code/UI should distinguish **value planning** (decoder) from **research / document planning** (this feature), e.g. `research_plan` vs `decoded_raw`.

---

## 4. Data model

### 4.1 `ResearchPlan` (Pydantic, planner agent output)

Suggested fields (names can be adjusted in implementation if kept consistent across prompts and tests):

| Field | Type | Notes |
|-------|------|--------|
| `intent_summary` | `str` | One short paragraph: what the document must accomplish. |
| `audience_and_constraints` | `str` | Echo or refine `PromptParameters` + explicit user constraints. |
| `key_points` | `list[KeyPoint]` | Non-negotiable ideas or messages; each item is **tagged with `value_id`** so merge/assessor ordering and planning stay aligned (see **§4.1.1**). |
| `facts_to_include` | `list[str]` | Concrete facts, figures, names, dates the draft should cover—**steering only**; factual particulars defer to **`evidence_bundle`** when grounding is on (see **§7.2**). |
| `open_questions` | `list[str]` | Gaps the draft should address or flag as unknown. |
| `risks_or_caveats` | `list[str]` | Optional; e.g. sensitivity, missing data, controversial claims. |
| `suggested_research_queries` | `list[str]` | Short search-style strings; **inputs** to retrieval augmentation (§5.2). |
| `coverage_checklist` | `list[str]` | Optional; section-agnostic checklist for “did we cover X?” |

Validation hints:

- Cap list lengths (e.g. max 12 items per list) via Pydantic `Field(max_length=…)` or a post-validator to bound tokens.  
- `suggested_research_queries` max 5–8 strings in v1.

### 4.1.1 `KeyPoint`

| Field | Type | Notes |
|-------|------|--------|
| `value_id` | `str` | Must match a `composed_values` entry (including craft / library / task-derived). |
| `text` | `str` | The substantive point for that value. |

### 4.2 `DocumentOutline` (Pydantic)

Either **merged into** `ResearchPlan` or a **separate** model returned by the same agent call (prefer **single agent call** for cost: one `result_type` wrapping both).

| Field | Type | Notes |
|-------|------|--------|
| `title` | `str \| None` | Working title. |
| `sections` | `list[OutlineSection]` | Ordered. |

**`OutlineSection`:**

| Field | Type | Notes |
|-------|------|--------|
| `heading` | `str` | Section heading (markdown-friendly). |
| `bullets` | `list[str]` | What to cover in this section. |
| `estimated_emphasis` | `Literal["low", "medium", "high"]` \| `None` | Optional; nudges length/detail. |

### 4.3 Combined result type

- **`ResearchPlanningOutput`** (name TBD): `research_plan: ResearchPlan`, `outline: DocumentOutline`.

Single Pydantic model as **`result_type`** for the planner agent keeps **one** retry/validation path and matches the project’s schema-first approach.

### 4.4 `AgentState` extensions (`app/orchestrator/run.py`)

Add optional keys (TypedDict, `total=False`):

- `research_planning_requested: bool | None` — what the client sent: **`True`** / **`False`** if the HTTP/CLI field was present; **`None`** if the field was **omitted** (let profile + env decide). Aliases: request body **`research_planning_enabled`** maps to this key on ingest (§9.2).  
- `research_planning_effective: bool` — **single source of truth for routing** after resolution (§9.2). The graph **must not** branch on raw request fields except through this flag.  
- `research_plan: ResearchPlan | None`  
- `document_outline: DocumentOutline | None`  
- `research_planning_skipped_reason: str | None` — e.g. `"disabled"`, `"short_prompt_heuristic"`, `"planner_validation_failed"` (see **§6.5**). When **`research_planning_effective`** is false because the client turned planning off, use **`"disabled"`** (or a dedicated **`"client_disabled"`** string—pick one and use consistently in tests).

**Resolution (normative):** Immediately after building the initial `AgentState` in **`run_workflow`**, set **`research_planning_effective`** using **`resolve_research_planning_enabled(...)`** (§9.2). Do not recompute mid-graph unless inputs change (they do not in v1).

**Persistence:** **`final_output`** should include **both** **`research_planning_requested`** (JSON **`null`** if omitted) and **`research_planning_effective`** so replays and support can see “what the user asked” vs “what the router used” (§8).

**Revision iterations:** Default policy is to **reuse** the same `research_plan` and `document_outline` for all writer iterations. If the product later allows “re-outline mid-run,” that is a separate design (would interact with plateau and assessor expectations).

---

## 5. Graph topology

### 5.1 Current relevant fragment

```
match_canonical_library → decode_values → compose_values → build_rubrics
  → [route_after_rubrics] → retrieve_evidence (if grounding_enabled) | else writer
  → writer → assess_all → merge_feedback → …
```

### 5.2 Target fragment (conceptual)

```
build_rubrics
  → [route_after_rubrics_planning] → research_planning (if enabled) | skip → …
```

After **`research_planning`** (or skip):

- If **`grounding_enabled`**: **`retrieve_evidence`** (possibly with plan-augmented query—§5.3).  
- Else: **`writer`**.

**Normative routing (single decision function from `build_rubrics`):** Implement **one** function **`route_after_build_rubrics(state) -> Literal["research_planning", "retrieve_evidence", "writer"]`** in `app/orchestrator/run.py` (or `app/orchestrator/routing.py` if split). It is the **only** place that encodes “after rubrics, what runs next?” **Do not** split the same predicate logic across multiple routers—avoids drift and keeps unit tests in **one** module.

**Decision order (evaluate top to bottom):**

1. If **`research_planning_effective`** and **not** skipped by short-prompt heuristic (§6.4) → **`research_planning`**.  
2. Else if **`grounding_enabled`** → **`retrieve_evidence`**.  
3. Else → **`writer`**.

**Illustrative shape:**

```python
def route_after_build_rubrics(state: AgentState) -> Literal["research_planning", "retrieve_evidence", "writer"]:
    if _should_run_research_planning(state):
        return "research_planning"
    if state.get("grounding_enabled", False):
        return "retrieve_evidence"
    return "writer"
```

**LangGraph:** **`add_conditional_edges("build_rubrics", route_after_build_rubrics, {...})`** with all three targets listed.

**After `research_planning` (second, trivial router):** Planning is done; only **grounding vs not** remains. Use a **separate** **`route_after_research_planning(state) -> Literal["retrieve_evidence", "writer"]`** — **not** duplicate logic with step 1–3 above; it is only **`grounding_enabled ? retrieve_evidence : writer`**. This second function does **not** re-encode “planning on/off”; it assumes the planner node already ran.

| From | Router | Outcomes |
|------|--------|----------|
| `build_rubrics` | **`route_after_build_rubrics`** | `research_planning` \| `retrieve_evidence` \| `writer` |
| `research_planning` | **`route_after_research_planning`** | `retrieve_evidence` \| `writer` |

**Unit tests:** Full matrix for **`route_after_build_rubrics`** (combinations of `research_planning_effective`, heuristic skip, `grounding_enabled`). **`route_after_research_planning`** needs **two** cases only.

### 5.3 Retrieval augmentation (optional v1.1)

Today `build_bundle_from_prompt` takes `raw_input`, `reference_material`, `mode`. **v1** can implement augmentation **without** API churn by:

- Concatenating `suggested_research_queries` into a **synthetic line** appended to the internal prompt text used for search query derivation, **or**  
- Extending `build_bundle_from_prompt(..., supplemental_queries: list[str] | None = None)` to merge queries deterministically (cleaner; preferred if touch budget allows).

Document the chosen approach in `bundle_builder.py` docstring and in this design’s revision history.

---

## 6. Agent design

### 6.1 Role and model

- Add a **`planner`** (or **`research`**) entry to `app/agents/llm_settings.py` **`Role`** type and env mapping (e.g. `SMART_WRITER_MODEL_PLANNER`), defaulting to the same tier as **`decoder`** or **`rubric`** for cost control.  
- **System prompt** loaded via **`app/prompts/loader.py`** (aligns with `design-versioned-prompt-program.md`): new template `planner.txt` under `app/prompts/programs/<program_id>/`.  
- **User message** should include: `raw_input`, **`composed_values`** summary (names + short descriptions), optional **`PromptParameters`** rendering, and **no full rubric JSON**—use a **rubric digest** instead (see **§6.1.1**).  
- **Library hint:** Pass **`library_canonical_value_ids`** (or equivalent) when the run has library-matched rows so the planner can **emphasize** those values in `key_points` (see **§6.1.3**).

#### 6.1.1 Deterministic rubric digest (implementation contract)

**No second LLM** for digest in v1: a **pure Python** builder keeps prompts reproducible and cheap.

- **Module:** `app/agents/rubric_digest.py` (or `app/planning/rubric_digest.py` if you split a `planning` package later).  
- **Signature (illustrative):**

```python
def build_rubric_digest_for_planner(
    composed: ComposedValues,
    rubrics: BuiltRubrics,
    *,
    max_chars_per_value: int = 400,
    max_total_digest_chars: int = 4000,
) -> str:
    ...
```

**Algorithm (normative):**

1. **Order:** Iterate **`composed.values`** in **list order** (stable, matches compose pipeline).  
2. **Join rubric:** For each value, locate **`ValueRubric`** by `value_id`. For each **`RubricDimension`**, take **`name`** plus a **truncated `description`** (first sentence or first **160 chars**, whichever is shorter)—do **not** emit full **`score_1`…`score_5`** ladders in v1; those are for assessors, not the planner digest.  
3. **Per-value block:** One block per value: line 1 = `value_id` + composed **`ValueDefinition.name`**; lines 2+ = **2–4 bullets** distilled from the five dimensions (merge adjacent dimensions if needed to stay under **`max_chars_per_value`**).  
4. **Global cap:** If total digest length &gt; **`max_total_digest_chars`**, **truncate the longest per-value blocks first** (repeat until within cap). **Never** drop **`value_id` / `name` header lines**—if a value must shrink, reduce bullets only.  
5. **Output:** A single **string** (markdown-ish plain text) embedded in the planner user message under a fixed key, e.g. `"rubric_digest"`.

**No stochastic steps:** Same inputs ⇒ same digest string (tests can snapshot).

#### 6.1.2 Planner input token budget

The digest from **§6.1.1** targets roughly **~300–800 tokens** for the digest block (via `max_*` defaults, tunable by env). The full planner **user** message (task + digest + `PromptParameters` + library hints) should stay in **~2.5k–6k tokens** total; adjust **`max_chars_per_value`** / **`max_total_digest_chars`** if the model context requires.

#### 6.1.3 Canonical / library values in planning

When **`library_canonical`** rows exist, pass their **`value_id`s** into the planner context explicitly. System/user instructions should state that those values are **priority success criteria**: `key_points` **must** include at least one **`KeyPoint` per library-matched value** where substantive content applies, while still covering **task-derived** and **craft** values so the outline does not collapse to catalog-only content.

### 6.2 Planner behavior

- **Input:** User task + composed values + **`build_rubric_digest_for_planner(...)`** output + optional library value ids (§6.1).  
- **Output:** `ResearchPlanningOutput` as in §4.3.  
- **Instructions (conceptual):** Prefer **specific** bullets; forbid empty **open_questions** when the task is research-heavy (prompt can require at least one question when `length_target` is `long` or when `genre` implies report-style).  
- **Retries:** Use existing `with_transient_llm_retry` pattern like other agents.

### 6.3 Node implementation

- **`research_planning_node`**: async; reads state; builds digest via **`build_rubric_digest_for_planner`**; calls `run_research_planning(...)`; persists `research_plan` + `document_outline`; appends history tuple `("research_planning", …)`; `append_turn` with input/output JSON.

### 6.4 Skip logic

- If `research_planning_effective` is false: router skips node; `research_planning_skipped_reason = "disabled"`.  
- Optional heuristic: if `len(raw_input) < N` (e.g. 200 chars) **and** no `reference_material`, skip with reason `"short_prompt_heuristic"`. **N** and heuristic toggles via env (e.g. `SMART_WRITER_PLANNING_MIN_CHARS`).

### 6.5 Planner failure and validation policy

| Failure class | After `with_transient_llm_retry` exhaustion | Policy |
|---------------|-----------------------------------------------|--------|
| **Transport / HTTP / rate limits** (same class as other agents) | Still failing | **Fail the run** — `research_planning_node` **raises**; graph stops; `finalize_run` **failed** (consistent with **`decode_values`** / **`build_rubrics`** on LLM failure). |
| **Pydantic / schema validation** on `ResearchPlanningOutput` (malformed model output) | N/A | **Do not fail the whole run.** Apply **§6.5.1** sanitization; if still invalid, **skip planning**: set `research_plan = None`, `document_outline = None`, `research_planning_skipped_reason = "planner_validation_failed"`, log **warning** with snippet; **continue** to `retrieve_evidence` or `writer`. |

#### 6.5.1 Sanitization before accept

- Strip **`KeyPoint`** entries whose **`value_id`** is not in **`composed_values`**; if stripping empties **`key_points`**, leave empty list or drop to minimal placeholder per prompt contract.  
- Clamp list lengths to schema caps (§4.1).  
- Optional **one** stricter repair: not required for v1 if sanitization + skip is enough; document if you add a single repair `agent.run` with “fix JSON only” instruction.

**Persistence:** On **skip after validation**, `append_turn` for `research_planning` should record **`success: false`** and error summary so operators can see planner drift without losing the user’s run.

---

## 7. Writer integration

### 7.1 Context JSON (`_writer_user_message`)

Add keys:

```json
"research_plan": {
  "key_points": [ { "value_id": "...", "text": "..." } ],
  ...
},
"document_outline": { ... }
```

When planning was skipped, set **`null`** or omit keys **consistently**; writer system prompt should say: “If `research_plan` is present, follow it; if absent, infer structure from the user prompt.”

### 7.2 System prompt changes

- In **`writer.txt`**, add:

  **Planning adherence:** Draft must **cover** `outline.sections` in order unless `raw_input` contradicts; **`key_points`** (per `value_id`) and **open_questions** inform substance and coverage.

  **Evidence precedence (when `grounding_enabled` / `evidence_bundle` present):** For **factual claims**, **`evidence_bundle` is authoritative**. The writer must **not** assert planner **`facts_to_include`** (or other plan text) as fact when it **contradicts** retrieved chunks or **lacks support** in the bundle—prefer bundle content, omit or hedge unsupported numbers, and **briefly surface tension** if the plan asserted something specific that sources contradict or do not support (tone per product mode). **`facts_to_include`** remains **coverage intent**, not a second knowledge base.

  **Precedence order (explicit — writer only):** When **composing or revising prose**, prioritize in this order: (1) **`raw_input`** — task and explicit user constraints; (2) **`evidence_bundle`** — factual particulars when present; (3) **`research_plan` / `document_outline`** — structure, checklist, open questions; (4) **rubrics** — the same **value dimensions** that **value assessors** will use to score the draft in **`assess_all`** (aim to satisfy them in the text; see **§7.4**).

  **When grounding is off:** No bundle to arbitrate; **`facts_to_include`** is softer guidance only—the writer must still avoid fabrication (unchanged baseline).

### 7.3 First vs revision iterations

- **Iteration 1:** Strongly weight outline + key_points.  
- **Iteration >1:** Merged assessor feedback remains primary; outline is **context** to avoid drift, not a hard replan unless product changes.

### 7.4 Writer precedence vs value assessors (no contradiction)

**Two different roles:**

| Role | What it uses | Purpose |
|------|----------------|--------|
| **Writer** | Precedence **§7.2** + full writer JSON (values, rubrics, plan, bundle, merged feedback) | **Produce** draft text; ordering tells the model **how to resolve conflicts** when *drafting* (e.g. facts come from bundle, not from plan guesses). |
| **Value assessors** (`assess_all`) | **Draft + one `ValueRubric` + one `ValueDefinition`** per call | **Score** the draft on that value’s grid; they **do not** receive `research_plan` / outline for v1. Success of the loop is still **rubric-grounded**. |

**Why “rubrics fourth” does not demote quality:** The stack is **not** “everything above rubrics overrides rubrics.” It orders **conflict resolution** for *content sourcing and structure* (user → evidence → plan). **Rubrics** remain the **definition of success** for each value; the writer should **still** draft toward those dimensions. Placement fourth means: do not invent facts to satisfy a rubric cell; do not let outline **excuse** unsupported claims—but do **write** so that, **honestly**, rubric dimensions can score well.

**Apparent outline–rubric tension** (e.g. outline asks for long detail, **brevity** value asks for short): the writer **balances**; **assessors** report tradeoffs via scores and **keep/change** feedback; **`merge_feedback`** and later iterations reconcile—**not** “outline wins, rubric ignored.”

**Grounding assessor:** orthogonal; sees draft + bundle only (**§3.1**).

---

## 8. Persistence and observability

- **`append_turn`:** `agent="research_planning"` with `input_data` including `raw_input` hash or length, `n_values`, `prompt_profile_id`; `output_data` the dumped `ResearchPlanningOutput`.  
- **Logfire:** Span `llm.research_planning` with `run_id`, `program_id`, `outline_section_count`.  
- **`finalize_run` / API / Supabase:** **Recommended:** include `research_plan`, `document_outline`, **`research_planning_requested`** (nullable), **`research_planning_effective`**, and (when relevant) `research_planning_skipped_reason` in **`final_output`** (mirror `decoded_raw` and other artifacts) for **operators, replay, debugging, and evals**.  
- **Clarification — “internal” vs persistence:** Including these fields in **`final_output`** does **not** mean the product **defaults** to showing them in the **end-user UI** in v1. **Internal-first** here means: the **draft** remains the primary user outcome; plan/outline are **not** marketed as a separate customer-facing deliverable until §11 P2. Persistence on the run record is **intentional** for traceability, not a contradiction of “no default UI.”

---

## 9. HTTP / CLI / request shape

- **`AuditRequest` / CLI:** Optional boolean **`research_planning_requested`** (same field name as today can remain **`research_planning_enabled`** in JSON for brevity—document alias). When **omitted**, **§9.1** manifest defaults apply; when **set**, it overrides profile defaults.  
- Optional: `force_research_planning: bool` to override skip heuristic.  
- Implementation: `resolve_research_planning_enabled(request, prompt_profile_id, program_id) -> bool` merging **explicit request** &gt; **profile default from manifest** &gt; **global env** (e.g. `SMART_WRITER_RESEARCH_PLANNING_DEFAULT`).  
- Document in `app/entrypoints/http.py` OpenAPI descriptions and `.env.example`.

### 9.1 Profile → planning default matrix (source of truth)

**Single source of truth:** extend the prompt program **`manifest.toml`** (same file as `program_id` / `version`, see `design-versioned-prompt-program.md`) with a **`[research_planning.profile_defaults]`** table mapping **`prompt_profile_id`** → **`true` | `false`** (planning **on** / **off** when the HTTP/CLI request **omits** an explicit **`research_planning_requested`** / `research_planning_enabled` field).

**Example (`app/prompts/programs/smart_writer_default/manifest.toml`):**

```toml
[research_planning.profile_defaults]
# Long-form / research-heavy — planning on
grant = true
policy_explainer = true
memo_executive = true
# Minimal / transactional — planning off
short_email = false
```

**Rules:**

- **`prompt_profile_id`** **not** listed: use **`SMART_WRITER_RESEARCH_PLANNING_DEFAULT`** env (`true`/`false`; **default `true`** if unset—substance-first for unknown profiles) or **`true`** as code default—pick one and document in `app/config.py`.  
- **Explicit** `research_planning_requested` (or HTTP field **`research_planning_enabled`**) on the request **always wins** over manifest and env.  
- **Tests:** Golden expectations use profile ids from this table (e.g. `grant`, `short_email`); integration tests load manifest or patch the resolver.

**Loader:** Add `get_research_planning_default_for_profile(program_id: str, profile_id: str | None) -> bool` next to `get_program_metadata`, reading the TOML section (cached with manifest).

### 9.2 Requested vs effective (single resolution rule)

**Goal:** No ambiguity between “what the client typed” and “whether the `research_planning` node runs.”

| Inbound (HTTP / CLI) | Maps to `research_planning_requested` | `research_planning_effective` |
|----------------------|----------------------------------------|-------------------------------|
| Field **omitted** | `None` | `get_research_planning_default_for_profile(program_id, prompt_profile_id)` then **`or`** env **`SMART_WRITER_RESEARCH_PLANNING_DEFAULT`** (see §9.1) |
| **`true`** / **`false`** (or JSON **`research_planning_enabled`**) | `True` / `False` | **Same bool** — explicit client choice **always wins** over profile + env |

**Function:**

```text
def resolve_research_planning_enabled(
    *,
    requested: bool | None,
    program_id: str,
    prompt_profile_id: str | None,
) -> bool:
    if requested is not None:
        return requested
    return get_research_planning_default_for_profile(program_id, prompt_profile_id)
    # inside: manifest [research_planning.profile_defaults] then env fallback from §9.1
```

**AgentState:** Store **both** **`research_planning_requested`** and **`research_planning_effective`** after the single call above at workflow start. **`route_after_build_rubrics`** (**§5.2**) combines **`research_planning_effective`** with short-prompt skip rules (**§6.4**)—it does not re-resolve profile defaults.

**API naming:** OpenAPI may keep the field name **`research_planning_enabled`** for backward compatibility; document that it populates **`research_planning_requested`** (not the effective flag). Response / **`final_output`** exposes **both** **`research_planning_requested`** and **`research_planning_effective`** (§4.4, §8).

**Anti-pattern:** Do not put **`research_planning_effective`** in the request body as the primary control unless you are building an admin override—default remains **requested** + profile resolution.

---

## 10. Testing and evals

- **Unit tests:** Pydantic validation on `ResearchPlanningOutput`; **snapshot / golden** tests for **`build_rubric_digest_for_planner`** (determinism); **`route_after_build_rubrics`** and **`route_after_research_planning`** (§5.2) truth tables with mocked state; §6.5 sanitization strips bad `value_id`s.  
- **Integration (mocked LLM):** Patch `run_research_planning` to return fixtures; assert writer receives plan/outline in message payload (string contains or parsed JSON).  
- **Evals (later):** Rubric or LLM-judge on “outline covers user ask,” “open_questions non-empty for research tasks”—aligned with `Improvement-suggestions.md` item 1.

---

## 11. Phased rollout

| Phase | Scope |
|-------|--------|
| **P0** | `ResearchPlanningOutput` model (`KeyPoint` with `value_id`), `build_rubric_digest_for_planner`, `research_planning_node` (§6.5), graph wiring, writer JSON + `writer.txt` (precedence §7.2), manifest **`[research_planning.profile_defaults]`** + `research_planning_effective` (§9). |
| **P1** | `supplemental_queries` passed into `build_bundle_from_prompt`; Logfire + `finalize_run` fields. |
| **P2** | UI surfacing of outline; user editing of plan before draft; eval harness. |

---

## 12. Resolved decisions (formerly open questions)

| # | Topic | Decision |
|---|--------|----------|
| 1 | **Mutable outline mid-run** | **No.** Do not re-run or refresh outline after assessor conflict in v1; outline stays fixed after planning for stable assessor comparability. |
| 2 | **`key_points` and values** | **Yes.** Model `key_points` as **`list[KeyPoint]`** with **`value_id` + `text`** so merge and assessor ordering can align planning with per-value feedback (§4.1.1). |
| 3 | **Profile defaults for planning** | **Yes.** Defaults **on** / **off** per **`prompt_profile_id`** in **`manifest.toml`** **`[research_planning.profile_defaults]`** (§9.1); resolve via `resolve_research_planning_enabled` (§9). |
| 4 | **Evidence vs plan (`facts_to_include`)** | **`evidence_bundle` wins** for factual claims when grounding is on. Writer must not insist on plan “facts” that contradict or lack support in chunks; **prefer bundle**, omit/hedge unsupported claims, **briefly surface conflict** when the plan asserted something sources contradict or omit. **`facts_to_include`** = coverage intent, not a parallel KB. Precedence: `raw_input` → bundle → plan/outline → rubrics (§7.2). |
| 5 | **Planner token budget** | **Yes, rubric digest only**—no full `BuiltRubrics` in the planner message. Target **~2.5k–6k tokens** total user message; **~300–800 tokens** for digest across values (~50–100 tokens/value); truncate longest summaries first if over budget (§6.1.1). |
| 6 | **Library / canonical emphasis** | **Yes.** Pass library-matched **`value_id`s** into planner input; instructions require **`key_points`** to **emphasize** those values (at least one substantive `KeyPoint` per library value when applicable) without starving task-derived or craft values (§6.1.2). |
| 7 | **Internationalization** | **English-only for v1**; no multi-locale planning requirement. |
| 8 | **User-visible artifacts** | **No default end-user UI** for plan/outline in v1 (draft-first); artifacts are still **persisted in `final_output`** / Supabase for operators, debugging, and evals (§8). Optional **product UI** for plan/outline is **later** (§11 P2). |
| 9 | **Planner output size ceiling** | **No** automatic truncation pass or second “compress plan” LLM call in v1; rely on Pydantic list caps and prompt discipline. |
| 10 | **Progress events for planning** | **No** planning-specific progress/SSE events in v1; defer to broader async-job work if needed later. |

---

## 13. Summary

Introduce a **schema-first research / planning step** after rubrics, producing **`ResearchPlan` + `DocumentOutline`** before the first draft, with **`key_points`** keyed by **`value_id`**. **Wire** it into LangGraph **before** `retrieve_evidence` when grounding is on, and **before** `writer` otherwise. **Extend** the writer payload and **`writer.txt`** so drafting is **outline- and substance-driven**, with explicit **evidence precedence** when **`evidence_bundle`** is present. Build planner input with **`build_rubric_digest_for_planner`** (§6.1.1), **`manifest.toml` profile defaults** (§9.1), and **`research_planning_effective`** routing (§9.2; **`research_planning_requested`** vs effective persisted in §8). **Grounding assessor** stays draft+bundle only (§3.1). **Failure policy:** transport errors fail the run; validation errors skip planning with reason (§6.5).

---

## 14. Design review and cross-document alignment

This feature sits **after** value decoding and rubric compilation (`ARCHITECTURE.md`, `design-weighted-values-craft-hygiene.md`) and **before** retrieval and drafting (`design-retrieval-grounding.md`). It does **not** change **`DecodedValues` / `ComposedValues`** schemas except by consuming them; **`KeyPoint.value_id`** must reference **`composed_values`** rows, including **library_canonical** provenance (`design-canonical-value-rubric-library.md`). **Retrieval** remains the sole place URL fetch / search runs; the planner only emits **`suggested_research_queries`** for optional augmentation of **`build_bundle_from_prompt`**, preserving SSRF and budget rules from the grounding design. **Prompts** follow the same **`programs/<id>/{role}.txt`** pattern as `app/prompts/loader.py` (`design-versioned-prompt-program.md`); adding **`planner`** is a **MINOR** prompt-program change (new role file + manifest entry) unless template placeholders break existing contracts. **Evidence precedence** in §7.2 is **compatible** with the grounding design’s “bundle for facts, natural prose for user” rule: the writer defers factual assertions to chunks, while **value assessors** still score against **rubrics** only. **§7.4** states that precedence orders **writer-side** conflict resolution, not assessor criteria. **§3.1** keeps the **grounding assessor** on **draft + bundle + clipped `raw_input`** only so “plan vs evidence” tension is not duplicated in **`GroundingAssessment`**.

---

## 15. Engineer-oriented follow-ups (review snapshot)

The following lists are a **prioritized review snapshot**: they identify gaps, ambiguities, and upgrades that would make implementation and maintenance safer. They are **not** a commitment to implement every item in order.

### A. Items previously missing — status

**Resolved in this document:** (1) **Planner failure policy** — §6.5; (2) **Deterministic rubric digest** — §6.1.1 (`build_rubric_digest_for_planner`); (3) **Profile → default matrix** — §9.1 (`manifest.toml`); (4) **Grounding assessor vs plan** — §3.1 (no plan in grounding payload in v1).

**Still open:**

1. **Backward compatibility and API contract** — When `research_plan` appears in **`final_output`**, specify **schema version** or stable field names for clients that persist runs; note whether **omitting** the block when planning was skipped is **required** for older clients.

### B. Inconsistencies — status

**Resolved — internal-only vs `finalize_run` exposure:** §8 and §12 row 8 now distinguish **(a)** persistence in **`final_output`** for observability/replay from **(b)** **no default end-user UI** for plan/outline in v1. See §8 “Clarification — internal vs persistence.”

**Resolved — raw vs effective planning flag:** §4.4, §8, and §9.2 define **`research_planning_requested`** (optional client input, alias **`research_planning_enabled`** on ingest), **`research_planning_effective`** (router-only), **`resolve_research_planning_enabled`**, and persistence of **both** in **`final_output`**.

**Resolved — writer precedence vs assessor rubrics:** §7.2 (writer-only precedence) and **§7.4** separate **drafting conflict resolution** from **assessor scoring**. Assessors always score **draft vs rubric**; outline/plan guides **structure and coverage**, not a bypass of rubrics.

**Resolved — routing implementation:** §5.2 **normatively** uses **`route_after_build_rubrics`** (single function for all branches from `build_rubrics`) plus a **thin** **`route_after_research_planning`** for the post-planning binary choice only—no duplicated “retrieve vs writer” logic from `build_rubrics`.

**Resolved — prompt program file naming:** `design-versioned-prompt-program.md` §5.1 now matches **`app/prompts/loader.py`**: **`manifest.toml`**, **`{role}.txt`**, optional **`profiles/<profile_id>.txt`**.

**Remaining:** None from the original §15.B inconsistency list.

### C. Five improvements to strengthen the design

1. **Post-planner validation** — Add a **deterministic check**: every `KeyPoint.value_id` ∈ `composed_values.value_id` set; reject or strip invalid IDs before `retrieve_evidence` / `writer`. Reduces silent misalignment with merge ordering.

2. **Cross-link weighted merge** — Reference `design-weighted-values-craft-hygiene.md`: when **`key_points`** are per-`value_id`, document whether **merge** or **writer** should **sort** or **highlight** feedback using **existing weights** so planning and revision stay consistent.

3. **Prompt program version bump policy** — State explicitly: adding **`planner.txt`** is a **MINOR** bump (new role, backward-compatible) per `design-versioned-prompt-program.md` §5.2; record **`prompt_program_version`** on runs including planner turns.

4. **Acceptance / smoke criteria** — Short bullets: “Planning on → `append_turn` includes `research_planning`”; “Planning skipped → writer JSON has no `research_plan`”; “Grounding on → retrieval runs **after** planning when both enabled.”

5. **Privacy / retention note** — `research_plan` may duplicate **PII** from `raw_input`. Note **Supabase retention** and redaction policy for logs (align with existing run/turn policy), without expanding scope to new compliance features.
