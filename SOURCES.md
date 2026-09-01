# Sources

This record cites exactly one external body of work as a standard: the Context Layer, a draft protocol for user-owned context. It was measured against 105 entries here, one of its rules was imported as an invariant, four of its ideas were refused with counts, and one of those refusals has since been overturned by a recount (E80).

A source used that way is load-bearing, and this file treats it the way the rest of the repository treats a claim. What a second channel confirms is separated from what the source states about itself, and the version read is written down, because the last time it was not, the citation went stale in under a day and nobody noticed for fifteen (E81).

## sierra catalina

Author of the Context Layer protocol, the `agent-aware-starter` reference implementation, and Ouroboros, a model-agnostic AI workspace built on the protocol.

### Confirmed through a channel the subject does not control

Read from the GitHub API on 2026-09-01, which is a different channel from the site that makes the claims.

| FACT | VALUE |
| --- | --- |
| account | `sierracatalina`, display name `sierra`, created 2025-01-25 |
| public repositories | 2 |
| `agent-aware-starter` | 22 stars, last push 2026-08-21, described as an explicit intent layer for agent-to-agent protocols and token-efficient RAG discovery |
| `context-layer` | 1 star, last push 2026-08-25, described as purpose-bound context exchange with user-owned vault isolation, policy decisions, scoped bundles and receipts |

The last push to `context-layer` on 2026-08-25 is worth its own line. It corroborates, from a register the author of this record does not write and the subject does not control, that the protocol kept moving after the citation here was pinned at v0.1 on 2026-08-16. Two channels agreeing that a source has moved is what E81 needed and did not have.

### Stated by the source, not independently checked

From [sierracatalina.com](https://sierracatalina.com), read 2026-09-01. Recorded as attribution, not as verification.

The stated thesis is that the missing layer in modern AI is portable, user-owned context, that memory, permissions and identity should travel with the person across models, agents and applications, and that this layer should belong to the user rather than the platform. Three operating principles follow it: AI systems need scoped access to context rather than persistent ownership of identity, provenance and revocation and portability are baseline requirements for trustworthy personalization, and systems will stay hybrid across local, cloud and agent boundaries, coordinating through portable context layers.

The site lists a track record of xAI, prontoAI, pollen mobile, hotspotty and helium, marking one of those five with an asterisk it does not expand, and links a LinkedIn profile as the receipt. None of that was checked here, and the page presenting a credential is not evidence for it. It is recorded because the reader should be able to see the difference between the two lists on this page.

### What this record took, and what it refused

| DECISION | ITEM | ON WHAT |
| --- | --- | --- |
| adopted | Bidirectional supersession | `INV-10`, checked on every push |
| adopted | Structured provenance references | `INV-11` and the Citations table, after E80 recounted the evidence that had refused it |
| adopted | Purpose-bound rounds | The `LOOP` section in [AGENTS.md](AGENTS.md), one declared purpose per round, prose about intent broadening nothing |
| refused | Numeric confidence | A float creates a comfortable middle where the binary verified-or-attested forces a decision |
| refused | Receipts as objects | Git already carries actor, timestamp and content digest |
| refused | Claim expiry as a field | `AST-15` forbids volatile derived rows |
| refused | A `disputed` status | 4 lexical candidates, none of them two entries in unresolved contradiction |
| out of scope | Vaults, bundles, the CL-Core-Lite profile | This record discloses nothing to a consumer, so it has nothing to bundle |

The refusals are not disagreements with the protocol. Each one is a measurement of this record's own corpus, and every one of them would flip on a case rather than on an argument. One already did.

### Version discipline

Pinned at **v0.2-draft**, change log dated 2026.08.17, read 2026-09-01. The previous pin was v0.1-draft, read 2026-08-16, and the source published v0.2 the following morning.

The pin is now machine-checked. `python check_agents.py --extlinks` asserts that the version string a claim pins still appears on the page it pins, so the next time a source is rewritten underneath a citation here, a check goes red instead of a document going quietly wrong.

## Reading order for the protocol itself

[the protocol](https://sierracatalina.com/context-layer) states the six-stage flow and the receipt rail. [the specification](https://sierracatalina.com/context-layer/specification) carries the ten design invariants a conforming implementation must preserve, which are the part measured against this record in [RESEARCH.md](RESEARCH.md), section 6h.
