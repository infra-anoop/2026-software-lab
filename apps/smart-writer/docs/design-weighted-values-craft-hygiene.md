# Design: Weighted values + fixed craft / hygiene dimensions

**Status:** Draft for review  
**App:** `apps/smart-writer`  
**Related:** `Improvement-suggestions.md` (semantic priority **#2**), `docs/TODO-smart-writer.md` (ideas 3–4), `docs/ARCHITECTURE.md`, `docs/design-retrieval-grounding.md` (value vs grounding metrics)

---

## 1. Purpose

Today the pipeline treats every **task-derived value** the same: assessors run in parallel, **merge** orders feedback by **lowest raw total** (`0–25` per value), and **plateau / history** use the **unweighted sum** of per-value totals (`aggregate_sum_scores` in `app/agents/feedback_merge.py`). The decoder is instructed to avoid redundancy but still often emits **generic “English class” criteria** (clarity, structure) alongside **domain goals** (persuasion, humor, donor alignment)—all with **equal influence** on stopping and on what the writer sees first.

This design adds two coupled ideas from the semantic roadmap:

1. **Designer-defined craft / hygiene values** — a small, stable set of criteria (e.g. grammar, clarity, coherence, length / structure) that are **always evaluated** with **versioned baseline rubrics**, instead of competing for slots with domain values in the decoder output.  
2. **Explicit weights** — per-value (or per-group) weights that drive **merge priority**, **aggregate signals for plateau**, and optionally **differentiated thresholds** for `targets_met`, so revision effort tracks **what matters for the task** rather than treating every rubric total equally.

**Relationship to retrieval grounding:** Weighting applies to the **value / rubric track only**. It does **not** replace or blend with **grounding** metrics for exit logic. Follow `design-retrieval-grounding.md` **§7**: keep **conjunctive** gates (value criteria satisfied **and** grounding satisfied when grounding is enabled); use **weighted** summaries only **inside** the value side. Do not introduce a single headline score that lets strong rubrics “pay for” weak grounding.

---

## 2. Goals and non-goals

### 2.1 Goals

- **G1 — Provenance classes (derived):** Every assessed value has **`provenance`** ∈ **`designer_craft`** | **`task_derived`** | **`library_canonical`** (see **§4.1** Option B—stored keys: `craft_key`, `canonical_id`, or neither). Useful for logging / UI.  
- **G2 — Bounded craft set:** A **small** number of craft values (suggested **3–5**), each with a **stable `value_id`** (e.g. `CRAFT_GRAMMAR`, `CRAFT_STRUCTURE`) and a **default rubric** maintained in code or versioned assets—not re-LLM’d every run unless you opt into refresh.  
- **G3 — Decoder focuses on domain:** The value-decoder emits **only** `task_derived` values, **without** duplicating craft dimensions the system already enforces. **Count:** when the **canonical library** is off, **`DEFAULT_MIN_VALUES` / `DEFAULT_MAX_VALUES`** bound the **decoder list length** (= total domain). When the library is on, those constants bound **total domain** (**library + task-derived**); the decoder’s **`d`** is derived per **`design-canonical-value-rubric-library.md` §5.3.1**.  
- **G4 — Weighted merge:** `merge_assessor_feedback` (and `merge_value_and_grounding_feedback`) order and section emphasis reflect **weights**—e.g. sort by **weighted gap** or **weighted deficit**, not raw `total` alone.  
- **G5 — Weighted aggregate for motion:** `aggregate_history` and plateau detection on the value side use a **documented weighted aggregate** (e.g. weighted sum of totals, or weighted mean on `0–25`), so “stuck” reflects **priority**, not raw sum.  
- **G6 — Explicit weights:** **Craft** weights are **designer-fixed**; **domain** weights are **decoder-emitted** (with optional **config / env / request** overrides for tuning). Grounding stays a **separate** conjunct; it is not weighted against values.  
- **G7 — Optional tiered `targets_met`:** Allow **stricter floors for craft** (must not ship broken prose) and **slightly looser or task-tuned targets for domain** values, still as **separate conjuncts** alongside grounding when applicable.

### 2.2 Non-goals (initial release)

- **NG1 — LLM-inferred weights as the only source** — v1 should not depend solely on the model guessing importance without deterministic defaults and bounds.  
- **NG2 — Merging craft into one mega-assessor** in the first slice (optional later for cost); initial design assumes **one assessor per value** for consistency with current graph.  
- **NG3 — Canonical value library + embeddings** — that is semantic priority **#3**; this design should **leave hooks** (`value_id`, provenance) but not require pgvector.  
- **NG4 — Changing the 5×5 rubric shape** — keep **25 max per value** unless a separate ADR changes global rubric geometry.  
- **NG5 — Weighted combination of value aggregate with grounding** — explicitly out of scope; remains **conjunctive** per retrieval design.

---

## 3. Current implementation snapshot (as of this doc)

| Area | Current behavior | Target (see §§) |
|------|------------------|-----------------|
| `ValueDefinition` | `priority` unused | **Derived `provenance`**, **`raw_weight`**, final **`weight`**, **`craft_key`**, **`canonical_id`** — **§4.1** |
| Decoder (`value_decoder.py`) | **5–8** task-derived values when **no** library | With library: **`d`** in derived range; **5–8** = **total** domain — **§5.2**, canonical **§5.3.1** |
| `run_build_rubrics` | One LLM rubric per decoded value | Domain unchanged; **craft from templates** — **§5.3** |
| `merge_assessor_feedback` | Sort by `(total, value_id)` | **Weighted gap** + tie-break **§6.1** |
| Aggregate / stop | Sum of totals; single threshold env | **`A_domain` / `A_craft` / `A`**; **`SMART_WRITER_DOMAIN_*`**, **`SMART_WRITER_CRAFT_*`**, **`PLATEAU_EPSILON_*`** — **§7.6**; **no backward compat** on old env names — replace tests |
| Grounding | Separate track | Unchanged — **§7.3** |

---

## 4. Data model

### 4.1 Extend `ValueDefinition`

**Provenance (Option B — locked):** Do **not** store a separate `provenance` field. **`provenance`** is a **computed** property derived from origin keys (see `app/agents/models.py`):

- **`craft_key` set** → `designer_craft`  
- **`canonical_id` set** (mutually exclusive) → `library_canonical` (canonical domain library; see `design-canonical-value-rubric-library.md` — **`value_id`** must be **`LIB_<canonical_id>`**)  
- **neither** → `task_derived`

Also:

- **`raw_weight` (decoder / template input):**  
  - **Domain** rows: **`raw_weight: float`**, strictly positive, emitted by the **decoder** for each task-derived value (see **§4.5**).  
  - **Craft** rows: **`raw_weight`** comes from the **craft inventory** defaults (**§4.3.1**); not LLM-generated per run.  
- **`weight` (after `compose_values`):** the **final** `w_i` assigned to each row after **§7.5** only (`Σ_i w_i = 1` over all composed value rows). **Do not** store two competing schemes; there is **one** normalization pipeline.  
- **`craft_key: str | None`** — maps to the craft template row (e.g. `grammar_mechanics`) when set.

**Terminology:** The headline scalar **`A = Σ_i w_i · total_i`** with **`Σ w_i = 1`** is both a **weighted sum** of totals and a **weighted mean** on the **0–25** scale (same number). The doc standardizes on **§7.5–7.6** formulas; older wording about “sum vs mean” referred to **alternative normalization schemes**, which **do not** coexist—only **§7.5** applies.

**Weight source of truth (locked):** After composition there are three **conceptual** categories—**(1) Grounding** is a separate assessor and metric (see `design-retrieval-grounding.md`); it does **not** participate in value weights. **(2) Craft** values: **raw** weights from templates (**§4.3.1**), then **§7.5**. **(3) Domain:** **`task_derived`** — decoder emits **`raw_weight`**; **`library_canonical`** — **raw** weights from **canonical entry** metadata (see `design-canonical-value-rubric-library.md`); then **§7.5** on the **union** of domain rows. Optional **env/API overrides** to raw weights before **§7.5** (**§8.1**).

**Note on `priority` (today’s unused field):** In the current schema, `priority: int | None` was intended as an optional **ordinal hint** (“which value matters more when decoding,” e.g. 1 = highest). It was **never wired** to merge ordering, aggregates, or stopping (**§3**). That is different from **`weight`**, which should drive merge urgency and plateau/`targets_met` math. For v1: **do not** treat `priority` as a second economic knob unless we explicitly repurpose it (e.g. decoder-internal ordering only); prefer **`weight`** (and provenance) as the single importance signal for product behavior—or **remove** `priority` once `weight` is mandatory to avoid confusion.

**Deprecation note:** If `weight` is mandatory after composition, **`priority`** should be **removed** or narrowed to **decoder-internal ordering only**—avoid three overlapping concepts (`priority`, `weight`, `craft_key`) without clear roles.

### 4.2 `AssessorResult`

No structural change required if `value_id` still keys into rubrics; ensure **`provenance`**, **`raw_weight`**, and final **`weight`** are available at merge time via a side map **`value_id → (weight, provenance, …)`** from **`composed_values`** (or extended state).

### 4.3 Craft template artifact (code-local v1)

Suggested shape (Pydantic or dataclass in `app/agents/craft_values.py` or similar):

- `craft_key: str`  
- `value_id: str` (stable)  
- `name`, `description`  
- `ValueRubric` **template** — dimensions fixed; guidance text versioned in git.

**Versioning:** Bump a constant `CRAFT_RUBRIC_VERSION` when copy changes; log in `final_output` / turns for replay.

#### 4.3.1 Canonical craft inventory (v1 — initial set)

Stable **value_id**s and **default raw weights** `c_k` (equal by default; tune in code). Rubric text lives in templates; this table is the **single source** for ids and keys.

| `craft_key` | `value_id` | Default `c_k` | Notes |
|-------------|------------|-----------------|--------|
| `grammar_mechanics` | `CRAFT_GRAMMAR` | `1.0` | Spelling, grammar, basic mechanics |
| `clarity_coherence` | `CRAFT_CLARITY` | `1.0` | Sentence clarity, flow, coherence |
| `structure_length` | `CRAFT_STRUCTURE` | `1.0` | Structure, headings, length fit to brief |
| `diction_register` | `CRAFT_REGISTER` | `1.0` | Tone, register, word choice |

**Count `C` = 4** for this inventory; subset via `SMART_WRITER_CRAFT_KEYS` if needed. Copy may change without changing ids.

### 4.5 Decoder output schema (domain — locked)

The value-decoder returns **`DecodedValues`** whose `values` entries are **only** `task_derived` candidates. **`len(values)`** is **`d`**: when **no** library, **`MIN_DOMAIN ≤ d ≤ MAX_DOMAIN`** (same as **`DEFAULT_MIN_VALUES` / `DEFAULT_MAX_VALUES`**); when **`k`** library domain rows are already selected, **`max(0, MIN_DOMAIN − k) ≤ d ≤ MAX_DOMAIN − k`** (**canonical doc §5.3.1**). Validation may use a **dynamic** `min_length`/`max_length` on that list or an outer wrapper type once the library node exists.

Each entry **must** include:

| Field | Type | Rule |
|-------|------|------|
| `value_id` | `str` | Unique among domain values; must **not** use `CRAFT_*` prefix (reserved). |
| `name`, `description` | `str` | As today. |
| `raw_weight` | `float` | **> 0**. If missing or invalid: implementation may **reject** the decode step or **clamp** to a small ε and log a warning. Optional **upper cap** (e.g. 10.0) to avoid one value dominating raw space before **§7.5**. |

**Example** (illustrative JSON — field names align with `ValueDefinition` / decoder contract):

```json
{
  "values": [
    {
      "value_id": "V1",
      "name": "Donor alignment",
      "description": "…",
      "raw_weight": 1.5
    },
    {
      "value_id": "V2",
      "name": "Concrete program detail",
      "description": "…",
      "raw_weight": 1.0
    }
  ],
  "rationale": "…"
}
```

After **`compose_values`**, each row gains **`provenance`** and **`weight`** (final `w_i`).

### 4.6 Composed values for the run

After `decode_values`:

1. Load **craft** definitions + rubrics from templates (**§4.3–4.3.1**).  
2. Take **decoder output** as **task_derived** only (**§4.5**).  
3. **Merge lists** → single composed list with **total count** within **§5.2** limits.  
4. Apply optional **raw-weight overrides** (**§8.1**), then compute **final `w_i`** via **§7.5**.

**State (locked):** Keep **`decoded_raw`** (decoder output **before** craft injection and before final weights) **and** **`composed_values`** (full list with `provenance`, **`raw_weight`**, **`weight`**). Downstream nodes (`build_rubrics`, writer, assess) use **`composed_values`** (or an agreed alias for `decoded` in code). **`decoded_raw`** is for **debugging / replay** only.

---

## 5. Pipeline / graph changes

### 5.1 Placement

**Option A (recommended):** New small node **`compose_values`** immediately after **`decode_values`**:

`decode_values` → **`compose_values`** → `build_rubrics` → …

- **`compose_values`:** inject craft `ValueDefinition`s + attach craft rubrics into state **or** mark craft for “skip LLM rubric build.”  
- **`build_rubrics`:** for `task_derived` only, call existing `run_build_rubrics`; for craft, use templates.

**Option B:** Single “super-node” that decodes and composes in one step—less clear separation for tests.

### 5.2 Count and limits

Let:

- **`C`** = number of **craft** values (fixed small, e.g. 4).  
- **`T`** = **total domain** row count after composition = **`library_canonical` + `task_derived`** (decoder output length **`d`** plus **`k`** library rows when the canonical library is enabled).  
- **`MIN_DOMAIN` / `MAX_DOMAIN`** = same product bounds as **`DEFAULT_MIN_VALUES` / `DEFAULT_MAX_VALUES`** (e.g. 5–8).

**Constraint (locked) — domain vs craft:**

- **`MIN_DOMAIN ≤ T ≤ MAX_DOMAIN`** always (for the composed **non-craft** value rows).  
- **Craft is not counted in `T`.** Total **value** assessors per iteration = **`C + T`** (not **`C + d`** alone when **`k > 0`**).

**Baseline — canonical library off (`k = 0`):** **`T = d`**; the decoder list length must satisfy **`MIN_DOMAIN ≤ d ≤ MAX_DOMAIN`**. This matches today’s **`DecodedValues`** validation.

**With canonical library (`k ≥ 1`):** **`T = k + d`**; **`d`** must satisfy **`max(0, MIN_DOMAIN − k) ≤ d ≤ MAX_DOMAIN − k`**. See **`design-canonical-value-rubric-library.md` §5.3.1**.

This **increases cost / TPM** versus a single-critic app when **`C`** is large; the product goal for v1 is **differentiation and correct weighting**, not minimizing calls. **Cost optimization** (fewer assessors, bundled craft, etc.) is explicitly **deferred** until the value prop is proven.

**Rejected for v1:** Capping **`C + T`** at a historical **`8`** by shrinking domain unless we later reintroduce it as an optional tuning knob.

### 5.3 Rubric build efficiency

- **Craft:** no per-run LLM rubric generation in **P0**; use static templates.  
- **Task-derived:** unchanged parallel `run_build_rubrics` paths.

Optional **P2:** “Refresh craft anchors” LLM pass that only rewrites guidance strings inside fixed dimension names—still deterministic schema.

---

## 6. Merge and writer-facing feedback

### 6.1 Weighted ordering

Replace pure `total` sort with a **primary key** that reflects importance × urgency:

- **Weighted gap:** `score_sort = weight * (RUBRIC_MAX_TOTAL - total)` — larger means “more urgent per product priority.”  
- **Tie-break (locked, deterministic):** sort by **`score_sort` descending**, then **`provenance`** with **`task_derived` before `designer_craft`**, then **`value_id` ascending** (lexicographic). Same tie-break inside the value block of **`merge_value_and_grounding_feedback`**.

Header text in `merge_assessor_feedback` should state that ordering is **weight-aware**, not only “lowest total first.”

### 6.2 Grounding merge

`merge_value_and_grounding_feedback` keeps retrieval design order: **grounding MUST_FIX** first, then **value block**, then grounding SHOULD_FIX. Inside the value block, use the same **weighted** ordering as **§6.1**.

### 6.3 Writer prompt

Pass a short **“priority table”** (value name, weight, provenance) in the writer deps so the model knows which tradeoffs favor domain vs craft when instructions conflict—without replacing structured merge text.

---

## 7. Scoring, plateau, and `targets_met`

### 7.1 Weighted aggregate (value track only)

Define explicitly in code and tests one of:

1. **Weighted sum:** `A = Σ w_i * total_i` (scale grows with count; epsilon must scale).  
2. **Weighted mean:** `A = (Σ w_i * total_i) / (Σ w_i)` (stays on ~`0–25` scale; **easier** to reuse `plateau_epsilon` semantics).

**Recommendation:** **Weighted mean** over **all value rows** (craft + domain) for a single **headline value-track number** `A` when one scalar is needed—plateau comparability with “per-value on 0–25” intuition.

**History:** `aggregate_history` can record this **`A`** each iteration for continuity with today’s **`aggregate_value_score`** (see `design-retrieval-grounding.md` **§7.4**). **Additionally**, per **§7.2**, maintain **separate** domain- and craft-**subset** aggregates (and histories) for **conjunctive** `targets_met` and **per-track** plateau epsilons—do not rely on `A` alone for pass/fail once craft is enabled.

### 7.2 `targets_met` and plateau (value side) — domain vs craft

**Locked intent:** Use the **same logical construct** for **craft** and for **domain** (mirroring each other), not a single vague “one number wins.”

- **Domain (`task_derived`):**  
  - **Aggregate `A_domain`:** weighted mean over domain rows (renormalized within domain—**§7.6**). Tracked in **`domain_aggregate_history`** each iteration.  
  - **Per-value floor:** each domain value `total_j ≥ SMART_WRITER_DOMAIN_PER_VALUE_FLOOR` (**§7.6**).  
  - **`targets_met`:** conjunctive **`A_domain` ≥ target** **and** per-domain floors (**§7.6**).  
  - **Plateau:** **`SMART_WRITER_PLATEAU_EPSILON_DOMAIN`** on **`domain_aggregate_history`** over `plateau_window` (**§7.4**, **§7.6**).

- **Craft (`designer_craft`):**  
  - **Aggregate `A_craft`:** weighted mean of craft totals only (renormalized within craft—**§7.6**). Tracked in **`craft_aggregate_history`**.  
  - **Per-craft floor:** each craft `total_k ≥ SMART_WRITER_CRAFT_PER_VALUE_FLOOR`.  
  - **`targets_met`:** conjunctive **`A_craft` ≥ target** **and** per-craft floors (**§7.6**).  
  - **Plateau:** **`SMART_WRITER_PLATEAU_EPSILON_CRAFT`** on **`craft_aggregate_history`**—parallel to domain (**§7.6**).

**Conjunction:** Value-side “done” requires **both** craft and domain gates to pass (in addition to **grounding** when enabled—**§7.3**). Do **not** blend craft + domain into one headline score for pass/fail; use **conjunctive** sub-gates.

### 7.3 Grounding conjunct

Unchanged: when `grounding_enabled`, `targets_met` still requires `grounding_score ≥ threshold`. **No** weight ties grounding to value aggregate.

### 7.4 Epsilon scaling

If switching from **sum** to **weighted mean**, re-tune default **`plateau_epsilon`** (and document migration): a delta of `0.5` on a **sum of six totals** is not the same as on a **mean**.

### 7.5 Weight normalization (locked — §13.3)

**Inputs:**

- **Craft** values `k ∈ K`: designer **raw** weights `c_k > 0` from templates/config (one row per craft `value_id`).  
- **Domain** values `j ∈ D` (**all non-craft** composed rows: **`library_canonical` ∪ `task_derived`**): **raw** weights **`d_j > 0`** — from the **decoder** for `task_derived`, from **canonical entry** metadata for `library_canonical` (strictly positive; clamp or reject on bad input—implementation detail).

**Group mass (craft vs domain):** Let **`α` = `SMART_WRITER_CRAFT_WEIGHT_MASS`** ∈ `(0, 1)` when both `K` and `D` are non-empty. Meaning: **`α`** is the fraction of **total** normalized weight allocated to the **craft** group; **`1 − α`** to the **domain** group.  
- Normalize within craft: `c'_k = c_k / Σ_{i∈K} c_i`.  
- Normalize within domain: `d'_j = d_j / Σ_{i∈D} d_i`.  
- **Final weights:** `w_k = α · c'_k` for craft; `w_j = (1 − α) · d'_j` for domain.  
- **Check:** `Σ w_k + Σ w_j = 1` over all composed values.

**Edge cases:**

- **Craft off or `C = 0`:** set `α = 0`; only domain weights normalize to sum `1`.  
- **Domain empty (degenerate):** not supported; **`compose_values`** must ensure **`|D| ≥ MIN_DOMAIN`** (**total** domain rows, library + task-derived) before run.

**Why two-stage:** Separates **“how much of the budget is craft vs domain”** (`α`, product/env) from **“within-group relative importance”** (template ratios vs decoder ratios). Tuning `α` does not force rescaling every decoder weight by hand.

### 7.6 Aggregates, env var names, and state (locked — §13.3)

**Definitions** (all on **0–25** per-value total scale):

- **Headline `A`:** weighted mean over **all** value rows using final `w_i`:  
  `A = Σ_i w_i · total_i` (equivalently `(Σ w_i total_i) / 1` since `Σ w_i = 1`). Same as **§7.1** recommendation.  
- **`A_domain`:** weighted mean over **domain-only** rows using **only** the domain weights renormalized to sum to 1 within `D`:  
  `w'_j = d'_j` (i.e. `w_j / (1−α)` when `α < 1`).  
  `A_domain = Σ_{j∈D} w'_j · total_j`.  
- **`A_craft`:** weighted mean over **craft-only** rows using weights renormalized within `K`:  
  `w''_k = c'_k`.  
  `A_craft = Σ_{k∈K} w''_k · total_k`.

**`targets_met` (value side, craft enabled):**

| Gate | Rule |
|------|------|
| Domain aggregate | `A_domain ≥ SMART_WRITER_DOMAIN_AGGREGATE_TARGET` |
| Domain per-value | each domain `total_j ≥ SMART_WRITER_DOMAIN_PER_VALUE_FLOOR` |
| Craft aggregate | `A_craft ≥ SMART_WRITER_CRAFT_AGGREGATE_TARGET` |
| Craft per-value | each craft `total_k ≥ SMART_WRITER_CRAFT_PER_VALUE_FLOOR` |

(When craft is disabled, omit craft rows and craft gates; domain-only thresholds apply.)

**Plateau:** Separate histories for **domain** and **craft** aggregates (see below).  
- **Domain plateau:** `len(hist_dom) > plateau_window` and `(hist_dom[-1] − hist_dom[-1−pw]) < SMART_WRITER_PLATEAU_EPSILON_DOMAIN`.  
- **Craft plateau:** same pattern with `hist_craft` and **`SMART_WRITER_PLATEAU_EPSILON_CRAFT`**.

**Defaults (starting point; tune with evals):**

| Variable | Default | Notes |
|----------|---------|--------|
| `SMART_WRITER_CRAFT_WEIGHT_MASS` | `0.35` | Craft share `α` of global weight budget |
| `SMART_WRITER_DOMAIN_AGGREGATE_TARGET` | `18.0` | Aligns with strong domain bar (~18/25 mean) |
| `SMART_WRITER_DOMAIN_PER_VALUE_FLOOR` | `12.0` | Low floor; stricter “good” via aggregate target |
| `SMART_WRITER_CRAFT_AGGREGATE_TARGET` | `20.0` | Slightly stricter than domain (hygiene bar) |
| `SMART_WRITER_CRAFT_PER_VALUE_FLOOR` | `15.0` | No ship with very weak craft dimension |
| `SMART_WRITER_PLATEAU_EPSILON_DOMAIN` | `0.5` | On **0–25** mean scale for `A_domain` |
| `SMART_WRITER_PLATEAU_EPSILON_CRAFT` | `0.5` | On **0–25** mean scale for `A_craft`; may tighten later |

**Dual plateau stop (value track):** When **craft is enabled**, value-side plateau requires **both** domain and craft plateau conditions (**§7.6** histories and epsilons). When **craft is disabled**, only **domain** plateau applies (`craft_aggregate_history` unused).

**State / persistence (locked):** Store **`domain_aggregate_history`** and **`craft_aggregate_history`** as **first-class lists on `AgentState`** (one float per completed assess round), not derived-only in logs. Rationale: deterministic **stop/replay** in tests and Supabase `final_output` without recomputing from turns. **`aggregate_history`** may still record headline **`A`** for API continuity (`aggregate_value_score` naming).

### 7.7 Role of headline `A` and `aggregate_history` (clarification)

| Question | Answer |
|----------|--------|
| What is **`A`** for? | One **headline** number on the **0–25** scale for **API / dashboards** (`aggregate_value_score` = last **`A`**). Useful for “how good is the rubric bundle overall” without splitting craft vs domain in the UI. |
| Does **`A`** gate **stop** when craft is enabled? | **No.** **`targets_met`** and **plateau** on the value track use **`A_domain`**, **`A_craft`**, and their **histories** (**§7.2**, **§7.6**), not **`A` alone**. |
| Does **`aggregate_history`** control plateau? | With craft enabled, **plateau** uses **`domain_aggregate_history`** and **`craft_aggregate_history`**. Do **not** require headline **`A`** to plateau for exit when **§7.6** dual tracks are active. |
| Why keep **`A` at all?** | Continuity with **retrieval grounding** doc and external metrics; optional **Logfire** / product summary. |

### 7.8 Stop routing vs assessor batching (clarification)

**What this is not:** It is **not** about **run order of assessors** or “who the writer sees first.” Assessors still run in parallel (subject to concurrency), **merge** runs once, and the **writer** receives **all** merged feedback in one shot.

**What “evaluation order” meant (§16):** Only **`stop_reason`** and the **conditional edge** after merge: the code checks exit conditions in a **defined order** so a single run ends with **one** reason (e.g. `max_iterations` vs `targets_met` vs `plateau`). That avoids ambiguity in logs and tests—not a preference for one assessor’s data over another.

**Suggested check order (align with `design-retrieval-grounding.md` §7.6):**

1. **`max_iterations`** — hard cap.  
2. **`targets_met`** — all conjunctive gates pass: **value side** (domain + craft per **§7.6** when craft on; domain-only when craft off) **and** **grounding** when `grounding_enabled`.  
3. **`plateau`** — **value track:** domain plateau **and** craft plateau when craft on (**§7.6**); **and** grounding plateau when grounding enabled (**retrieval doc**).  
4. Otherwise continue to **writer** (or **`completed`** if the graph ends without the above).

**Precedence:** Evaluate **`targets_met`** before **`plateau`** for the same round (success exit should win). **`max_iterations`** overrides if the iteration cap is hit.

### 7.9 Worked numeric example (weights and aggregates)

Assume **`α = 0.35`**, **two craft** rows with **`c_k = 1`** each, **two domain** rows with decoder **`d_j = 1.5`** and **`1.0`**. Within-group: `c' = (0.5, 0.5)`, `d' = (0.6, 0.4)`. Final: **`w_k = 0.35 × c'`** → craft `0.175` each; **`w_j = 0.65 × d'`** → domain `0.39`, `0.26`. Check: `0.175+0.175+0.39+0.26 = 1.0`.

Mock **totals** (0–25): craft `20`, `18`; domain `17`, `22`. Then:

- **`A`** = `0.175×20 + 0.175×18 + 0.39×17 + 0.26×22` ≈ **19.0** (headline).  
- **`A_craft`** = `0.5×20 + 0.5×18` = **19**.  
- **`A_domain`** = `0.6×17 + 0.4×22` = **19**.

(Numbers chosen for illustration only.)

---

## 8. Configuration and API

### 8.1 Environment / config (suggested)

| Variable | Purpose |
|----------|---------|
| `SMART_WRITER_CRAFT_ENABLED` | `1` / `0` — toggle craft injection |
| `SMART_WRITER_CRAFT_KEYS` | Optional subset of craft keys to enable |
| `SMART_WRITER_CRAFT_WEIGHT_MASS` | `α` ∈ (0,1): share of normalized weights for **craft** vs domain (**§7.5**); default **0.35** |
| `SMART_WRITER_VALUE_WEIGHTS` | Optional JSON **`value_id` → positive float** overriding **`raw_weight`** **before §7.5** (applied to **both** domain `value_id`s and craft `value_id`s present in the run). Does **not** replace **`α`**; final **`w_i`** still from **§7.5**. |
| Craft template raw weights | In code / `craft_values` module per `value_id` (feeds `c_k` before **§7.5**) |
| `SMART_WRITER_DOMAIN_AGGREGATE_TARGET` | `targets_met`: minimum **`A_domain`** (**§7.6**) |
| `SMART_WRITER_DOMAIN_PER_VALUE_FLOOR` | `targets_met`: minimum each domain value total |
| `SMART_WRITER_CRAFT_AGGREGATE_TARGET` | `targets_met`: minimum **`A_craft`** |
| `SMART_WRITER_CRAFT_PER_VALUE_FLOOR` | `targets_met`: minimum each craft value total |
| `SMART_WRITER_PLATEAU_EPSILON_DOMAIN` | Plateau on **`A_domain`** history (**0–25** mean scale) |
| `SMART_WRITER_PLATEAU_EPSILON_CRAFT` | Plateau on **`A_craft`** history (**0–25** mean scale) |
| `plateau_window` | Shared window length (same semantics as today; request/env) |

**Legacy env (no compatibility layer):** **`SMART_WRITER_VALUE_PER_VALUE_TARGET`** and undifferentiated **`plateau_epsilon`** (sum-scale) are **superseded** by **`SMART_WRITER_DOMAIN_*`** and **`SMART_WRITER_PLATEAU_EPSILON_DOMAIN`** in **§7.6**. Remove or rename in code when implementing; **update tests** accordingly (**§3**).

### 8.2 HTTP / CLI (later phase)

- Optional request fields: `craft_enabled: bool`, `value_weights: dict[str, float] | None` with validation (positive, caps).  
- Document that **omitted** means **defaults from env**.

---

## 9. Persistence and observability

- **`append_turn`:** log composed values with **`provenance`, `weight`, `craft_key`**.  
- **`final_output`:** include `craft_rubric_version`, list of `value_id` with **final `w_i`**, last **`A`**, **`A_domain`**, **`A_craft`**, and compact **`domain_aggregate_history` / `craft_aggregate_history`** tails if size-bounded.  
- **Logfire:** span attributes `craft_count`, `domain_count`, `weighted_mean_aggregate` (`A`), `A_domain`, `A_craft`.

---

## 10. Testing strategy

- **Unit:** weighted merge order (construct three assessors with different totals/weights; assert order).  
- **Unit:** weighted mean aggregate and plateau with synthetic history.  
- **Unit:** `_value_targets_met` with mixed craft/domain thresholds.  
- **Integration (mocked):** graph runs with craft disabled vs enabled; assessor call count = `C + D`. **No requirement** for legacy pure-`total` merge ordering; update tests when behavior changes (**§13.2**).

---

## 11. Phased delivery

Phases are **delivery order**, not alternate physics: **§7.5–7.6** is the **single** target behavior. Earlier phases may **stub** (e.g. decoder emits **`raw_weight: 1.0` everywhere**) but must not introduce a second normalization scheme.

| Phase | Scope |
|-------|--------|
| **P0** | Models; **§4.3.1** craft inventory + templates; **`compose_values`**; **`decoded_raw` + `composed_values`** (**§4.6**); decoder **`raw_weight`** (**§4.5**) and prompt to **exclude** craft duplication; **§7.5** final weights; weighted merge **§6.1**. |
| **P1** | **`A`**, **`A_domain`**, **`A_craft`** + histories; **`targets_met`** + dual plateau per **§7.6**; env defaults **§8.1**; replace legacy aggregate/stop tests. |
| **P2** | HTTP/CLI **`value_weights`** overrides; writer **priority table** **§6.3**; eval tuning. |
| **P3** | Optional LLM refresh of craft anchors; optional single “craft bundle” assessor for cost. |

---

## 12. Alignment with other semantic priorities

| Priority | Interaction |
|----------|-------------|
| **1 — Retrieval grounding** | Orthogonal; **conjunctive** stopping. Weighted value aggregate **must not** absorb grounding. |
| **3 — Canonical library** | Craft `value_id`s are the first **stable library** entries; future embedding match can map decoder outputs to **task_derived** aliases. |
| **4 — Versioned prompt program** | Craft rubrics and decoder/writer instructions are **versioned artifacts**; fits the same git + eval loop. |
| **5 — Research / plan phase** | Planner can set **domain weights** higher for research-heavy tasks; not required for P0. |

---

## 13. Decisions to lock in implementation

### 13.1 Resolved in this draft

- **Grounding:** No weighted blend across value vs grounding (**§1**, **§2.2 NG5**).  
- **Craft rubrics:** Template-first in P0; LLM rubric build only for **task_derived**.  
- **Headline value aggregate:** Prefer **weighted mean** over all value rows for `A` / reporting where one number is shown (**§7.1**); **craft vs domain sub-aggregates** for gates (**§7.2**).  
- **Merge:** Use weight × gap (or equivalent) for ordering (**§6.1**).  
- **Product review (§13.2):** Domain-only decoder slot limits; decoder-emitted domain weights; craft/domain parallel threshold structure; English craft; no legacy ordering requirement—see **§13.2–13.3**.

### 13.2 Resolved in review (product alignment)

The following were **open** in the prior draft; answers below are **folded into §§4–8** and the decision log (**§15**).

1. **Global max assessors:** **`DEFAULT_MAX_VALUES` / `DEFAULT_MIN_VALUES` apply to domain only**; craft adds **`C`** on top (`C + D` assessors per round). Higher cost/TPM is **accepted** for v1 to prove differentiation; optimization later (**§5.2**).

2. **Weight source of truth:** **Three tracks:** **Grounding** — separate assessor/metric, **not** part of value weights. **Craft** — weights **fixed by design** (templates + normalization). **Domain** — **decoder emits suggested weights** per value; env/API overrides optional (**§4.1**).

3. **`targets_met` / plateau for craft:** Same **construct** as domain: **aggregate-craft** threshold, **per-craft floors**, **absolute targets** for pass, and a **dedicated epsilon** on the **craft aggregate history** for plateau—**parallel** to domain (**§7.2**).

4. **`priority` field:** Explained in **§4.1** (was an unused ordinal hint vs **`weight`**). **Prefer removal or decoder-internal-only use**; **`weight` is the behavioral lever.**

5. **Backward compatibility:** **Not required.** Update regression tests to match weighted / craft-aware behavior (**§10**).

6. **Locale for craft rubrics:** **English-only for v1**; no locale-specific craft templates required initially (**§4.3**).

7. **`assess_parallel` vs “craft group”:** The graph already **waits for all value + grounding assessors** before the next writer iteration. **No separate sequential “craft-only” phase** is required for correctness; TPM is handled by **`max_concurrent_llm`** and provider limits, not by splitting craft vs domain into different barrier semantics.

### 13.3 Implementation locks (resolved)

See **§7.5** (normalization via **`SMART_WRITER_CRAFT_WEIGHT_MASS`**), **§7.6** (env names, defaults, **`A_domain` / `A_craft`**, dual plateau), and **§9** (state + **`final_output`**). No open items under this heading.

---

## 14. Summary

This design splits **designer craft / hygiene** values (template rubrics, always on) from **task-derived** decoder values, assigns **explicit weights** (**fixed craft**, **decoder-suggested domain**), and uses **§7.5** normalization and **§7.6** env-backed gates in **merge ordering** and in **domain- and craft-specific aggregates** (each with floors, targets, and plateau epsilons) for **value-track** motion and reporting—without merging the value signal with **grounding** for exit logic. **Domain-only** slot limits apply; **total assessors = `C + D`**, trading cost for differentiation until optimized later. Implementation centers on a **`compose_values`** step, craft template assets, **decoder outputs for domain raw weights**, **`domain_aggregate_history` / `craft_aggregate_history`** on state, and deterministic changes to `feedback_merge` and headline **`aggregate_history`**.

---

## 15. Decision log and review notes

| Topic | Decision | Doc anchor |
|-------|----------|------------|
| Value vs grounding | **Conjunctive** gates only; no cross-track weighted headline | **§1**, **§2.2 NG5** |
| Craft rubrics | **Template-first**; no per-run LLM in P0 | **§4.3**, **§5.3** |
| Domain slot limits | **`DEFAULT_MAX/MIN` apply to domain only**; craft adds `C` assessors (`C + D` total) | **§5.2**, **§13.2** |
| Weights | **Craft:** fixed in design/config; **Domain:** **decoder-emitted**; **Grounding:** separate track (no value weights) | **§4.1**, **§13.2** |
| Plateau / targets (value) | **Domain** and **craft** each: aggregate threshold, per-value floors, **`targets_met`**, and **epsilon on aggregate history** | **§7.2** |
| Plateau signal (overall value reporting) | **Weighted mean** of per-value totals for API/history naming where “one number” is needed (**§7.1**); craft/domain sub-aggregates per **§7.2** | **§7.1–7.2** |
| Merge | **Weight × gap** sort; grounding block order unchanged | **§6.1–6.2** |
| Decoder | **Domain-only** values + **emits weights**; no craft duplication | **§2.1 G3**, **§4.1** |
| Backward compatibility | **Not required**; update tests | **§10**, **§13.2** |
| Craft locale | **English** templates for v1 | **§13.2** |
| Parallel assessors | **No special craft-only barrier**; same iteration gate; TPM via concurrency env | **§13.2** |
| Weight normalization | Two-stage: **within-group** normalize, then **`SMART_WRITER_CRAFT_WEIGHT_MASS` (`α`)** splits mass between craft and domain | **§7.5** |
| `A_domain` / `A_craft` | Renormalized means within each group; separate **histories** and **plateau epsilons** | **§7.6** |
| Env defaults | **§7.6** table (`DOMAIN` / `CRAFT` targets, floors, `PLATEAU_EPSILON_*`) | **§7.6**, **§8.1** |
| State | **`domain_aggregate_history`**, **`craft_aggregate_history`** first-class; headline **`A`** in **`aggregate_history`** | **§7.6**, **§9** |

---

## 16. Review appendix — status after incorporation

Original **§16** lists drove updates throughout the doc. Below: **where each item landed**, plus a short **FAQ** for the common confusion about “evaluation order.”

### FAQ — “Why evaluation order?” (§16a1)

**Your mental model is right for the writer:** all assessors complete, merge runs once, the writer sees **all** feedback in one shot. Nothing in “evaluation order” changes that.

**“Order” only applies to the `if`/`else` that decides `stop_reason` after a round** (continue loop vs end): e.g. if both **max iterations** and **targets_met** could apply, the code must pick **one** reason for logs/API. That is **not** precedence among assessors and **not** about feeding the writer faster. See **§7.8**.

### Incorporation map

| Original §16 item | Resolution |
|-------------------|------------|
| **a1** Stop / precedence | **§7.8** (routing vs batching); **§7.3** grounding conjunct |
| **a2** Decoder schema | **§4.5** (fields + example JSON) |
| **a3** Craft inventory | **§4.3.1** (table + default `c_k`) |
| **a4** Legacy env | **§8.1** paragraph “Legacy env”; **§3** target column |
| **a5** Merge tie-break | **§6.1** (locked sort key) |
| **b1** One normalization scheme | **§4.1** (single pipeline; terminology note on sum/mean when `Σw=1`) |
| **b2** §11 vs §7.6 | **§11** phased delivery rewritten |
| **b3** Headline `A` | **§7.7** |
| **b4** `decoded_raw` vs composed | **§4.6** |
| **b5** `VALUE_WEIGHTS` | **§8.1** row for `SMART_WRITER_VALUE_WEIGHTS` |
| **c1** Numeric example | **§7.9** |
| **c2–c5** Diagram, decoder contract bullets, cross-doc `stop_reason`, §3 column | **Partially done:** §3 updated; **optional follow-ups:** mermaid diagram, explicit decoder must/must-not list under **§4.5**, cross-doc table in `design-retrieval-grounding.md` or here |

---

*End of document.*
