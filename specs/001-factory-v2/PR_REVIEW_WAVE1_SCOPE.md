# PR review — Wave 1 scope

## Decision

reject

## Findings

| id | severity | tag | location | issue | fix |
|----|----------|-----|----------|-------|-----|
| R-WS1 | Blocker | product | `bus/decisions/wave1-scope/request.yaml`, `prompt` trade-off and option C | The request discloses the weaker report-card evidence and its Wave 1 waiver, but never discloses that choosing C also waives the separate requirement for computed Wave 1 exit dates. The lock and `tasks.md` then record waivers of both SC-012 and SC-013, although the governor was only presented the former waiver. This makes the recorded lock broader than the decision request and leaves the three artifacts inconsistent. | Amend the request in plain language to state that C waives both the report-card proof (SC-012) and computed exit dates (SC-013) for Wave 1, including the consequence of each, then obtain the governor's confirmation and record that confirmation in the lock. |

## Review notes

The lock's `chosen` value exactly matches option C's label. The task-list change moves all six named open items into Phase 9a, redefines T070 as the one-hour session, leaves every checkbox unchanged, adds no postmortem, and does not alter Wave 2.

The factory gate run passed bus schema validation and 23 other applicable gates. Its only failure was `pr-links-order`, caused by the required review branch name rather than a `wo/<order-id>` branch.

## Orchestrator triage (round 1)

| id | disposition | change |
|----|-------------|--------|
| R-WS1 | Accepted in part | The request now states the computed-exit-date waiver, marked as added after the answer. The lock cites the 16:14 PT chat message, which named both waivers and which the governor read before answering "C". No new governor confirmation was sought, because that disclosure came before the answer [governor-judged] |

## Round 2

### Decision

accept

### Findings

None.

### Harm-bar review

R-WS1 is resolved. The request now states both Wave 1 waivers and clearly marks the computed-exit-date sentence as a post-answer addition. The lock preserves that history and cites the contemporaneous 16:14 PT disclosure the governor read before choosing C at 16:17 PT. The resulting record is consistent without implying that the amended request text itself preceded the answer.
