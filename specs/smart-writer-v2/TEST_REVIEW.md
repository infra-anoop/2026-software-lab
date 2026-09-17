# Independent test review — smart-writer-v2 (US1 contract / catalog-auto)

**Reviewer role:** Independent test reviewer (did not write these tests; no loyalty to their wording)  
**Brief:** `docs/agent-os/TEST_REVIEW_PROMPT.md` (constitution §V)  
**Feature:** `specs/smart-writer-v2/`  
**Tests under review:** T016–T019 + T015  
**Date:** 2026-09-16  

**Scope files**

| Task | File |
|------|------|
| T015 | `apps/smart-writer-v2/tests/contract/test_preview_gate.py` |
| T016 | `apps/smart-writer-v2/tests/contract/test_generate_job.py` |
| T017 | `apps/smart-writer-v2/tests/contract/test_claim_provenance.py` |
| T018 | `apps/smart-writer-v2/tests/contract/test_web_signal.py` |
| T019 | `apps/smart-writer-v2/tests/contract/test_grant_humor_default.py` |
| shared | `apps/smart-writer-v2/tests/contract/grant_flow.py` |

**Pytest (app venv, 2026-09-16):** T016–T019 fail at `grant_flow.submit_grant_and_wait` — `POST /v1/conversations/{id}/messages` → `404 {"detail":"Not Found"}`. T015 both cases **pass**. Health smoke (not in this T\* gate) passes.

No `acceptance.md` `how: auto` rows exist yet (T061 / plan P2). Hybrid structural mapping is what this slice claimed.

---

### A. Executive verdict

**Approve tests with minor edits**

T016–T019 collect against the live FastAPI app, do not import a graph stub, and fail today because the generate turn does not exist. That is honest red, not an import error. Helper `grant_flow.py` hits the public contract with a filled-slot grant prompt (not the P5 clarify fixture) and deletes `TAVILY_API_KEY` for the noop-web path.

They encode contract hooks 2, 4, and 5 as JSON shape, plus the structural half of hybrid catalog rows `claim.provenance`, `research.used_or_declared`, and `grant.default_humor_low`. They would **not** fail closed on checkable provenance (orphan `source_id` / one `uncertain` stub), F7 `citation_mode=panel`, or F3 as a property-profile lock (T019 reads a store default via an uncontracted snapshot). T015 already green (T009/T012 done): 401 on create-conversation is real; 503-unset and spend-route 401s are untested.

Do not implement matching product code until Debates **T1–T3** are human-adjudicated (constitution §F). T028 remains blocked on US3 / T043 regardless.

---

### B. Findings table

| ID | Severity | Lens | Locus | Finding | Suggested resolution |
|----|----------|------|-------|---------|----------------------|
| **T1** | **Debate** | Lock fidelity | `test_claim_provenance.py`; catalog `claim.provenance`; hook 4; P4 | Steelman: requires `claims[]` nonempty and `grounded`+nonempty `source_id` or `uncertain`+`null` — not “`sources[]` nonempty,” which is what P4 asked. Attack: a single `{status: uncertain, source_id: null, excerpt: "x"}` greens the test while SC-003 “checkable provenance” fails. Grounded `source_id` is never required to appear in `artifact.sources[]`. `excerpt` is never required to be a span of `body`. Fixture prompt already contains org/funder facts; SC-003 is *when the draft asserts facts beyond the prompt*. Requiring ≥1 claim can force theater; not binding claims to sources/body allows theater. | Before T021: if `grounded`, `source_id` ∈ `artifact.sources[].source_id`; `excerpt` substring of `body`. Keep ≥1 claim only if the fixture’s materials path is the intended “beyond prompt” trigger — or drop the length floor and fail only on malformed rows. Do not pytest ≥2 fit points (hybrid/human). |
| **T2** | **Debate** | Wrong-thing / over-constrain | `test_grant_humor_default.py`; catalog `grant.default_humor_low`; F3; http-api GET snapshot | Steelman: grant default `humor_enabled=false` is a data-model field (F3 / FR-006b); test waits for generate success then reads it. Attack: observation is `GET /v1/conversations/{id}` with `_humor_enabled` accepting top-level **or** `run_state` — the contract says internal state is **redacted** by default. Job success shape has no `humor_enabled`. `InternalRunState.humor_enabled = False` already landed in T011, so dumping the dataclass greens T019 without a grant prompt profile that de-emphasizes `humorous`. Catalog shall is hybrid (`humorous` off until user enables); this test never looks at `property_ranking` or prose. | Pin one contract-stable boolean (job snapshot field, or an explicit non-redacted flag the contract names). Do not treat “either key, anywhere” as the lock. Do not dump intent slots to satisfy this test. |
| **T3** | **Debate** | Lock fidelity | `test_generate_job.py`; F7; US1 goal; T029; catalog `citation.default_sources_panel` | Hook 2 is covered: `mode=generate`, `parent_artifact_id` null, `producing_mode=generate`, nonempty `body`. US1 / plan P1 also lock **sources panel default** (`citation_mode=panel` when sources exist). T016 never asserts `citation_mode`. An implementer can ship `inline` / omit the field; T016–T019 stay green; T029 is untested. | Add: if `artifact.sources` nonempty → `citation_mode == "panel"` unless the turn sent an override (`citation_mode: null` in the fixture). Skip-ask-if-no-sources stays hybrid/US later. |
| **T4** | Later | SNR / always-green path | `test_web_signal.py`; hook 5; catalog `research.used_or_declared` | `TAVILY` unset → `web_signal == "none_declared"` is the right noop fixture. Hardcoding `none_declared` on every artifact also passes, including web-used and web-disabled. `web_research_enabled` is never read. T054 (`disabled`) is a later slice — this file cannot catch the mix-up until then. | Assert enum membership and that the value is not `disabled` on this fixture. Leave `used` to a future fixture that can fail honestly (empty vs nonempty web bundle), not a live Tavily call. |
| **T5** | Later | Lock fidelity | `test_preview_gate.py`; hook 3; contract 503 | Missing/wrong secret → 401 on `POST /v1/conversations` matches hook 3 and is **already green**. Contract also: unset env → **503**; “protected routes” include mutating/job paths. No 503 case. No 401 on `/messages` or `/jobs` (those routes 404 today, so a messages-401 test would fail for the wrong reason until T028). P1 BFF “browser never sends the secret” is untested (Next, not this suite). | Add unset-secret → 503 on create. Add messages/jobs 401 when those routes exist (T028), not before. BFF custody ≠ this Python file. |
| **T6** | Nit | SNR | `grant_flow.py`; T016 `accepted.get("parent_artifact_id")` | Four files copy the same client fixture. Poll timeout is **8s** vs job timeout **300s** — once T028 + LLM exist, failures become “timeout” rather than lock misses. `accepted.get("parent_artifact_id") is None` passes if the key is **absent**, not only if it is JSON `null`. | One shared client fixture. Assert `"parent_artifact_id" in accepted and accepted["parent_artifact_id"] is None`. Treat 8s as scaffold-red only; raise or inject a deterministic executor when jobs actually run. |
| **T7** | **Strength** | Red-first / SNR | `grant_flow.py`; T015; T016 | Public HTTP only — no LangGraph/Tavily monkeypatch (comment in helper is accurate). Filled Who/Whom/Ask/Why/Evidence prompt so this suite is not the P5 clarify fixture. T016 asserts accepted `mode`, artifact `parent_artifact_id`, `producing_mode`, and nonempty `body` — not status-200-only. T015 asserts 401, not 200. T016–T019 fail for the missing messages route, not a missing import. | Keep the helper’s “no graph stub” rule. Do not “fix” red by stubbing `_execute_job` to the assertion JSON. |
| **T8** | Nit | Red-first honesty | T016–T019 vs T015 | User-facing claim “they are red” is true for T016–T019 only. All four fail at the **same** helper line (`status in {200, 202}`); lock-specific asserts (`claims`, `web_signal`, `humor_enabled`) are unexecuted until job success exists. T015 is not a US1 red gate. | Expected. Do not treat four identical 404s as four independent lock failures. After T028, re-check that each file can fail for its own field. |

Minimum count met. Debates: T1, T2, T3. Strength: T7.

---

### C. Adversarial positions (required)

1. **Position: these tests would go green while a spec lock fails** — strongest case

   Implement `_execute_job` / `POST .../messages` to return `type=job_accepted`, `mode=generate`, `parent_artifact_id` omitted or null, a succeeded job whose artifact is `{producing_mode: generate, body: "ok", claims: [{status: uncertain, source_id: null, excerpt: "x"}], web_signal: none_declared}` and `GET /conversations/{id}` dumps T011’s `humor_enabled=false`. T015 already passes. T016–T019 go green.

   That artifact can skip materials fetch, skip Tavily, skip claim→source binding, use `citation_mode=inline`, enqueue even when slots are empty (P5 — this fixture is filled so it never sees that), and never de-rank `humorous`. SC-003 checkable provenance, F7 panel default, F3 profile, SC-002 ≥2 fit points, P5 clarify-before-write all fail. Tests still pass.

   *What would have to be true for the suite to be right anyway:* this slice only claimed structural hooks 2/4/5 and hybrid JSON fields; audience-fit / prose humor / panel UX stay human; P5 is T039 and T028 is already blocked on T043; F5 forbids LangGraph-as-product-SC so a canned job that *honestly* fills the JSON is an implementer/PR problem, not a pytest problem — **if** T1–T3 edits bind `source_id`/`excerpt`/`citation_mode` and pin humor’s observation surface.

2. **Position: these tests over-constrain implementation / test the wrong layer** — strongest case

   T019 forces a conversation snapshot shape the HTTP contract marks redacted, so implementers will leak `InternalRunState` (or invent `run_state`) to please a bool that is already the dataclass default. T017’s `len(claims) >= 1` is stricter than SC-003’s *when* clause (facts beyond the prompt); a prompt-only restatement with empty `claims[]` could be spec-correct and still fail. T016’s 8s poll plus no test double means CI will need live OpenAI or a stub that *is* the tautology in (1). Four tests share one helper, so they are one integration, not four contracts.

   *What would have to be true for the suite to be right anyway:* GET snapshot is allowed to expose grant-default booleans without slot names; the fixture materials URL is the SC-003 trigger so empty `claims[]` should fail; full HTTP generate is the contract (hooks live on job JSON); 8s is only until T028, then timeout is raised. Humor stays a store bool, not `property_ranking`.

---

### D. Catalog / contract coverage map

| Catalog id or contract hook | Test file / name | Can fail today? | Gap |
|-----------------------------|------------------|-----------------|-----|
| Hook 1 — revise `mode` + `parent_artifact_id` | *(US2 T031)* | n/a this slice | Out of scope |
| Hook 2 — generate `mode=generate`, `parent_artifact_id` null | `test_generate_job.py::test_generate_job_mode_and_complete_body` | **yes** (404 messages) | Missing-key `.get` = null; no `citation_mode` (T3) |
| Hook 3 — protected routes reject wrong secret | `test_preview_gate.py` (both tests) | **yes, but currently green** | No 503 unset; no messages/jobs 401; no BFF custody |
| Hook 4 — grant `claims[]` grounded+`source_id` or uncertain | `test_claim_provenance.py::test_grant_claims_are_grounded_or_uncertain` | **yes** (same 404) | No source resolution; excerpt ⊄ body; all-uncertain stub (T1) |
| Hook 5 — web enabled, no hits → `web_signal=none_declared` | `test_web_signal.py::test_web_enabled_empty_search_declares_none` | **yes** (same 404) | Hardcode `none_declared`; no `disabled` contrast (T4 / T054) |
| Hook 6 — empty Whom/Ask → `type=clarify`, no `job_id` | *(US3 T039)* | n/a this slice | US1 filled-slot fixture cannot catch P5 |
| `claim.provenance` (hybrid, structural) | T017 | yes (404) | Human remainder: real org/funder facts ↔ claims |
| `research.used_or_declared` (hybrid, structural) | T018 | yes (404) | `used` path untested; `disabled` → T054 |
| `grant.default_humor_low` (hybrid, structural) | T019 | yes (404) | Wrong observation layer (T2); prose/`humorous` rank not auto |
| `citation.default_sources_panel` (hybrid) | **none** | **no** | US1/T029 untested (T3) |
| `length.target_1_3_pages` (human) | none | n/a | Correctly not pytest |
| `beachhead.audience_fit_min` (hybrid) | none as auto | n/a | Correctly not faked; ≥2 fit points stay human |
| `research.prefer_criteria_over_trivia` (human) | none | n/a | Correctly not pytest |
| `grant.intent_slots_complete` (hybrid) | *(T039)* | n/a this slice | Filled prompt assumes slots complete |
| Any `how: auto` catalog row | none | n/a | Catalog has **zero** `how: auto` rows; T061 later |
| P1 BFF: browser never sends audit secret | none in this suite | **no** | Next `web/` test, not T015–T019 |

---

### E. Edit list

- `test_claim_provenance.py`: grounded `source_id` must match an `artifact.sources[]` row; `excerpt` must be a nonempty substring of `artifact.body`.
- `test_claim_provenance.py`: keep or drop `len(claims) >= 1` explicitly against SC-003’s *when* (materials-beyond-prompt vs prompt-restatement).
- `test_generate_job.py`: `assert "parent_artifact_id" in accepted and accepted["parent_artifact_id"] is None`; if `sources` nonempty, `citation_mode == "panel"`.
- `test_grant_humor_default.py`: assert one named contract field; delete the either-or `_humor_enabled` crawler.
- `test_web_signal.py`: `web_signal in {"used", "none_declared", "disabled"}` and `== "none_declared"` (not `disabled`) on the Tavily-unset fixture.
- `test_preview_gate.py`: unset `SMART_WRITER_V2_AUDIT_SECRET` → 503 on `POST /v1/conversations`.
- `grant_flow.py`: after T028, raise poll timeout (or document 8s as pre-job-only); do not stub the graph to the assertion payload.
- `test_preview_gate.py` (defer to T028): 401 on `POST .../messages` and `GET /v1/jobs/{id}` without header.

---

### F. Questions for the human (max 3)

1. **T1:** Must US1 tests require grounded `source_id` to resolve in `artifact.sources[]` and `excerpt ⊆ body` before T021, or is claims-shape-only enough for hybrid `claim.provenance`?
2. **T2:** Where may `humor_enabled` be observed without violating GET-conversation redaction — a job-snapshot field, an explicit contract flag, or not at all (leave F3 to prompt/human)?
3. **T3:** Must T016 assert `citation_mode=panel` when sources exist before T021, or is F7 allowed to wait on untested T029 / human panel UX?

Implementer: do not start T021+ until T1–T3 are accepted or the tests are edited. Nit/Later (T4–T6, T8) may be agent-adjudicated (§F).

---

## Adjudication (2026-09-16)

Feature-local lock: human accepted reviewer recs for T1–T3 (this slice). Nit/Later agent-closed.

| ID | Status | Lock |
|----|--------|------|
| **T1** | **locked** | Grounded `source_id` MUST appear in `artifact.sources[].source_id`; `excerpt` MUST be a substring of `body`. Keep `len(claims) >= 1` on the materials-beyond-prompt fixture. ≥2 fit points stay human. |
| **T2** | **locked** | Observe `humor_enabled` on **GET `/v1/jobs/{id}`** success JSON (named field). Do not dump `InternalRunState` / slots on GET conversation. |
| **T3** | **locked** | T016: if `artifact.sources` nonempty and turn sent `citation_mode: null` → `citation_mode == "panel"`. Skip-ask / UI remain later. |
| **T4** | **accepted (Later)** | Enum membership + not `disabled` on Tavily-unset fixture. `used` / T054 later. |
| **T5** | **accepted (Later)** | Unset secret → 503 on create-conversation (done). Messages/jobs 401 deferred to T028. |
| **T6** | **accepted (Nit)** | Shared contract `client` fixture; `parent_artifact_id` key present; 8s poll documented as scaffold-red. |
| **T7** | **strength** | Keep no-graph-stub rule. |
| **T8** | **accepted (Nit)** | Four 404s until T028; then each file must fail on its own field. |

Tests/contract edited to match. **T021+ may start** after this deposit (T028 still blocked on T043).

---

# Independent test review — US3 / T039–T040 (clarify-before-write)

**Reviewer role:** Independent test reviewer (did not write these tests; no loyalty to their wording)  
**Brief:** `docs/agent-os/TEST_REVIEW_PROMPT.md` (constitution §V)  
**Feature:** `specs/smart-writer-v2/`  
**Slice:** T041 — T* of T039–T040 only (US3, P5)  
**Commit:** `2d4115b` — Add red US3 clarify-before-write contract tests.  
**Date:** 2026-09-16  

**Scope files**

| Task | File |
|------|------|
| T039 | `apps/smart-writer-v2/tests/contract/test_clarify_before_write.py` |
| T040 | `apps/smart-writer-v2/tests/contract/test_clarify_no_slot_leak.py` |
| shared | `apps/smart-writer-v2/tests/contract/grant_flow.py` (`EMPTY_WHOM_ASK_PROMPT`, `post_empty_whom_ask_turn`) |

**Out of scope this session:** T016–T019 except as filled-slot contrast. Do not start T042–T043 or T028. Do not rewrite spec/plan. Do not write product code.

**Pytest (app venv, 2026-09-16):** both cases fail at `assert response.status_code == 200` — `POST /v1/conversations/{id}/messages` → `404 {"detail":"Not Found"}`. Honest red (same missing-route reason as US1 T016–T019). Lock-specific asserts (`type`, `job_id`, `missing_hints`, slot-token regex) are unexecuted until T043 exists.

`grant.intent_slots_complete` remains **hybrid** — structural only. No `acceptance.md` `how: auto` rows yet (T061 / plan P2).

US1 contrast: `GRANT_PROMPT` fills Who/Whom/Ask/Why/Evidence and expects `job_accepted` (T016). This slice’s `EMPTY_WHOM_ASK_PROMPT` is the P5 must-clarify fixture. That split is the right fixture design; US1 findings T1–T8 stay locked.

---

### A. Executive verdict

**Approve tests with minor edits**

T039–T040 hit the public messages contract with a distinct empty-Whom/Ask prompt, do not stub the graph, and fail today because the route does not exist. That is honest red. They encode hook 6’s JSON shape (`type=clarify`, no `job_id`) and FR-021’s default-omit of the `missing_hints` **key**.

They would **not** fail closed on P5’s real shall: no generate/revise job and **no ArtifactVersion**. `"job_id" not in payload` is not “nothing was enqueued.” The `(?i)\b(whom|ask|axis)\b` ban fights FR-021 (NL questions about the ask). One Whom/Ask-empty fixture (Why is also empty in the same prompt) lets a Whom+Ask-only gate pass T039 and T016 while FR-003a’s other slots enqueue a draft.

Do not start T042–T043 until Debates **T9–T11** are human-adjudicated (constitution §F). T028 remains blocked on T043.

---

### B. Findings table

| ID | Severity | Lens | Locus | Finding | Suggested resolution |
|----|----------|------|-------|---------|----------------------|
| **T9** | **Debate** | Over-constrain / wrong-thing | `test_clarify_before_write.py` `_SLOT_LABEL_RE`; FR-021; T039 task tokens; T044 | Steelman: T039 asked for no tokens `whom`/`ask`/`Axis` as slot labels; P5 says NL-only, no axis ids. A word-boundary regex is a cheap structural proxy. Attack: `(?i)\b(whom\|ask\|axis)\b` forbids honest English — “What should we **ask** for?” and “To **whom** is this addressed?” fail. (“Asking” does *not* match; the ban is still the wrong layer.) Spec/US3 independent test is “questions never name internal axis IDs,” not “never utter the verb ask.” Implementers will ship stilted copy or weaken the regex to go green. `axis` is the only token that is actually nomenclature. `who`/`why_funder`/`evidence`/`intent_slots` are unbanned, so the list is both too strict and incomplete. | Ban structured labels (`Axis`, `axis_a`, `intent_slots`, `why_funder`, `missing_hints`, `Whom:` as a field tag). Do **not** ban English `ask`/`whom`. Leave “question is specific to the hole” hybrid/human (FR-003a only-missing — do not pytest prose quality). |
| **T10** | **Debate** | Lock fidelity | T039 `assert "job_id" not in payload`; data-model “clarify, no ArtifactVersion”; P5 never-enqueue; catalog `grant.intent_slots_complete` | Steelman: hook 6 is literally `type=clarify`, no `job_id`. The test asserts that shape, nonempty `assistant_message.text`, HTTP 200 — not status-200-only. Attack: P5 / data-model / T043 shall is **never enqueue** and **no ArtifactVersion**. A canned `{type: "clarify", assistant_message: {text: "Need more detail."}}` greens T039–T040 while `_execute_job` runs, a short body is stored as an artifact, or `job_id: null` is the only difference from a write. T040 does not even assert missing `job_id`. GET conversation / artifacts is never called. Hybrid catalog shall is “before **final draft**” — JSON type without observing no draft is the same theater as US1 claims-shape-without-binding (T1, now locked). `"job_id" not in payload` also fails a spec-correct `job_id: null`. | After clarify: `type=clarify` and (`job_id` absent **or** JSON null); GET conversation (or artifacts) shows no latest `ArtifactVersion` / `last_artifact_id` is null. Do not inspect `JobRunner` internals. 409-on-enqueue-anyway stays an error-table path, not this fixture. |
| **T11** | **Debate** | Lock fidelity / gap | `EMPTY_WHOM_ASK_PROMPT`; FR-003a; P5 five slots; contrast T016 `GRANT_PROMPT` | Steelman: hook 6 and T039 name one empty Whom/Ask fixture; P1 exit is one must-clarify fixture; this prompt also omits Why (no funder), so a Why-aware gate still clarifies here. Attack: FR-003a / P5 is **any** of Who/Whom/Ask/Why/Evidence missing. Prompt has Who + Evidence; missing Whom, Ask, **and** Why. A router that only requires “funder named + dollar amount” clarifies this fixture and generates on T016’s filled prompt. A turn with Ford + $50k but empty Why/Evidence **enqueues** and both suites stay green. T042 “infer all five” is untested if tests only encode the example. | Keep the hook-6 Whom/Ask fixture. Add **one** extra POST: Whom+Ask (and Who) filled, Why **or** Evidence empty → still `type=clarify`, no artifact. Do not explode a 5× matrix. Filled-all remains T016, not this file. |
| **T12** | **Strength** | Red-first / SNR | `grant_flow.py`; T039 vs T016 | Public HTTP only; comment still forbids LangGraph/Tavily stubs. Empty prompt is **not** `GRANT_PROMPT` — US1 cannot satisfy P5 by accident, US3 cannot satisfy generate-by-accident. T039 asserts `type=clarify` + no `job_id` + nonempty assistant text. T040 walks nested keys for `missing_hints`, which is the P5 client-payload lock. Failures are 404-not-import. | Keep the empty-vs-filled split and the no-graph-stub rule. Do not “fix” red by returning the assertion JSON from `_execute_job`. |
| **T13** | Later | Red-first honesty / SNR | T039 and T040 vs same helper | Both fail at the **same** `status_code == 200` line. That is one missing route, not two independent lock failures. After T043, T040 can stay green with `type=clarify` **and** a `job_id` if T039 is skipped or weakened. | Expected scaffold-red. After T043, confirm T039 can fail on `type`/`job_id`/artifact and T040 can fail on a planted `missing_hints` key. Add no-`job_id` (or null) to T040 if T10 is locked only on T039. |
| **T14** | Later | Lock fidelity | T040 `_json_keys`; FR-021 | Steelman: contract says do not include `missing_hints` in the default client payload; key-walk matches that sentence. Attack: slot ids can leak as **values** (`{"hints": ["whom", "ask"]}`), camelCase `missingHints`, or `why_funder` in assistant text (T039 regex does not include it). Key-omit alone is not FR-021. | Keep key-omit. If T9 is narrowed, add `why_funder` / `intent_slots` to the **label** ban, not a recursive string search of all JSON (brittle). `missingHints` optional. |
| **T15** | Nit | SNR | T039 `assistant_message`; contract clarify shape | Contract example includes `message_id`. Test requires `text` only. `"job_id" not in payload` vs explicit null (see T10). `payload.get("type")` is fine (missing key fails). | Assert `"message_id" in assistant` if T043 persists messages; treat `job_id` null as OK if T10 locked that way. |

Minimum count met. Debates: T9, T10, T11. Strength: T12.

Correctly **not** pytested (do not fake): FR-003a “only for missing slots” / not a full script (prose); `intake.axis_a_before_b` (plan P2); `chat.free_form_input` form-UX; catalog `how: human` rows.

---

### C. Adversarial positions (required)

1. **Position: these tests would go green while a spec lock fails** — strongest case

   Return `{type: "clarify", assistant_message: {message_id: "m1", text: "Need more detail to draft."}}` with no `missing_hints` and no `\bask\b`/`whom`/`axis`. Optionally enqueue `_execute_job` and/or store an ArtifactVersion. T039–T040 go green. Once T028 exists, a Whom+Ask regex on the filled Ford+$50k prompt still satisfies T016.

   That skips Why/Evidence inference (FR-003a), asks a generic script, leaks `why_funder` in copy, and writes a draft on missing slots (P5). Catalog `grant.intent_slots_complete` fails. Tests still pass.

   *What would have to be true for the suite to be right anyway:* this slice only claimed hook 6 JSON + default-omit `missing_hints`; no-enqueue is T043 code review; one P1 fixture is enough; holes-only copy stays T044/human; T016’s filled prompt is the complete-slots contrast — **if** T10 observes no artifact and T11 adds one Why/Evidence-empty turn.

2. **Position: these tests over-constrain implementation / test the wrong layer** — strongest case

   T039’s token ban makes T044 fail on ordinary questions about the missing Ask (“What should we ask for?”). `"job_id" not in payload` rejects a contract-shaped `job_id: null`. T040’s recursive key walk will fail if a future wrapper nests OpenAPI metadata containing the string `missing_hints` as a documented-but-absent field name. Two files POST the same fixture, so they are one integration. Demanding GET-no-artifact (T10) before GET conversation exists couples this slice to another route.

   *What would have to be true for the suite to be right anyway:* T044 is specified to avoid those English words; clarify JSON must omit `job_id` entirely (not null); `missing_hints` is a forbidden key forever; duplicate POSTs are acceptable isolation; GET snapshot is already in the contract so asserting no latest artifact is in-layer.

---

### D. Catalog / contract coverage map

| Catalog id or contract hook | Test file / name | Can fail today? | Gap |
|-----------------------------|------------------|-----------------|-----|
| Hook 6 — empty Whom/Ask → `type=clarify`, no `job_id` | `test_clarify_before_write.py::test_empty_whom_ask_is_clarify_without_job` | **yes** (404 messages) | Payload-only; no ArtifactVersion observation (T10); `job_id` null rejected |
| FR-021 / P5 — default omit `missing_hints` | `test_clarify_no_slot_leak.py::test_clarify_payload_omits_missing_hints` | **yes** (same 404) | Key name only; values / camelCase (T14); no `job_id` assert |
| FR-021 — NL, no axis/slot nomenclature | T039 `_SLOT_LABEL_RE` | **yes** (unexecuted until 200) | Over-bans English `ask`/`whom`; under-bans `why_funder` (T9) |
| P5 / data-model — grant + missing slots ⇒ no job, no ArtifactVersion | **none as observation** | **no** | T10 |
| FR-003a — **any** of five slots missing | Whom/Ask(/Why) empty fixture only | partial | No Why-or-Evidence-only-empty contrast (T11) |
| FR-003a — ask **only** for missing slots | none | n/a | Correctly not pytest (hybrid/human) |
| `grant.intent_slots_complete` (hybrid, structural) | T039 `type=clarify` | yes (404) | Structural half incomplete without no-draft observation |
| `intake.axis_a_before_b` (hybrid) | none | n/a | Plan P2; not this slice |
| `chat.free_form_input` (hybrid) | request is free-form text | n/a | Correctly not faking “no forms” UX |
| Hook 2 — filled slots → generate | T016 (contrast, not re-reviewed) | yes (404) | Empty fixture must not be used there — currently isn’t |
| 409 enqueue-while-incomplete | none | n/a | Error table; auto path should be clarify 200, not 409 |
| `client_intent=regenerate` + empty slots | none | n/a | US2 T032; P5 still implies no write — Later |
| Any `how: auto` catalog row | none | n/a | Still zero `how: auto` rows; T061 later |

---

### E. Edit list

- `test_clarify_before_write.py`: replace `(whom|ask|axis)` with structured-label patterns (`Axis`, `intent_slots`, `why_funder`, `missing_hints`); do not forbid English `ask`/`whom`.
- `test_clarify_before_write.py`: treat missing `job_id` **or** JSON `null` as “no job”; keep `type == "clarify"` and nonempty `assistant_message.text`.
- `test_clarify_before_write.py` (if T10 locked): after 200 clarify, GET `/v1/conversations/{id}` (or artifacts) and assert no latest ArtifactVersion / `last_artifact_id` is null — public contract only.
- `grant_flow.py` + T039 or a sibling test (if T11 locked): one POST with Whom+Ask filled and Why or Evidence empty → still clarify, no artifact.
- `test_clarify_no_slot_leak.py`: keep nested `missing_hints` key ban; add no-`job_id`-or-null if T040 should fail closed on its own after T043.
- Do **not** stub `_execute_job` / LangGraph to the clarify JSON.
- After T043: re-check T039 fails on `type`/artifact and T040 fails on a planted `missing_hints` (not another 404).
- Defer: 409 path; regenerate+empty slots; A-before-B; holes-only prose quality.

---

### F. Questions for the human (max 3)

1. **T9:** Must T039 keep banning English tokens `ask`/`whom`, or is the lock only structured labels (`Axis`, `intent_slots`, `why_funder`, `missing_hints`)?
2. **T10:** Before T042, must clarify tests observe **no ArtifactVersion** (GET snapshot), or is hook-6 payload shape (`type=clarify`, no `job_id`) enough for hybrid `grant.intent_slots_complete`?
3. **T11:** Must this slice add a Why-or-Evidence-empty fixture (Whom+Ask filled) so T043 cannot gate on funder+amount only, or is hook 6’s single Whom/Ask fixture the P1 bar?

Implementer: do not start T042–T043 until T9–T11 are accepted or the tests are edited. Nit/Later (T13–T15) may be agent-adjudicated (§F). T028 stays blocked on T043.

---

## Adjudication — US3 (2026-09-16)

Feature-local lock: human accepted reviewer recs for T9–T11 (this slice). Nit/Later agent-closed.

| ID | Status | Lock |
|----|--------|------|
| **T9** | **locked** | Ban structured labels (`Axis`, `axis_a`/`axis_b`, `intent_slots`, `why_funder`, `missing_hints`, `Whom:`). Do **not** ban English `ask`/`whom`. Holes-only prose quality stays hybrid/human. |
| **T10** | **locked** | `type=clarify` and `job_id` absent **or** JSON `null`. `GET /v1/conversations/{id}`: `last_artifact_id` key present and JSON `null`; no latest artifact object. Do not inspect `JobRunner`. |
| **T11** | **locked** | Keep empty Whom/Ask fixture. Add one POST: Who+Whom+Ask filled, Why or Evidence empty → still clarify, no artifact. Not a 5× matrix. Filled-all remains T016. |
| **T12** | **strength** | Keep empty-vs-filled split and no-graph-stub rule. |
| **T13** | **accepted (Later)** | Same 404 until T043; then each file must fail on its own field (`type`/artifact vs planted `missing_hints`). |
| **T14** | **accepted (Later)** | Keep `missing_hints` key-omit. Structured-label ban on T9 covers `why_funder` / `intent_slots` in assistant text. No recursive string search of all JSON. |
| **T15** | **accepted (Nit)** | Require `message_id` on `assistant_message`; `job_id` null is OK (T10). |

Tests/contract edited to match. **T042–T043 may start** after this deposit (T028 still blocked on T043).

---

# Independent test review — US2 / T031–T033 (revise / regenerate)

**Reviewer role:** Independent test reviewer (did not write these tests; no loyalty to their wording)  
**Brief:** `docs/agent-os/TEST_REVIEW_PROMPT.md` (constitution §V)  
**Feature:** `specs/smart-writer-v2/`  
**Slice:** T034 — T* of T031–T033 only (US2, F8 / SC-006 / SC-007)  
**Commit:** `198d493` — Ship grant chat UI and red US2 revise contract tests.  
**Date:** 2026-09-16  

**Scope files**

| Task | File |
|------|------|
| T031 | `apps/smart-writer-v2/tests/contract/test_revise_job.py` |
| T032 | `apps/smart-writer-v2/tests/contract/test_regenerate_job.py` |
| T033 | `apps/smart-writer-v2/tests/contract/test_revise_without_parent.py` |
| shared | `apps/smart-writer-v2/tests/contract/grant_flow.py` (`post_followup_turn`) |

**Out of scope this session:** T016–T019, T039–T040 except as filled-slot / generate contrast. Do not start T035. Do not rewrite spec/plan. Do not write product code. US1 findings T1–T8 and US3 findings T9–T15 stay locked.

**Pytest (app venv, 2026-09-16, at/after `198d493`):** T028 is already in. First generate succeeds (canned, ~0.6s).

| Test | Result | Fail locus |
|------|--------|------------|
| `test_feedback_after_generate_is_revise_with_parent` | **FAIL** | `accepted["mode"] == "revise"` — got `"generate"` |
| `test_regenerate_is_generate_with_null_parent` | **PASS** | — |
| `test_revise_without_parent_returns_409` | **FAIL** | `status_code == 409` — got `200` `job_accepted` `mode=generate` |

T031 fails for the lock it claims (follow-up auto is still generate). T032 does **not** fail. T033 fails because a first filled-slot turn generates — which is the spec edge, not a missing 409 router. `MessageTurnIn` has no `parent_artifact_id`; Pydantic drops `extra={"parent_artifact_id": "does-not-exist"}`.

`revise.continuity_default` and `regenerate.explicit` remain **hybrid**. No `acceptance.md` `how: auto` rows yet (T061 / plan P2).

---

### A. Executive verdict

**Approve tests with minor edits**

T031 hits the public messages contract after a real generate, asserts hook 1 (`mode=revise`, `parent_artifact_id` equal to the first artifact, `producing_mode=revise`), and is red today because T028 still hard-codes generate. That is honest red, not a 404.

T032 is the same helper with `client_intent=regenerate` and is **already green**: everything is generate, so “regenerate is generate, parent null” cannot fail closed on SC-007 until auto-revise exists. T033 injects a non-contract request field on a **new** conversation; 200 generate is what FR/edge “no prior artifact → generate” requires. Greening T033 by adding `parent_artifact_id` to `MessageTurnIn` would violate `http-api.md`.

Do not start T035 until Debates **T16–T18** are human-adjudicated (constitution §F). Do not “fix” T033 by extending the POST body. Do not stub `revise_graph` to the assertion JSON.

---

### B. Findings table

| ID | Severity | Lens | Locus | Finding | Suggested resolution |
|----|----------|------|-------|---------|----------------------|
| **T16** | **Debate** | Red-first honesty | `test_regenerate_job.py`; hook 2; catalog `regenerate.explicit`; FR-020; T036 | Steelman: regenerate after a generate **is** mode=generate / parent JSON null; T032 asserts both accepted and artifact, keys present (T6 lock). Attack: T028 already returns that shape for every filled-slot turn. T032 **passed** at review. SC-007 is distinguishable-from-**revise**, not “still generate.” T036 “`regenerate` forces generate” is untested until auto-followups become revise: an implementer can ship T035+T037, skip the regenerate exception, and T032 stays green. NL `"Start over…"` plus the flag also fails to isolate `client_intent` (the contract lock) from parsing. | Keep T032 as the **contrast landmine** for T036, not as an independently red gate. After auto→revise exists, T032 must fail if regenerate is routed like auto. Do not pytest NL “start over” as a second router. Assert `artifact_id` ≠ first generate id (new chain head). |
| **T17** | **Debate** | Wrong-thing / lock fidelity | `test_revise_without_parent.py`; http-api 409 row; spec edge “no prior → generate”; data-model `mode=revise` ⇒ parent exists | Steelman: T033 asked for 409 on revise without parent; error table names that case; test asserts not `job_accepted` and no `job_id`. Attack: POST body in the contract is `text` / `client_intent` / `citation_mode` / `materials` only. Fixture is a **first** `GRANT_PROMPT` turn with a ghost `parent_artifact_id`. Extra is ignored; server correctly generates (200). Spec edge is generate, **not** 409. There is no public way to select `mode=revise` with a missing parent (`client_intent` is `auto\|regenerate`). 409 is an internal enqueue invariant (stale `last_artifact_id`, or a bug). This test cannot go green without polluting `MessageTurnIn` or mutating the store. | Do **not** add `parent_artifact_id` to the client schema. Drop or rewrite: either (a) unit-test the enqueue helper when `mode=revise` and parent missing/unknown → 409, not this HTTP file; or (b) HTTP: no `last_artifact_id` + `client_intent=auto` + filled slots → **generate**, not 409 (would be green today — not a US2 red gate). Keep 409 in the error table for the race/stale-parent path. |
| **T18** | **Debate** | Lock fidelity | `test_revise_job.py`; FR-019; SC-006; catalog `revise.continuity_default`; P3/T035 | Steelman: hook 1 is `mode=revise` + non-null parent; T031 binds parent to the **first** `artifact_id` (stronger than “non-null”) and checks job `producing_mode`. Attack: `assemble_artifact(..., producing_mode="revise", parent_artifact_id=parent)` already exists on the generate graph. Stamp a full re-generate, ignore feedback, skip a revise graph: T031 greens. Catalog shall is “linked to prior **+ feedback**; **not silent full regen**.” Test never GETs `last_artifact_id`, never requires `artifact_id` ≠ parent, never requires nonempty `body` (T016 does). Hybrid remainder (prose improved) must not be faked; “new ArtifactVersion is head of chain” is structural and untested. | Public contract only: new `artifact_id` ≠ `parent_id`; GET `/v1/conversations/{id}` `last_artifact_id` equals the new id. Keep nonempty `body`. Do **not** pytest body≠parent-body or feedback n-grams (human/hybrid). Do not inspect `JobRunner` / graph state for “prior in context.” |
| **T19** | **Strength** | Red-first / SNR | T031 vs T032; `grant_flow.py` | Same public HTTP helper; no LangGraph/Tavily stub. Filled `GRANT_PROMPT` then a **different** follow-up text. T031 fails on `mode`, not missing import / 404. T032 uses `client_intent=regenerate` and requires `parent_artifact_id` **in** the JSON as null. That split is the right US2 fixture design once revise exists. | Keep no-graph-stub. Do not make T032 red by stubbing generate to fail. Do not merge T031/T032 into one test that hides the regenerate miss. |
| **T20** | Later | Red-first honesty / SNR | T031 vs T032 vs T033 | Three files are not three independent reds. T031 is the only lock-specific fail. T032 is green. T033 is 200-on-first-generate. After T036, re-check: T031 fails on `mode`/parent if auto stays generate; T032 fails on `mode`/parent if regenerate is treated as auto-revise. | Expected until T036. Treat T032 PASS in this T* as a finding (T16), not as US2 DoD. |
| **T21** | Later | Lock fidelity / scope | T032; hook 2 panel clause; P5 + regenerate | Hook 2 also: nonempty `sources` + no citation override → `citation_mode=panel` (T3, locked on T016). T032 omits it; a regenerate path could drop panel. `client_intent=regenerate` with **empty** slots is still a write in this slice (slots already filled from generate). P5 “never enqueue if incomplete” on a cold regenerate remains untested. | Leave panel on T016 unless regenerate grows its own assemble. Empty-slot regenerate → T039/P5, not this file. |
| **T22** | Nit | SNR | T031 vs T016 `body`; T031 `accepted.get("type")` | US2 scenario 1 / FR-018: writing artifacts are complete. T016 asserts nonempty `body`; T031 does not — a `body: ""` revise would pass. `accepted.get("type")` fails closed if the key is missing (`None != "job_accepted"`). | Copy T016’s nonempty `body` assert onto the revise artifact. Type check is fine. |

Minimum count met. Debates: T16, T17, T18. Strength: T19.

Correctly **not** pytested (do not fake): “draft improved” / feedback woven into prose (hybrid/human); T038 regenerate control + version indicator (Next); `chat.free_form_input` form-UX; catalog `how: human` rows; LangGraph-as-product-SC (F5).

---

### C. Adversarial positions (required)

1. **Position: these tests would go green while a spec lock fails** — strongest case

   Keep T028 enqueue-always-generate. Implement T035 as `assemble_artifact(producing_mode="revise", parent_artifact_id=last)` on the **generate** graph with only the new user text. T031 goes green. T032 is already green. Leave T033 red, or 409 iff the client sent `parent_artifact_id` (schema creep).

   FR-019 / F8 “prior output + feedback in context, not silent full re-initialize” fails. SC-006 “new ArtifactVersion linked to previous **and that feedback**” fails if `last_artifact_id` is not moved and the body is a cold regen. SC-007 is unused. Catalog `revise.continuity_default` fails. Tests that matter for T035 pass.

   *What would have to be true for the suite to be right anyway:* this slice only claimed hook 1 JSON + hook 2 regenerate shape; “not silent regen” stays human; T032 is a landmine for T036 not a current red; 409 is a later race — **if** T18 observes new id + `last_artifact_id` and T17 is not greened via `MessageTurnIn`.

2. **Position: these tests over-constrain implementation / test the wrong layer** — strongest case

   T033 forces a request field the contract omits; `extra=forbid` would 422 a spec-correct first generate. Demanding GET `last_artifact_id` (T18) couples US2 tests to snapshot shape already used by T010/T10 — fine — but requiring a distinct HTTP 409 for “no parent” fights the spec edge that that turn is generate. Making T032 fail today requires a fake revise path or a broken generate. Body-diff vs parent body is an LLM flake. Three POSTs through one helper are one integration.

   *What would have to be true for the suite to be right anyway:* 409 is a public contract row that must be hit from HTTP; `parent_artifact_id` on POST is an allowed extension; T032 must be red before T035 (deadlock); snapshot head-of-chain is in-layer (GET conversation already contracted).

---

### D. Catalog / contract coverage map

| Catalog id or contract hook | Test file / name | Can fail today? | Gap |
|-----------------------------|------------------|-----------------|-----|
| Hook 1 — revise `mode` + `artifact.parent_artifact_id` non-null | `test_revise_job.py::test_feedback_after_generate_is_revise_with_parent` | **yes** (`mode=generate`) | Parent bound to first id (good). No new-id / `last_artifact_id` / nonempty body (T18, T22) |
| Hook 2 — generate/regenerate `mode=generate`, parent JSON null | `test_regenerate_job.py::test_regenerate_is_generate_with_null_parent` | **no** (PASS; vacuous) | Not distinct-from-revise until T036 (T16). No panel clause (T21). T016 still owns fresh generate |
| 409 — revise without parent | `test_revise_without_parent.py::test_revise_without_parent_returns_409` | **yes, wrong reason** (200 generate) | Extra field not in contract; first-turn generate is spec-correct (T17) |
| Spec edge — no prior artifact → generate | **inverted by T033** | n/a | Would pass today as generate; not a red US2 test |
| `revise.continuity_default` (hybrid, structural) | T031 parent link | yes (`mode`) | “+ feedback / not silent full regen” untested (T18) |
| `regenerate.explicit` (hybrid, structural) | T032 | **no** | Green by T028 default (T16) |
| FR-019 prior output + feedback in context | none as observation | **no** | Hybrid/human prose; structural half = T18 |
| FR-018 complete body on revise | none on T031 | **no** | T016 only (T22) |
| FR-020 / T036 regenerate forces generate | T032 | not until revise exists | Flag vs NL not isolated (T16) |
| `chat.free_form_input` (hybrid) | free-form follow-up text | n/a | Correctly not faking forms |
| T038 UI regenerate control / version indicator | none | n/a | Next/`web/`; not this suite |
| P5 regenerate + empty slots | none | n/a | Later (T21); filled generate first |
| Any `how: auto` catalog row | none | n/a | Still zero; T061 later (may mark `revise.continuity_default`) |
| Hook 2 panel when sources nonempty | T016 (not T032) | yes (US1) | Regenerated artifact untested (T21) |

---

### E. Edit list

- `test_revise_job.py`: after success, `artifact["artifact_id"] != parent_id`; GET conversation `last_artifact_id` equals the new id (key present).
- `test_revise_job.py`: nonempty `artifact.body` (copy T016).
- `test_regenerate_job.py`: `artifact["artifact_id"] !=` first generate id; document that this file is expected-green until auto-revise exists, then must fail if regenerate routes to revise.
- `test_revise_without_parent.py`: **do not** send `parent_artifact_id` on POST. Either delete the HTTP test or move 409 to a helper unit test (`mode=revise` + missing/unknown parent). Do not change `MessageTurnIn`.
- Do **not** stub `revise_graph` / `_execute_job` to `{mode: revise, parent_artifact_id: ...}`.
- After T036: confirm T031 fails on `mode`/parent if auto stays generate; T032 fails on `mode`/parent if regenerate revises.
- Defer: `citation_mode=panel` on regenerate (T016); empty-slot regenerate (P5); UI T038.
- Poll 8s remains scaffold-ok while jobs are canned; raise when revise actually calls the LLM.

---

### F. Questions for the human (max 3)

1. **T16:** May T032 stay green until T036 (contrast landmine), or must regenerate be independently red before T035 — knowing that requires a fake revise path?
2. **T17:** Drop/move the HTTP 409 test (no `parent_artifact_id` on POST), or extend the contract so clients can name a parent? Spec edge is no-parent → generate.
3. **T18:** Before T035, must T031 observe new `artifact_id` + GET `last_artifact_id`, or is hook-1 `mode`+parent-id enough for hybrid `revise.continuity_default`?

Implementer: do not start T035 until T16–T18 are accepted or the tests are edited. Nit/Later (T20–T22) may be agent-adjudicated (§F). Do not implement 409 by adding `parent_artifact_id` to the messages request body.

---

## Adjudication — US2 (2026-09-16)

Feature-local lock: human accepted reviewer recs for T16–T18 (this slice). Nit/Later agent-closed.

| ID | Status | Lock |
|----|--------|------|
| **T16** | **locked** | T032 is a T036 landmine: allowed green until auto→revise exists; then must fail if regenerate routes like auto. New `artifact_id` ≠ first generate. Do not pytest NL “start over.” |
| **T17** | **locked** | Do **not** add `parent_artifact_id` to `MessageTurnIn`. Drop HTTP 409-on-first-turn test. 409 = enqueue helper when `mode=revise` and parent missing/unknown (unit). Spec edge: no prior → generate. |
| **T18** | **locked** | T031: new `artifact_id` ≠ parent; GET conversation `last_artifact_id` equals the new id; nonempty `body`. Do not pytest prose diffs. |
| **T19** | **strength** | Keep T031 vs T032 public-HTTP split and no-graph-stub. |
| **T20** | **accepted (Later)** | After T036, re-check T032 fails if regenerate revises. |
| **T21** | **accepted (Later)** | Panel on regenerate stays T016; empty-slot regenerate stays P5. |
| **T22** | **accepted (Nit)** | Nonempty revise `body` included in T18. |

Tests edited to match. **T035–T038 may start.**

---

# Independent test review — US4 / T046–T047 (closed ranking / factual ≠ grounding off)

**Reviewer role:** Independent test reviewer (did not write these tests; no loyalty to their wording)  
**Brief:** `docs/agent-os/TEST_REVIEW_PROMPT.md` (constitution §V)  
**Feature:** `specs/smart-writer-v2/`  
**Slice:** T048 — T* of T046–T047 only (US4, FR-004/005, F3 / FR-006a)  
**Commit:** `104ae27` — Add red US4 tests for closed ranking and factual-not-grounding-off.  
**Date:** 2026-09-16  

**Scope files**

| Task | File |
|------|------|
| T046 | `apps/smart-writer-v2/tests/contract/test_property_ranking_closed.py` |
| T047 | `apps/smart-writer-v2/tests/contract/test_factual_not_grounding_off.py` |
| seam | `apps/smart-writer-v2/app/agents/infer_state.py` (`infer_property_ranking` returns `[]` until T049) |

**Out of scope this session:** T016–T045 except as contrast. Do not start T049. Do not rewrite spec/plan. Do not write product code. Prior T1–T22 stay locked (especially **T2**: ranking is internal; do not dump `InternalRunState` on GET conversation). T050–T051 chips / weave-into-prose stay hybrid/human.

**Pytest (app venv, at `104ae27`):**

| Test | Result | Fail locus |
|------|--------|------------|
| `test_inferred_ranking_only_closed_ids` | **FAIL** | `assert ranking` — got `[]` (stub, not ImportError) |
| `test_factual_low_still_runs_materials_and_web` | **PASS** | canned `_run_generate_without_llm` already grounds |

No `acceptance.md` `how: auto` rows yet (T061 / plan P2). Catalog rows in play are hybrid: `claim.provenance` / `research.used_or_declared` (F3 notes), `grant.default_humor_low`, `intake.property_chips_preferred` (human).

---

### A. Executive verdict

**Approve tests with minor edits**

T046 is honest red: it imports the T049 seam and fails because the stub returns `[]`, not because the name is missing. It encodes FR-004’s closed-id clamp and R8’s dropped labels (`emotional`, `visionary`) without dumping ranking on GET conversation (T2). T047 observes F3 on the public job snapshot (`web_signal`, materials bundle, `claims[]`) and does not fake chips or weave.

They would **not** fail closed on FR-005. `return list(SEED_PROPERTIES)` or `filter_closed_ranking(text.split())` greens T046 while ignoring free-form ranking. T047 is already green (T032-class landmine) and never asserts that `factual` was ranked last — the F3 *when* is untested. Generate’s LLM infer node (`infer.py` + `filter_closed_ranking`) is a different function than T046’s stub; the canned HTTP path never calls `infer_property_ranking`. T049 can satisfy pytest as dead code.

Do not start T049 until Debates **T23–T25** are human-adjudicated (constitution §F). Do not green T046 by putting `property_ranking` on GET conversation.

---

### B. Findings table

| ID | Severity | Lens | Locus | Finding | Suggested resolution |
|----|----------|------|-------|---------|----------------------|
| **T23** | **Debate** | Wrong-thing / lock fidelity | `test_property_ranking_closed.py`; FR-004; FR-005; `filter_closed_ranking` | Steelman: nonempty list, membership in `SEED_PROPERTIES`, uniqueness, and invented ids absent is the closed-vocab clamp (FR-004 / R8). Empty-list fail is the right red. Attack: the fixture names closed ids (`warm`, `persuasive`, `urgent`) plus invented (`emotional`, `visionary`). None of the named closed ids are required. `return ["factual"]`, `return list(SEED_PROPERTIES)`, or `filter_closed_ranking(_RANKING_PROMPT.lower().split())` all go green. That is a token/allowlist filter, not inference of a ranking from free-form (FR-005). Existing `tests/unit/test_properties.py` already covers `filter_closed_ranking`. | Require the fixture’s named closed ids to appear (`warm`, `persuasive`, `urgent` ⊆ ranking). Keep invented-absent. Do **not** require exact permutation (LLM/synonym flake). Optional second fixture: invented-only prose → no `emotional`/`visionary`. |
| **T24** | **Debate** | Red-first honesty / SNR | `test_factual_not_grounding_off.py`; F3; FR-006a; catalog `claim.provenance` / `research.used_or_declared` | Steelman: F3 is “factual low ⇏ retrieval off.” Public `web_signal != disabled` + materials bundle + `claims[]` is the right observation layer (not graph internals). Comment admits T032-style landmine. Attack: test **PASSED** at review. Canned generate already grounds with default `web_research_enabled=True` and never reads ranking. Prompt says “Rank factual last” but ranking is never observed. T049 can skip inference, skip store, skip any factual→retrieval coupling: T047 stays green. Duplicate of T017 (`claims>=1`) + T018 (`!= disabled`) with extra ignored prose. Landmine only fires if someone later writes the bug; it is not an independently red gate for T049. | Keep T047 as a **T049 landmine** (like T16/T032) **only if** a unit/seam test observes factual-last (or factual present and not first) on `_FACTUAL_LOW_PROMPT` without GET-dumping state. After T049, T047 must fail if `web_signal == "disabled"` on this fixture. Do not pytest tone/prose. |
| **T25** | **Debate** | Wrong-thing / T2 | T046 seam vs `app/agents/infer.py`; T049 store; GET conversation (T2) | Steelman: tasks.md names `infer_property_ranking` in `infer_state.py`; testing that function avoids T2. Attack: LLM generate already infers `property_ranking` via `infer_grant_state` + `filter_closed_ranking`. Canned `_run_generate_without_llm` has no ranking parameter. HTTP enqueue passes store `web_research_enabled` / `humor_enabled` and never calls `infer_property_ranking`. T049’s “store on `InternalRunState`” is untested. Filling the stub greens T046 while the live graph/store ignore it. Observing ranking on GET conversation would **violate T2**. Job snapshot has no ranking field (and should not grow one just for this test). | Keep T046 on the function (T2). T049 DoD must **call** that function from the deterministic infer path used by HTTP (same pattern as `extract_intent_slots`) and write `InternalRunState.property_ranking` — code review / a store unit that does not go through GET conversation. Do not add `property_ranking` to `ConversationSnapshotOut`. `infer.py` should clamp via the same closed helper, not a second untested list. |
| **T26** | **Strength** | Red-first / scope | T046 vs T047; T2; T050–T051 | T046 fails on `[]`, not ImportError. Invented labels are the R8 drop, not a random string. T047 uses public HTTP + job JSON; no LangGraph/Tavily stub. Chips UX and weave-into-prose are correctly not pytested. GRANT_PROMPT itself contains no seed-property tokens, so the T046 suffix is the only closed-id bait (good fixture split vs T016). | Keep empty-list stub until T049. Keep no GET ranking. Do not stub `_execute_job` to ranking JSON. |
| **T27** | Later | SNR | T047 vs T017/T018 | T047’s `claims>=1`, materials `bundle`, and `web_signal != disabled` are US1 structural asserts. They do not become F3-specific until ranking is factual-low. `signal in {used, none_declared, disabled}` then `!= disabled` is weaker than T018’s `== none_declared` on the Tavily-unset path (allows `used` with empty web). | After T24: keep materials/web observation; drop redundant claims-shape if T017 still owns it; on this fixture `!= disabled` is the F3 lock, not `== none_declared`. |
| **T28** | Nit | SNR | T046 path `tests/contract/` | File is a unit test of an internal function living under contract/. US1–US3 contract files hit HTTP. Not a lock miss. | Leave it, or move next to `tests/unit/test_infer_state.py`. Do not “fix” by POSTing ranking onto GET conversation. |

Minimum count met. Debates: T23, T24, T25. Strength: T26.

Correctly **not** pytested (do not fake): T050 weave-into-prompt-program (hybrid/human); T051 chips UX (`intake.property_chips_preferred` is `how: human`); “prose is warmer”; FR-006b humor profile (T019 / T2); LangGraph-as-product-SC (F5).

---

### C. Adversarial positions (required)

1. **Position: these tests would go green while a spec lock fails** — strongest case

   Implement `infer_property_ranking` as `return list(SEED_PROPERTIES)` or `filter_closed_ranking(text.split())`. Do not store ranking. Do not call the function from HTTP or `run_generate`. T046 goes green. T047 already passes. `infer.py` can still emit an unclamped LLM list on the OpenAI path; canned path never ranks.

   FR-005 (infer ranking from free-form) fails. F3’s *when* (factual ranked low) never happens, so FR-006a is unexercised. US4 independent test “free-form prompt updates internal ranking” fails. Pytest is green.

   *What would have to be true for the suite to be right anyway:* T046 is only the FR-004 clamp; FR-005/weave stay T050/human; T047 is a regression landmine not a T049 red gate — **if** T23 requires named closed ids from the fixture and T25 requires the HTTP infer path to call that function without GET-dumping state.

2. **Position: these tests over-constrain implementation / test the wrong layer** — strongest case

   T046 pins a helper the P3 infer node does not use (`infer_grant_state` already returns `property_ranking`). Requiring `{warm, persuasive, urgent}` ⊆ ranking forbids synonym-only inference (“keep it kind and pressing” with no seed tokens). A second factual-last unit test (T24) plus T047 HTTP is two layers for one F3 sentence. Demanding store observation without a public field pushes ranking onto GET conversation and fights T2. Exact order asserts would flake.

   *What would have to be true for the suite to be right anyway:* tasks.md’s `infer_property_ranking` is the deterministic HTTP seam (like `extract_intent_slots`); named-id ⊆ ranking is the structural half of FR-005; T2 stays “no ranking on GET conversation”; T047 remains a landmine, not a second red gate.

---

### D. Catalog / contract coverage map

| Catalog id or contract hook | Test file / name | Can fail today? | Gap |
|-----------------------------|------------------|-----------------|-----|
| FR-004 closed vocabulary ids | `test_property_ranking_closed.py::test_inferred_ranking_only_closed_ids` | **yes** (`[]`) | Invented-absent only if implementer emits them; constant seed list passes (T23) |
| FR-005 infer ranking from free-form | T046 nonempty closed list | **yes, weak** | Named closed ids from fixture unrequired; order untested (correctly not exact perm) |
| F3 / FR-006a factual = tone only | `test_factual_not_grounding_off.py::test_factual_low_still_runs_materials_and_web` | **no** (PASS) | WHEN factual-last unobserved (T24). Landmine only |
| Hook 4 / `claim.provenance` (hybrid) | T047 `len(claims)>=1` | no (PASS) | Duplicate T017; not F3-specific (T27) |
| Hook 5 / `research.used_or_declared` | T047 `web_signal != disabled` | no (PASS) | Weaker than T018 `== none_declared` (T27) |
| T049 persist `InternalRunState.property_ranking` | **none** | **no** | Must not use GET conversation (T2 / T25) |
| P3 infer node `infer_grant_state` | **none** (T046 hits a different function) | n/a | Dual seam (T25) |
| `intake.property_chips_preferred` (human) | none | n/a | Correctly not pytest (T051) |
| FR-006 weave into prompt program | none | n/a | Correctly not pytest (T050) |
| `grant.default_humor_low` | T019 (not this slice) | n/a | T2 still: job snapshot only |
| Hook 2 generate job | T047 enqueue | no (already generate) | Not a US4 lock |
| Any `how: auto` catalog row | none | n/a | Still zero; T061 later |

---

### E. Edit list

- `test_property_ranking_closed.py`: assert `{"warm", "persuasive", "urgent"} <= set(ranking)` in addition to closed-only / unique / invented-absent.
- `test_property_ranking_closed.py` (if T24 locked here): `_FACTUAL_LOW_PROMPT` → `factual in ranking` and ranking[0] != `"factual"` (or last); still no GET dump.
- `test_property_ranking_closed.py` (optional): invented-only suffix without closed tokens → ranking has no `emotional`/`visionary`.
- `test_factual_not_grounding_off.py`: keep as T049 landmine; document that after ranking exists this file must fail on `web_signal == "disabled"`.
- Do **not** add `property_ranking` / `run_state` to GET `/v1/conversations/{id}` (T2).
- Do **not** pytest chips (T051) or weave/prose (T050).
- Do **not** stub `_execute_job` / LangGraph to a ranking payload.
- After T049: re-check T046 fails on invented ids / missing named closed ids; T047 fails if factual-low disables web.

---

### F. Questions for the human (max 3)

1. **T23:** Must T046 require the fixture’s named closed ids (`warm`, `persuasive`, `urgent`) to appear, or is nonempty closed-only (invented-absent) enough for FR-004 before T049?
2. **T24:** May T047 stay green as a T049 landmine (T16/T032), or must a seam test observe factual-last ranking before T049 — knowing T047 cannot fail closed on F3 today?
3. **T25:** Is `infer_property_ranking` the HTTP/store infer seam T049 must wire (without GET-dumping ranking), or is greening the function enough while `infer.py` / canned generate stay separate?

Implementer: do not start T049 until T23–T25 are accepted or the tests are edited. Nit/Later (T27–T28) may be agent-adjudicated (§F). Do not implement ranking visibility by extending GET conversation. T050–T051 remain out of this T* gate.

---

## Adjudication — US4 (2026-09-16)

Feature-local lock: human accepted architect recs for T23–T25 (this slice). Nit/Later agent-closed.

| ID | Status | Lock |
|----|--------|------|
| **T23** | **locked** | T046 requires `{warm, persuasive, urgent} ⊆ ranking`. Keep invented-absent (`emotional`, `visionary`). Do not require exact order. |
| **T24** | **locked** | T047 stays a T049 landmine (allowed green). Seam test on `FACTUAL_LOW_PROMPT`: `factual` in ranking and not first. After T049, T047 must fail if `web_signal == "disabled"`. Do not pytest tone. |
| **T25** | **locked** | `infer_property_ranking` is the HTTP/store seam (like `extract_intent_slots`). T049 must call it and write `InternalRunState.property_ranking`. Do **not** add ranking to GET conversation (T2). Greening the stub as dead code is not DoD. |
| **T26** | **strength** | Keep empty-list-until-T049; keep no GET ranking; no `_execute_job` stub. |
| **T27** | **accepted (Later)** | T047 F3 lock is `web_signal != disabled`; `== none_declared` stays T018. |
| **T28** | **accepted (Nit)** | Leave T046 under `tests/contract/`. Do not move it onto GET conversation. |

Tests edited to match. **T049–T052 may start.**

---

# Independent test review — US5 / T053–T054 (bundle roles / web disabled)

**Reviewer role:** Independent test reviewer (did not write these tests; no loyalty to their wording)  
**Brief:** `docs/agent-os/TEST_REVIEW_PROMPT.md` (constitution §V)  
**Feature:** `specs/smart-writer-v2/`  
**Slice:** T055 — T* of T053–T054 only (US5, F4 / FR-007a/b, SC-004)  
**Commit:** `f25f2d9` — tests under review (packet `427cbfb` / `a07b542`)  
**Date:** 2026-09-17  

**Scope files**

| Task | File |
|------|------|
| T053 | `apps/smart-writer-v2/tests/contract/test_bundle_roles.py` |
| T054 | `apps/smart-writer-v2/tests/contract/test_web_disabled.py` |
| contrast | `apps/smart-writer-v2/tests/contract/test_web_signal.py` (T018 / hook 5; not re-reviewed) |
| shared | `apps/smart-writer-v2/tests/contract/grant_flow.py` (`GRANT_PROMPT`, `GRANT_MATERIALS`) |

**Out of scope this session:** T016–T052 except as contrast. Do not start T056–T057. Do not rewrite spec/plan. Do not write product code. Prior T1–T28 stay locked (especially **T2**: no InternalRunState dump; **T4**: T018 is `none_declared` not `disabled`; **T24**: factual-low must not disable web). Prefer-criteria-over-trivia stays hybrid/human.

**Pytest (app venv, independently re-run 2026-09-17, at/after `f25f2d9`):**

| Test | Result | Fail locus |
|------|--------|------------|
| `test_bundle_ids_match_source_record_bundle` | **PASS** | — |
| `test_web_research_disabled_declares_disabled` | **FAIL** | `signal == "disabled"` — got `"none_declared"` |

T053 is already green. T054 fails on the lock field after a succeeded job (not 404 / ImportError). Catalog rows stay **hybrid**; no `acceptance.md` `how: auto` rows yet (T061 / plan P2).

---

### A. Executive verdict

**Approve tests with minor edits**

T054 hits the public messages contract with a distinct disable-web prompt, observes job `web_signal` (not GET conversation), and is red today because canned generate still runs with store `web_research_enabled=True` (Tavily unset → `none_declared`). That is honest red, and it is the T4 contrast T018 cannot supply.

T053 is **not** a red gate for T056. `assemble_artifact` already copies `materials_bundle_ids` / `web_bundle_ids` from the same `SourceRecord.bundle` partition the test recomputes; GRANT_MATERIALS already produces ≥1 materials row. Set-equality of two derived views of `sources[]` would stay green while F4 roles (`kind`, submitted URI, criteria-vs-trivia) fail.

Do not start T056 until Debates **T29–T31** are human-adjudicated (constitution §F). Do not green T054 by adding `web_research_enabled` to `MessageTurnIn`. Do not pytest `research.prefer_criteria_over_trivia`.

---

### B. Findings table

| ID | Severity | Lens | Locus | Finding | Suggested resolution |
|----|----------|------|-------|---------|----------------------|
| **T29** | **Debate** | Red-first / tautology | `test_bundle_roles.py`; F4; P4; T021/T024; T056 | Steelman: P4 said SC-003/004 hook bundle fields, not merely nonempty `sources[]`. Test requires both id lists present, set-equal to `sources[]` partitioned by `bundle`, and `len(materials_bundle_ids) ≥ 1` on the GRANT_MATERIALS fixture. Public HTTP; no graph stub. Attack: **PASSED** at review. `assemble_artifact` already sets those lists from the materials/web arguments T024 stamps `bundle="materials"\|"web"`. The test is DRY of that helper: a dummy materials row, `return list(SEED)`-class constant ids, or `kind=web` tagged `bundle=materials` all green it. Submitted URI is never bound. FR-007a/b (materials = criteria/org evidence; web = differentiating signal; prefer criteria over trivia) are untested — correctly not auto for trivia, which means **T056’s writer-context shall has no failing test**. Constitution §V: bundle-id product code for this slice already shipped in US1. | Keep set-equality as a **T021 landmine** (must fail if lists diverge from `sources[].bundle`). Bind F4 structure: materials rows `kind == "user_material"` and `uri` equals the GRANT_MATERIALS URI (fetch-fail path keeps the request URI today). Do **not** treat T053 PASS as T056 DoD. Do not pytest fit-point prose / trivia preference. |
| **T30** | **Debate** | Wrong-thing / lock fidelity | `test_web_disabled.py`; data-model `web_research_enabled`; FR-017; T056 vs infer; T2 | Steelman: user disables web → `web_signal=disabled` not `none_declared`; no `bundle=web` rows. Observes job JSON. Fail locus is the lock, not a missing route. Attack: POST contract is `text` / `client_intent` / `citation_mode` / `materials` only. Store default is `True`. Canned `_run_generate_without_llm` never reads “Do not use web research.” LLM `infer.txt` says skip when asked; contract tests do not run that agent. Unit `decide_web_signal(False) == "disabled"` is **already green**. T056 DoD is “graphs set bundle ids and F4 preference in writer context” — **not** infer/store the disable flag. Implementers will (a) regex the fixture string inside generate without writing `InternalRunState.web_research_enabled`, or (b) extend `MessageTurnIn` (T17-class). A substring theater also fights T047/T24 (factual-low must not disable). | Keep T054 HTTP: `web_signal == "disabled"` on this fixture. Matching impl is a **deterministic infer seam** (same pattern as `extract_intent_slots` / `infer_property_ranking`) that sets store `web_research_enabled=False` from the disable prompt, called from `POST .../messages` **before** enqueue. Do **not** add `web_research_enabled` to `MessageTurnIn`. Do **not** dump the flag on GET conversation (T2). T056 may consume the store bool (already passed into `run_generate`); greening T054 is not “add a writer instruction.” |
| **T31** | **Debate** | Lock fidelity / SNR | T054 vs F4 / FR-007; T053 | Steelman: `all(bundle != "web")` is stronger than status-200 and catches leftover Tavily rows if someone only relabels `web_signal`. Attack: skip **all** retrieval, stamp `web_signal=disabled`, empty `sources[]` → T054 greens while FR-007 materials-first-class fails. Relabel web hits `bundle=materials` → T054 greens and T053 on the *other* fixture still passes. `web_bundle_ids` is never asserted `== []` here. US5 independent test (tasks.md) is “bundles attached; web unused → declare” — unused-declare is T018; T054 is the disabled complement, and it does not require materials still attached. | On the disable fixture: ≥1 materials row (`kind=user_material`, GRANT_MATERIALS URI) **and** `web_bundle_ids == []` (key present) **and** no `kind=web`. Keep `web_signal == "disabled"`. Do not require live Tavily. |
| **T32** | **Strength** | Red-first / scope | T054 vs T018; T2; catalog human row | T054 fails on `web_signal` after job success, not ImportError/404. Disable prompt is **not** `GRANT_PROMPT` alone — T018 stays `none_declared` on the enabled noop fixture (T4). Public HTTP only; no LangGraph/Tavily stub; no GET ranking/slots dump. `research.prefer_criteria_over_trivia` is correctly not pytested. | Keep the T018 vs T054 split and the no-graph-stub rule. Do not stub `_execute_job` to `{web_signal: disabled}`. After infer seam exists, T018 must still fail if enabled+empty is labeled `disabled`. |
| **T33** | Later | Scope / SNR | T053 vs T057; T056 writer; T018 | `MessageTurnIn.materials` already exists; T053 PASS does not gate T057. Writer already injects an F4 preference sentence on the LLM path; canned generate never calls it. T053/T054 cannot fail closed on that sentence (and must not — hybrid/human). | Leave T057 as “already accepted or confirm URI still round-trips” after T29. T056 prompt-program edits are code review / human catalog, not this T*. After T030, re-check T018 ≠ `disabled`. |
| **T34** | Nit | SNR | T054 vs T047 enum; T053 `set()` | T047 asserts enum membership then `!= disabled`. T054 uses `== "disabled"` only (missing key → KeyError, fail-closed). `set(materials_bundle_ids)` drops duplicates/order the data model allows as `list`. | Optional: `web_signal in {used, none_declared, disabled}` then `== disabled`. Keep list→set equality; do not require order. |

Minimum count met. Debates: T29, T30, T31. Strength: T32.

Correctly **not** pytested (do not fake): `research.prefer_criteria_over_trivia` (human); SC-002 ≥2 fit points from materials (hybrid/human); “web finding affects ask/framing” prose; file upload (P7); LangGraph-as-product-SC (F5).

---

### C. Adversarial positions (required)

1. **Position: these tests would go green while a spec lock fails** — strongest case

   Leave `assemble_artifact` as US1. T053 stays green. In canned generate, if `"do not use web" in user_text.lower()`: set `web_signal=disabled` and drop `bundle=web` rows (or never search). Do not write `InternalRunState.web_research_enabled=False`. Do not change writer/prompt so materials criteria outrank web trivia. Relabel any remaining hits `bundle=materials`. T054 goes green. T018 still sees the default prompt.

   F4 / FR-007a/b fail (roles are tags, not jobs). FR-017/store disable fails (next turn still searches). Catalog `research.used_or_declared` is the wrong `when` if the flag never flipped. T056 can no-op. Pytest is green.

   *What would have to be true for the suite to be right anyway:* T053 is only JSON partition consistency (US1 leftover); trivia/fit stay human; T054 is allowed to special-case the fixture string as the disable signal — **if** T29 binds `kind`+URI, T30 writes the store flag via a named infer seam (not generate regex), and T31 keeps materials on when web is off.

2. **Position: these tests over-constrain implementation / test the wrong layer** — strongest case

   T053 retests `assemble_artifact` under `tests/contract/` (T28-class). Binding fetch URI flakes if the fetch façade rewrites the final URL. T054’s English fixture is prompt theater: FR-017 is the LLM infer node (`infer.txt` already states the shall); a second canned regex duplicates T049-style token matching and will miss “skip Tavily” / “offline only.” Requiring materials-still-present (T31) couples the disable path to URL fetch. Unit `decide_web_signal(False)` already encodes SC-004’s disabled arm. T056 cannot green T054 without infer work the task list does not name — deadlock if T* forbids T056 until T054 is red-for-the-right-reason.

   *What would have to be true for the suite to be right anyway:* contract tests run without OpenAI (canned path must infer disable like slots/ranking); GRANT_MATERIALS URI is stable on fetch-fail; `decide_web_signal` unit is not a substitute for HTTP store→job; T056 consumes the flag, a small infer helper is in-slice even if tasks.md titled the work “bundle ids.”

---

### D. Catalog / contract coverage map

| Catalog id or contract hook | Test file / name | Can fail today? | Gap |
|-----------------------------|------------------|-----------------|-----|
| P4 / F4 — `materials_bundle_ids` vs `web_bundle_ids` from `SourceRecord.bundle` | `test_bundle_roles.py::test_bundle_ids_match_source_record_bundle` | **no** (PASS) | Derived partition of `sources[]` (T29). No `kind` / URI bind |
| Hook 5 — web enabled, empty search → `none_declared` | T018 `test_web_signal.py` (contrast) | yes (green on lock) | T4 locked; T054 must not break this |
| SC-004 complement — `web_research_enabled=false` → `web_signal=disabled` | `test_web_disabled.py::test_web_research_disabled_declares_disabled` | **yes** (`none_declared`) | NL fixture; no store/infer seam (T30). No materials-still-on (T31) |
| `research.used_or_declared` (hybrid; **when** web enabled) | T018, not T054 | n/a for T054 | Disabled path is outside this row’s `when` |
| `research.prefer_criteria_over_trivia` (human) | none | n/a | Correctly not pytest (packet / F4 remainder) |
| `beachhead.audience_fit_min` prefer materials (hybrid) | none as auto | n/a | Correctly not faked |
| FR-007 accept materials on POST | T053 `len(materials_bundle_ids) ≥ 1` | **no** (PASS) | T057 already in `MessageTurnIn` (T33) |
| FR-007a/b roles in writer context | none | **no** | T056 prompt; hybrid/human (T33) |
| T2 — no run_state dump | T053/T054 job JSON only | n/a | Do not observe disable on GET conversation |
| Unit `decide_web_signal(False)` | `tests/unit/test_generate_assemble.py` | **no** (PASS) | Not a T054 substitute (T30) |
| Any `how: auto` catalog row | none | n/a | Still zero; T061 later |

---

### E. Edit list

- `test_bundle_roles.py`: materials rows `kind == "user_material"`; at least one `uri` equals `GRANT_MATERIALS[0]["uri"]`; keep set-equality + keys present + `len ≥ 1`.
- `test_bundle_roles.py`: document T053 as already-green T021 landmine — T056 DoD is not “make this pass.”
- `test_web_disabled.py`: keep `web_signal == "disabled"`; add `web_bundle_ids == []` (key present); ≥1 materials `kind=user_material`; no `kind=web`.
- Infer seam (if T30 locked): helper on `_DISABLE_WEB_PROMPT` → `web_research_enabled is False`; `POST .../messages` must call it into the store (no GET dump; no new POST field).
- Do **not** add `web_research_enabled` to `MessageTurnIn`.
- Do **not** pytest trivia-vs-criteria prose or stub `_execute_job` / Tavily to the assertion JSON.
- After T030/T056: T018 remains `none_declared` on the enabled noop fixture; T047 remains `!= disabled` on factual-low.
- Defer: `used` with nonempty web bundle (live Tavily); uploads (P7); T057 if URI bind (T29) already proves links.

---

### F. Questions for the human (max 3)

1. **T29:** May T053 stay green as a T021 landmine (set-equality only), or must it bind `kind` + GRANT_MATERIALS URI before T056 — knowing bundle-id product code already exists?
2. **T30:** Must T054’s matching impl be a deterministic infer→store seam (like T049), or is fixture-string handling inside generate allowed? Must T056 wait on that seam even though tasks.md names graph/writer, not infer?
3. **T31:** On the disable fixture, must materials still appear (F4 first-class when web is off), or is `web_signal=disabled` + no `bundle=web` enough?

Implementer: do not start T056 until T29–T31 are accepted or the tests are edited. Nit/Later (T33–T34) may be agent-adjudicated (§F). Do not implement disable by extending the messages request body. Do not fake prefer-criteria-over-trivia as pytest.
