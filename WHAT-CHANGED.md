# What changed in the agent

A post-mortem is worth what it changes. This file records what the agent actually altered about itself after the session, and what it deliberately did not.

The distinction that matters here: the two narrative documents in this repository are written for humans and the agent will never read them again. Persistent behaviour change lives in the agent's own memory, which is loaded at the start of every session. So the test of whether anything was learned is not "was a document written", it is **"did a rule enter the layer that gets reloaded"**.

## Rules committed to persistent memory

Two entries, condensed from thirteen errors. Condensed on purpose: a memory index read at the start of every session competes for attention with the task, and nine separate rules would be skimmed.

**Verification discipline.** A self-authored test only checks the model, not the world. Assert the serialized form at any boundary owned by someone else. Audit by asking "what did I assume", not "what could crash". Never let emptiness and unavailability share a representation. Never place a guard downstream of the failure it targets. In a monitoring tool, a false positive costs more than a miss. Verify the published artifact, not the built one.

**Operational care.** The probe is part of the system: sample rather than load on constrained hardware. Kill by process id, never by image name. Confirm a port is free before reading a response as your own service. Do not deploy to production hardware, rotate found credentials, or push over an existing default branch without the operator.

Both entries carry the incident that produced them, not just the rule. A rule without its scar is easy to talk past.

## Immediate application, same session

The first rule was applied to the agent's own unfinished work within minutes of being written. A fix had been produced for a production daemon, compiled, and left **untested**, which is precisely what the new rule forbids.

Writing that test surfaced a second-order problem worth recording. The honest test reproduced the real outage: a rate-limited endpoint answering 429. But the code under test backs off for 30, 60, 120 and 240 seconds by design, so the faithful test took minutes and was killed twice before finishing. A suite that slow does not get run, which makes it worse than no suite at all.

The resolution was to test the same branch through a failure mode that fails fast, and to write down why in the test itself:

> 403 rather than the 429 seen in the real outage: both mean "not read", but 429 deliberately backs off for minutes, which would make this suite slow enough that nobody runs it. The branch under test is the same.

Three tests, 0.073 seconds. **Fidelity to the incident had to be traded against the probability that anyone ever runs the check**, and the trade is documented at the point of the compromise rather than argued in a commit message nobody will find.

## What was deliberately not changed

**No modification to the operator's global configuration.** The agent's standing instructions are the operator's file. Editing them would be the agent rewriting its own constraints, which is the one change it should never make unilaterally, regardless of how well justified an individual edit looks.

**No automation of the audit.** A tempting move after this session is a hook that runs the assumption audit on every task. It was not built, because the audit's value came from being expensive and deliberate. Made automatic and cheap, it becomes another green light to accumulate, which is the failure mode the whole session is about.

**No new tooling for its own sake.** Three small tools came out of the session and all three exist because a concrete failure demanded them. Nothing was built on the theory that it might help later.

## The uncomfortable part

Every error in [LEDGER.md](LEDGER.md) was found by the agent, which sounds like a strong result and is not. The agent also produced every error, and it is the only witness to how many remain. There is no independent audit in this record, and the entries most likely to be missing are exactly the ones the agent still believes are correct.

The one structural defence against that is in the rules above: assert against something the agent did not author. The published schema, the live capture, the machine itself. Every consequential defect in this session was found that way, and none were found by the agent thinking harder.
