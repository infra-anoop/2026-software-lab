# Research template (lab)

Copy structure into `specs/<feature>/research.md` during `/speckit-plan` Phase 0.  
Enforce `docs/agent-os/STACK_POSTURE.md` + `docs/agent-os/PLAN_AUTHORING_GATES.md`.

For each major block below that the Architecture uses, fill Decision / Rationale / Pattern source / Alternatives.
Mark unused blocks `N/A`.

---

## Block: UI client

- **Decision:**
- **Rationale:**
- **Pattern source:** (none | path)
- **Alternatives considered:** (≥1 non-sibling SOTA/managed/OSS or Deferred to Pn)

## Block: UI host / deploy

- **Decision:**
- **Rationale:**
- **Pattern source:**
- **Alternatives considered:**

## Block: API / application service

- **Decision:**
- **Rationale:**
- **Pattern source:**
- **Alternatives considered:**

## Block: Jobs / orchestration

- **Decision:** (include P1 lock: named graph nodes **or** linear + migrate trigger — not “when fit” alone)
- **Rationale:**
- **Pattern source:**
- **Alternatives considered:**

## Block: Data store

- **Decision:**
- **Rationale:**
- **Pattern source:**
- **Alternatives considered:**

## Block: Search / retrieval / LLM

- **Decision:**
- **Rationale:**
- **Pattern source:**
- **Alternatives considered:**

## Block: Secrets / preview gate

- **Decision:** (include who holds the secret: BFF | same-origin server | …)
- **Rationale:**
- **Pattern source:**
- **Alternatives considered:**

## Block: Topology & runtime custody

- **Decision:** (runtimes/hosts; how UI talks to API; secret custody)
- **Rationale:**
- **Pattern source:**
- **Alternatives considered:**

## Other forks (feature-specific)

- …
