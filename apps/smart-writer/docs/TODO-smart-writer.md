It runs for a long time. We need to find optimization ideas - both from cost point of view and from the time run point of view
We need to find ways to "personalize" the design to make it better or at least unique compared to other similar solutions.
We also need to code the solution to do a lot more research - get content from internet to write and critique. In addition to the style, the major part is to actually find the content that is factual, relevant and not ahllucinated.

Some thoughts:
1: Maintain a list of values -and its rubrik - that persists and grows over time.  When the value_decoder identifies a value, it first checks against an existing list. if there is a matching value, it uses that instead of creating a new rubrik, it uses existing one.  When it does not find it in the list, it creates a new one - and adds it to the list.  Core idea being, that the list of values should be finite ( say 15 to 20 max). We don't have to spend cycles and llm to discover and generate them again and again. We might require a vector database concept to see if the two values are very close - and therefore nealy identical

2: There should be a set of preppolutaed prompts - both system and user or at least system - which get the output very close to the ideal on first iteration itself. The pre-poulated prompts can have a set of parameters that are default initialized, even if the user prompt does not mention it. This system prompt can be iteratively improved at design revision times - over time - to make the service better.  It makes sense for the writer.  But it may also make sense for rubrik builder, value_decoder.  Most interestingly if we can find a way to create a good system prompt even for the "variable" assessor, it gives the opportunity to make the writer personalized and constrained.

3: Currently we are putting equal weight on each value. That is probably overly simplistic. There should be relative weights for the value.

4: Have two set of values. One designer defined - which are always present. Things like grammar, paragraph construction, length etc. Second derived or user defined.  This is also from the perspective of making the solution unique and differentiated.

5: When I ran one iteration, I noticed that it just used general english concepts. How do we nudge it to be a lot more "reserach" oriented. Go out and uncover information from internet. Use that to write content that is relevant to the purpose.

--------
Other  ideas:



-------
Prioritized list (aligned with `Improvement-suggestions.md` — semantic section)

Crosswalk to the five semantic priorities there:

| Your # | Maps to semantic priority # | Comment |
|--------|----------------------------|---------|
| 5 (research / internet / factual) | **1** (retrieval, citations, fact discipline) and **5** (planning/research phase) | Strongest “better than chat” lever; implement retrieval + optional plan step before draft. |
| 1 (persistent values + rubrics + vectors) | **3** (canonical library + similarity) | Also helps **cost/time** (your opening note). |
| 2 (pre-populated / versioned prompts) | **4** (prompt program) | High leverage on first-iteration quality; do not skip eval-driven iteration on prompts. |
| 3 (weights) | **2** (weighted values + designer vs derived) | Combine with #4 in your list: hygiene values + weights together. |
| 4 (designer vs user values) | **2** (same) | Same design bucket as weights; implement as two layers in the schema and merge. |

---
## Review / feedback (maintainer notes)

**On runtime and cost (opening paragraph)**  
The pipeline is inherently multi-call (decode → many rubrics → loop of writer + N assessors). Gains will come from **reusing rubrics** (your idea 1), **cheaper models** for assess/rubric where safe, **lowering N** or **capping iterations**, and **parallelism within TPM limits**—not from expecting a single LLM call. Treat “long runtime” as a product expectation and surface progress (already noted elsewhere for HTTP).

**Idea 1 — Canonical values + rubrics**  
This is sound and belongs in the **top semantic list as priority #3**. It improves **consistency** (semantic stability) and **efficiency**. Watch for: governance (who approves new canonical values), versioning when rubrics change, and not over-merging distinct values just because embeddings are close—keep a **similarity threshold** and optional human gate for new entries.

**Idea 2 — Pre-populated / versioned prompts**  
Strong agreement. This is **priority #4** in the semantic list. Variable assessors can still share a **template** with slots for rubric-specific anchors; “one mega prompt per assessor” is not required. Version prompts in git, A/B with offline evals.

**Idea 3 — Relative weights**  
Agree; pair with **idea 4** (designer vs derived). Implementation-wise, weights should affect **merge ordering**, **aggregate score**, and possibly **which assessor feedback the writer must not ignore**. Document whether weights are user-supplied, inferred, or defaulted by genre.

**Idea 4 — Designer-defined vs user-derived values**  
This is the right split for differentiation. “Grammar / structure / length” as always-on **craft** values avoids the decoder inventing redundant criteria and matches how editors think. Keep the count bounded so the assessor fan-out stays manageable.

**Idea 5 — Research-oriented, internet-grounded**  
This is the main **semantic** gap today. It maps to **priority #1** (grounding + citations) and **#5** (explicit research/plan phase). Browsing without **citation discipline** can increase hallucination risk—prefer **retrieval with snippets**, **allowed domains**, and **“cite or omit”** rules in the writer and a **lightweight critic** pass for unsupported claims.

**Bottom line**  
Your TODO items **1–5** align well with the five semantic priorities in `Improvement-suggestions.md`; the only ordering nuance is that **grounding/research (#5 in your list)** is listed **first** there because it most directly improves *truth and substance* vs. generic chat fluency. **Canonical rubrics (your #1)** is third there because it improves stability and cost but does not by itself fix factual depth.


1:  Adapt the Supabase tables for the new structure

2: **App configuration layer (holistic)** — Today many tunables (including `SMART_WRITER_MAX_CONCURRENT_LLM` / `DEFAULT_MAX_CONCURRENT_LLM`) are surfaced via environment variables and `.env` as a delivery mechanism. Introduce a unified **application config** story: typed defaults in code, optional committed config file for non-secret parameters, `.env` / platform env for secrets and deploy overrides, and clear precedence. Fold `MAX_CONCURRENT_LLM` and other `SMART_WRITER_*` knobs into that model so configuration is not scattered across `os.getenv` and workspace-level tooling. (Tracked here; implement when focusing on the app layer.)

