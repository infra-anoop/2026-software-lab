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
