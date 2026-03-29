# Design: Versioned prompt program for Smart Writer

**Status:** Draft for review  
**App:** `apps/smart-writer`  
**Related:** `Improvement-suggestions.md` (semantic priority #4), `docs/TODO-smart-writer.md`, `app/agents/llm_settings.py`, `app/agents/{value_decoder,rubric_builder,writer,assessor}.py`

---

## 1. Purpose

Introduce a **versioned prompt program**: **centralized, parameterized system prompts** (and optional **few-shot** pairs) for each pipeline role—**decoder**, **rubric builder**, **writer**, **assessor** (and **grounding** when enabled)—so that **first-iteration quality** and **voice constraints** improve **without** users hand-authoring mega-prompts.

Today, role instructions live as **string literals** on `Agent(..., system_prompt=...)` plus ad hoc **user message** templates (e.g. writer JSON context, decoder constraint block). That works for a POC but blocks:

- **Reproducible iteration** on instructions (what changed between deploys?).  
- **Defaults for unstated intent** (audience, register, length, risk tolerance) injected consistently across roles.  
- **Genre- or product-mode profiles** (grant narrative vs. explainer vs. executive memo) with **few-shots** tuned offline.  
- **A/B and rollback** tied to a **named version**, not opaque code edits.

**Relationship to other semantic priorities:** This design is **orthogonal** to retrieval grounding (priority #1), weighted values (priority #2), and the canonical value library (priority #3). It **composes** with all of them: parameterized prompts can reference **evidence-bundle** rules (writer) or **library constraints** (decoder) as **template slots**, not duplicate logic.

---

## 2. Goals and non-goals

### 2.1 Goals

- **G1 — Single source of truth per role:** Each role’s **base system prompt** is loaded from a **named artifact** (package data or `prompts/` tree), not scattered duplicates.  
- **G2 — Explicit versioning:** Every deployable combination has **`prompt_program_id`** + **`prompt_program_version`** (semver or calver) recorded in run state and observability for **replay and regression analysis**.  
- **G3 — Parameter injection:** A small, typed **`PromptParameters`** (or per-role subsets) supplies **defaults** when the user omits them—e.g. `audience`, `register`, `length_target`, `risk_tolerance`, `formality`, optional **`genre` / `product_mode`**. Values are merged from **config defaults** → **request/API overrides** → **inference** (optional later).  
- **G4 — Genre / mode profiles:** **`PromptProfile`** (e.g. `grant_nonprofit`, `policy_explainer`, `executive_brief`) selects **few-shot examples** (user/assistant pairs or “principle snippets”) and **profile-specific prompt addenda** without forking the entire program.  
- **G5 — Offline iteration loop:** Prompts change in **git**; quality is validated with **fixture-based evals** (golden inputs, schema checks, optional LLM-as-judge or human rubric)—same spirit as `Improvement-suggestions.md` item 1.  
- **G6 — Writer + upstream roles:** **Writer** benefits most visibly; **decoder** and **rubric** prompts gain stable **constraint wording**; **assessor** uses a **shared template** with **slots** for rubric JSON (avoid “one bespoke mega prompt per value” in code—slots stay **data-driven**).

### 2.2 Non-goals (initial release)

- **NG1 — Full visual prompt IDE** or non-git authoring workflow.  
- **NG2 — Dynamic prompt learning from production logs** (automatic prompt optimization) — out of scope; manual + eval-driven updates only.  
- **NG3 — Replacing** Pydantic schemas or rubric structure — prompts **wrap** existing models.  
- **NG4 — Per-tenant arbitrary system prompts** from end users in v1 (security + support burden); **operator-configured** profiles and parameters only unless product explicitly opens this later.

---

## 3. Comparison to ad-hoc string prompts

| Aspect | Current (inline strings) | Versioned prompt program |
|--------|--------------------------|---------------------------|
| Change tracking | Diff in Python files mixed with logic | Dedicated prompt files + version metadata |
| Defaults for unstated goals | Implicit in model behavior | Explicit **`PromptParameters`** merged into templates |
| Genre tuning | Copy-paste or hope the user prompt is enough | **`PromptProfile`** + few-shots per genre |
| Regression testing | Weak unless separate fixtures | **Eval sets** keyed by `prompt_program_version` |
| Rollback | Revert code commit | Pin **env** or **request** to prior `prompt_program_version` |

---

## 4. Data model

### 4.1 `PromptParameters` (user- and system-visible defaults)

Typed model (Pydantic), **subset** may be exposed on HTTP/CLI later:

| Field | Example | Notes |
|-------|---------|--------|
| `audience` | `"foundation program officers"` | Injected into writer/decoder/rubric context |
| `register` | `"professional"` \| `"conversational"` \| `"formal"` | Tunes tone instructions |
| `length_target` | `"short"` \| `"medium"` \| `"long"` or word band | Writer + assessor “brevity vs depth” |
| `risk_tolerance` | `"conservative"` \| `"balanced"` \| `"bold"` | Hedging vs strong claims (pairs with grounding when on) |
| `formality` | float or enum | Optional finer control |
| `genre` / `product_mode` | string key | Selects **`PromptProfile`** |

**Precedence:** `defaults` (from **`PromptProgram`**) &lt; **environment** (optional `SMART_WRITER_PROMPT_PARAM_*`) &lt; **`AuditRequest`** fields (future) &lt; **explicit user text** in `raw_input` (always wins for *substantive* task description; parameters **fill gaps**, do not overwrite user-stated constraints if policy says otherwise—see **§7.3**).

### 4.2 `PromptProfile`

- `profile_id: str` — e.g. `grant_nonprofit`, `memo_executive`, `article_explainer`.  
- `label: str` — human-readable.  
- `system_prompt_suffix: str | None` — appended to role base for **each** role or keyed by role (implementation choice in **§14.1**).  
- `few_shots: list[FewShotPair]` — optional; each pair: `user: str`, `assistant: str` (or structured JSON strings matching our message shapes).  
- `compatible_genres: list[str]` — optional validation.

Few-shots are **not** pasted into end-user output; they **steer** the model’s behavior in the **system** or **developer** channel per provider capabilities (see **§8**).

### 4.3 `PromptProgram` (versioned bundle)

- `program_id: str` — e.g. `smart_writer_default`.  
- `version: str` — **semver** `MAJOR.MINOR.PATCH` or **calver** `YYYY.MM.seq`.  
- `roles: dict[Role, RolePromptBundle]` where **`Role`** matches `llm_settings.Role`: `decoder` \| `rubric` \| `writer` \| `assessor` \| `grounding`.  
- `default_parameters: PromptParameters`.  
- `profiles: dict[str, PromptProfile]` — keyed by `profile_id`.

### 4.4 `RolePromptBundle`

- `system_template: str` — **Jinja2** or **str.format**-style template with placeholders `{audience}`, `{register}`, … (see **§6.2**).  
- `user_message_template: str | None` — optional override for **writer** / **decoder** if the team wants templates out of Python (else keep Python builders but feed **rendered fragments**).  
- `few_shot_placement: Literal["system_prefix", "system_suffix", "user_prefix"]` — per role; default **`system_suffix`** for short style primers.

### 4.5 Runtime snapshot in `AgentState` / persistence

Extend orchestrator state (and optionally Supabase `runs.metadata` or `final_output`):

- `prompt_program_id: str`  
- `prompt_program_version: str`  
- `prompt_profile_id: str | None`  
- `prompt_parameters: PromptParameters` (resolved snapshot)

This mirrors how **`model`** ids are already chosen per role—prompt version is equally important for **audit and evals**.

---

## 5. File layout and versioning mechanics

### 5.1 Repository layout (recommended)

**Implementation (`app/prompts/loader.py`):** The loader reads **`manifest.toml`** (TOML) for **`program_id`** and **`version`**, and each role template from **`{role}.txt`** in the program folder. Optional profile suffixes load from **`profiles/<profile_id>.txt`** (plain text), appended after the base role template in **`render_system_prompt`**.

```
apps/smart-writer/
  app/
    prompts/
      __init__.py          # load_program(), get_program_metadata(), render_system_prompt()
      programs/
        smart_writer_default/
          manifest.toml    # program_id, version (TOML)
          decoder.txt
          rubric.txt
          writer.txt
          assessor.txt
          grounding.txt
          refresh_rubric_anchors.txt
          profiles/        # optional; profile_id -> profiles/<profile_id>.txt
            grant_nonprofit.txt
            memo_executive.txt
```

**Roles** supported by **`get_role_template` / `render_system_prompt`:** `decoder`, `rubric`, `writer`, `assessor`, `grounding`, `refresh_rubric_anchors`. Future roles (e.g. **`planner`** for `design-research-planning-phase.md`) add **`planner.txt`** beside these files.

**Alternative:** A single embedded manifest (e.g. **TOML/YAML**) with multiline strings—acceptable for small programs; **`manifest.toml` + per-role `.txt` files** matches the shipped loader and scales better for diffs and review.

### 5.2 Version bump rules

| Change type | Version bump |
|-------------|----------------|
| Wording fix, no semantic intent change | **PATCH** |
| New optional parameters, backward-compatible templates | **MINOR** |
| Breaking placeholder names, role split, or profile removal | **MAJOR** |

**Git** remains the **source of truth**; runtime loads **packaged** assets (or path override for dev — see **§10**).

---

## 6. Template rendering and role integration

### 6.1 Loading

- At process start (or first request), **`load_prompt_program(program_id, version | "latest")`** resolves files under `app/prompts/programs/...`.  
- **`SMART_WRITER_PROMPT_PROGRAM`** = `smart_writer_default` (default).  
- **`SMART_WRITER_PROMPT_PROGRAM_VERSION`** = optional pin (e.g. `1.2.0`); if unset, use **latest embedded** manifest version.

### 6.2 Rendering API

- `render_system_prompt(role: Role, *, params: PromptParameters, profile: PromptProfile | None) -> str`  
- Merge **base template** + **profile suffix** + **few-shots** (formatted as a dedicated block with clear **“Examples (do not copy verbatim)”** headers to reduce plagiarism of few-shot text into user drafts).

### 6.3 Integration with existing agents

| Component | Current | With prompt program |
|-----------|---------|---------------------|
| `value_decoder_agent` | Static `system_prompt` | Built from **`render_system_prompt("decoder", ...)`**; user message still ends with **`_decode_constraint_block`** (decoder-specific **pipeline** constraints stay code-owned unless moved to template **§14.2**). |
| `rubric_per_value_agent` | Static string | Rendered base + optional profile; user payload still JSON from `_build_one_rubric`. |
| `writer_agent` | Static string | Rendered **writer** template includes parameter-driven **voice** + grounding rules **slot**; evidence-bundle injection stays in **`_writer_user_message`** JSON. |
| `assessor_agent` | Static string | Template emphasizes **one value**, **dimension order**, **keep/change**; rubric still passed as JSON in user message. |
| Grounding (if present) | Static | Same pattern. |

**Important:** Keep **Pydantic `result_type`** and **JSON shapes** unchanged unless a **MAJOR** prompt program bump explicitly coordinates schema changes.

### 6.4 User message builders

Two acceptable patterns:

1. **Template-light (recommended for v1):** Keep **`_writer_user_message`**, **`_assessor_message`**, etc. in Python; only **system_prompt** is fully templated. Lower risk, faster ship.  
2. **Full templating:** Move large JSON wrappers to **Jinja** files — better for non-dev editors; higher test surface.

**Recommendation:** **Pattern 1** for **P0–P1**; revisit **Pattern 2** if prompt bodies exceed ~200 lines in code.

---

## 7. Parameters vs. `raw_input` (conflict policy)

### 7.1 Why both exist

- **`raw_input`** carries **task substance** (topic, org names, deliverable type).  
- **`PromptParameters`** carry **how to write** when the user is silent (audience, length, risk).

### 7.2 Defaults

If HTTP/CLI does not send parameters, use **`default_parameters`** from the active **`PromptProgram`** (and optional env overrides for ops tuning).

### 7.3 Conflicts

- **Substance** (topic, facts, named entities): always from **`raw_input`** / evidence bundle.  
- **Style / length / audience**: if the user explicitly states them in **`raw_input`**, those **override** the same fields in **`PromptParameters`** for that run (simple rule: **detect override** optional in v2; **v1** can **always merge** with a sentence in the writer template: *“If the user prompt conflicts with default parameters, follow the user prompt.”*)

---

## 8. Few-shots and context placement

### 8.1 Purpose

Per-genre **examples** improve **first-draft** calibration (structure, tone) without bloating **`raw_input`**.

### 8.2 Risks

- **Leakage:** Few-shot bodies must be **synthetic or licensed**; mark as **internal examples** in template.  
- **Context length:** Cap total few-shot chars per role via **`PromptProgram`** limits.

### 8.3 Placement options

| Option | Pros | Cons |
|--------|------|------|
| **System suffix** | Stable; matches common practice | Long system prompts |
| **User prefix** | Clear separation | May confuse “example” vs “task” if not labeled |
| **Structured `messages` multi-turn** if API supports it | Most faithful to “few-shot” | `pydantic_ai` Agent may need **instruction** wrapper |

**Recommendation:** **System suffix** with a **clear delimiter** and **short** 1–2 examples per profile for v1.

---

## 9. Graph and orchestrator changes

**Minimal.** The LangGraph topology (**decode → rubrics → retrieve? → writer → assess → merge**) is unchanged.

Additions:

1. **Early in `run_workflow`:** Resolve **`PromptParameters`** (defaults + request + env).  
2. **Agent construction:** Either  
   - **A)** Eager: rebuild `Agent` with new `system_prompt` per run (simple; may cost construction), or  
   - **B)** Lazy: single `Agent` factory **`get_agent(role, resolved_prompts)`** per run (preferred if construction is heavy).  
3. **State:** Persist **`prompt_program_*`** and resolved parameters on the run.

No new nodes strictly required for the prompt program **alone**.

---

## 10. Configuration, HTTP, CLI

### 10.1 Environment (operator)

| Variable | Purpose |
|----------|---------|
| `SMART_WRITER_PROMPT_PROGRAM` | Program id (default `smart_writer_default`). |
| `SMART_WRITER_PROMPT_PROGRAM_VERSION` | Pin version; unset = bundled latest. |
| `SMART_WRITER_PROMPT_PROFILE` | Default **`PromptProfile`** id when request omits it. |
| `SMART_WRITER_PROMPTS_DIR` | Optional **dev override**: load prompts from filesystem path. |

### 10.2 HTTP (`AuditRequest`) — future fields

Optional extension (when product-ready):

- `prompt_profile_id: str | None`  
- `prompt_parameters: PromptParameters | None` (or flattened optional fields)

**v1:** Env-only profile + defaults; **v2:** expose on API for integrators.

### 10.3 CLI

Flags: `--prompt-profile`, and optional **`--parameter audience=...`** style or JSON file path **`--prompt-params path.json`**.

---

## 11. Observability and persistence

- **Logfire:** Span attributes `prompt_program_id`, `prompt_program_version`, `prompt_profile_id`; hash of **resolved** parameter dict (not secrets).  
- **Supabase `runs` / `turns`:** Store **`prompt_program_version`** on run row; optional **full** resolved parameters in JSON (size-bounded).  
- **Support:** When debugging “why did it sound like X?”, **version + profile** answer **which instruction set** was active.

---

## 12. Testing strategy

### 12.1 Unit

- **Template rendering:** Given **`PromptParameters`** and **`PromptProfile`**, output contains expected substrings; missing placeholder → test failure.  
- **Loader:** Manifest version matches **`PromptProgram.version`**.

### 12.2 Eval / integration (mocked LLM)

- **Golden runs:** Fixed **`raw_input`** + parameters → assert **decoded value count**, **writer output schema**, optional **snapshot** of first-iteration draft length or **embedding distance** to fixture (lightweight).  
- **Regression matrix:** When **`prompt_program_version`** bumps, run **eval suite**; fail CI if metrics drop beyond threshold (team-defined).

### 12.3 A/B (later)

- Route a fraction of traffic to **`candidate_version`** via env or feature flag; compare **aggregate_value_score**, **iteration count**, and **human** spot checks.

---

## 13. Phased delivery

| Phase | Scope |
|-------|--------|
| **P0** | Introduce **`PromptProgram`** manifest + **loader**; **externalize** current inline strings to **`programs/smart_writer_default`** with **same** text (no behavior change); add **`prompt_program_version`** to state + Logfire only. |
| **P1** | Add **`PromptParameters`** model + defaults + **`render_system_prompt`**; wire **writer** + **assessor** first (highest UX impact). |
| **P2** | **`PromptProfile`** + few-shots for **2–3** genres; CLI `--prompt-profile`; document **version bump** process. |
| **P3** | HTTP fields for parameters/profile; **A/B** hooks; optional **full user-message** templates. |

---

## 14. Decisions (resolved vs open)

### 14.1 Resolved — one program, multiple profiles

**Yes:** A single **`PromptProgram` version** bundles all roles; **profiles** layer genre/mode. Avoid independent version pins per role in v1 (explodes combinatorics).

### 14.2 Resolved — pipeline constraints (decoder) remain code-first initially

The **d_min/d_max** and **library reservation** block (`_decode_constraint_block`) stays **computed in Python** for correctness; only the **instructional framing** moves to templates. Optionally fold into template in **P3** with rigorous tests.

### 14.3 Resolved — assessor uses one system template + JSON user payload

**No** per-value **bespoke** system prompts in v1; **rubric + value** stay in the **user** message as today.

### 14.4 Resolved — template engine (**str.format** + composition)

**Shipped:** Role templates are plain text with **`{placeholder}`** fields; rendering uses Python **`str.format_map`** with a safe defaulting mapping (unknown keys → empty string). Optional **profile** text is loaded from **`profiles/<id>.txt`** and appended after the base template—**no Jinja2** in the current codebase.

**When to add Jinja2:** If profile or role prompts need **`{% if %}`**, **`{% include %}`**, or large in-file branching that would otherwise duplicate paragraphs across files. Until then, keep logic in Python and prose in **`.txt`** files.

### 14.5 Resolved — parameter inference from `raw_input` (**deferred**, not a hole)

**Decision:** Do **not** add an automatic LLM (or heuristic) pass to infer **`PromptParameters`** from **`raw_input`** in the **current** product path.

**Rationale:** Defaults + **`prompt_parameters`** on HTTP/CLI + env overrides already fill “silent” style gaps; inference adds **cost, latency, failure modes**, and **silent wrong guesses** unless you also ship **visibility** (what was inferred) and **evals** (accuracy on real prompts).

**If we revisit later, decide explicitly:**

| Question | What to nail down |
|----------|-------------------|
| **Trigger** | e.g. only when the client omits `prompt_parameters` entirely, or only when all fields still equal program defaults. |
| **Mechanism** | Dedicated small structured-output call vs fusion with an existing node; schema = full or subset of **`PromptParameters`**. |
| **Conflicts** | **`raw_input` wins** for substance and explicit style; inferred fields are **hints**, never overriding clear user wording (extends §7). |
| **Observability** | Persist and/or return **`prompt_parameters_inferred`** vs **`prompt_parameters_effective`** so runs are auditable. |
| **Gate** | Enable only after **offline evals** or A/B show measurable lift; optional **feature flag** for public traffic. |

Until those are answered and justified, **§14.5 remains “intentionally not implemented”**—not an open technical debt item.

---

## 15. Summary

A **versioned prompt program** turns role instructions into **first-class, reviewable artifacts** with explicit **`prompt_program_version`**, **`PromptParameters`** for **silent defaults** (audience, register, length, risk tolerance), and optional **`PromptProfile`** + **few-shots** per genre. Implementation **externalizes** existing `Agent` system strings, adds **rendering** and **state/observability**, and **composes** with grounding, weights, and the canonical value library without replacing their logic. Delivery is **phased**: **loader + parity (P0)** → **parameters + writer/assessor (P1)** → **profiles + CLI (P2)** → **HTTP/A-B (P3)**.

---

## 16. Decision log and review notes

*Canonical “decisions + summary” for implementers.*

### 16.1 Folded decisions

| Topic | Decision | Doc anchor |
|-------|----------|------------|
| **Versioning** | **`program_id` + semver/calver `version`** per bundle; persisted on run. | §4.3, §5.2 |
| **Parameters vs raw_input** | Substance from user; parameters fill **style/default** gaps; explicit **conflict** rule in template for v1. | §7 |
| **Profiles** | **Genre/mode** few-shots + suffixes; not separate unrelated program forks in v1. | §4.2, §14.1 |
| **Assessor** | **One** system template; rubric in **user** JSON. | §6.3, §14.3 |
| **Graph** | **No** new LangGraph nodes for prompts alone. | §9 |
| **User message bodies** | **System templating first**; keep Python JSON builders until P3. | §6.4 |
| **Template engine** | **`str.format`** + optional **`profiles/<id>.txt`** suffix; **Jinja2** only if branching/includes justify it (§14.4). | §14.4 |
| **Inference from `raw_input`** | **Not implemented**; revisit only with trigger/mechanism/conflict/observability/eval gates (§14.5). | §14.5 |

### 16.2 Clarifying notes

- **Eval discipline:** Every **MAJOR/MINOR** prompt bump should run or update **golden evals** (`Improvement-suggestions.md` semantic #1 engineering counterpart).  
- **Security:** Do not allow **untrusted users** to supply arbitrary system prompts in v1 (**NG4**).  
- **Grounding:** Writer templates must **remain compatible** with **`EvidenceBundle`** injection in **`_writer_user_message`**; parameters do not replace evidence rules.

### 16.3 Dependencies on other designs

- **`design-retrieval-grounding.md`:** Writer prompt slots must keep **evidence** and **hedging** language aligned.  
- **`design-weighted-values-craft-hygiene.md`** (if present): **`PromptParameters`** should not duplicate **weight** semantics—**weights** live on **values**, not only in prose.  
- **`design-canonical-value-rubric-library.md`:** Decoder templates should reference **library reservation** wording consistently with **`_decode_constraint_block`**.

---

*End of document.*
