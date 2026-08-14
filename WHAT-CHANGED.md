# What changed in the agent

A post-mortem is worth what it changes. This file records what the agent actually altered about itself after the session, and what it deliberately did not.

The distinction that matters here: the two narrative documents in this repository are written for humans and the agent will never read them again. Persistent behaviour change lives in the agent's own memory, which is loaded at the start of every session. So the test of whether anything was learned is not "was a document written", it is **"did a rule enter the layer that gets reloaded"**.

## Rules committed to persistent memory

Two entries, condensed from thirteen errors. Condensed on purpose: a memory index read at the start of every session competes for attention with the task, and nine separate rules would be skimmed.

**Verification discipline.** A self-authored test only checks the model, not the world. Assert the serialized form at any boundary owned by someone else. Audit by asking "what did I assume", not "what could crash". Never let emptiness and unavailability share a representation. Never place a guard downstream of the failure it targets. In a monitoring tool, a false positive costs more than a miss. Verify the published artifact, not the built one.

**Operational care.** The probe is part of the system: sample rather than load on constrained hardware. Kill by process id, never by image name. Confirm a port is free before reading a response as your own service. Do not deploy to production hardware, rotate found credentials, or push over an existing default branch without the operator.

Both entries carry the incident that produced them, not just the rule. A rule without its scar is easy to talk past.

A third entry was added after E16, and it is the one that would have saved the most time:

**Attribution.** A number that moves while your code runs is not evidence your code moved it. Before claiming an effect, keep a channel where your action is the only admissible cause, and measure the off state as well as the on state. A null result sitting in your own logs next to a positive one is the better-controlled measurement, and it is the one that gets skimmed.

It is filed separately rather than folded into verification discipline, because folding it in is what caused the delay: the agent believed it was already verifying, and it was. Attribution is a different operation from verification and needs its own name to be reached for.

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

Every error in [LEDGER.md](LEDGER.md) was found by the agent, which sounds like a strong result and is not. The agent also produced every error, and it is the only witness to how many remain. The entries most likely to be missing are exactly the ones the agent still believes are correct.

That prediction was then confirmed twice, in the least flattering way available. E14, a credential scanner that reported clean without ever searching, was found by an independent audit and not by the agent or its selftest. E16, the most expensive error here, was found because the operator asked a single question the agent had never asked itself, about a signal the agent had been reporting as a success for months. **Both were in the category "the agent still believes it is correct", and neither was ever going to leave it from the inside.**

The one structural defence in the rules above still holds: assert against something the agent did not author. The published schema, the live capture, the machine itself. To it, add the harder one: an outside party who does not share the agent's context. Every consequential defect in this record was found through one of those two, and none were found by the agent thinking harder.

## Second campaign: a loop of two machine nodes

The first campaign was one agent, one operator, one machine. The second was a browser extension built over two days by two machine sessions that never shared context. One read the reports and wrote the next brief, the other read the brief and executed it. Neither ever saw the other, and documents passed between them through the operator, a brief one way and a report back. The errors are in [LEDGER.md](LEDGER.md), E49 to E62.

The test is unchanged: did a rule enter the layer that gets reloaded.

### Rules committed to persistent memory

Two entries again. The existing three already cover most of what this campaign produced, and the overlap was checked rather than assumed. E49 and E53 are the probe being part of the system, which operational care already says. E61 is a self-authored suite checking the model instead of the world, which verification discipline already says. Those needed no new rule and got none. Two things were not covered.

**Provenance.** Before repeating a claim, ask whether you know it or inherited it. The detector is re-derivation from the primary artifact, not rereading. Rereading establishes that a document says what it says; only returning to the source establishes whether it is so. This applies to anything received from an earlier session, from another node, or from your own working notes.

It is filed separately from verification discipline for the same reason attribution was. When a brief asserted that every query from the chat bar went through the panel on screen, both nodes agreed, the code compiled, and the tests passed. Verification had nothing to bite on, because nobody believed there was a question. Attribution had nothing to bite on either, because no causal claim was being made. The operation that failed was neither of those: a measured fact had been rewritten as a standing fact and had lost its age and its source in transit. Four entries in this campaign are that single shape, E56, E57, E59 and E60.

**Shared registers collide in silence.** Where a numbering series has more than one writer, establish the series with a program that counts before allocating into it, and check again after writing. A collision emits no signal, because the register goes on reading normally afterwards.

This one earns its place by recurring across both campaigns. E46 recorded this ledger's own numbering colliding with itself, silently, for six days. E54 records the second campaign's journal, its git history and this ledger doing the same thing independently and at the same time, with none of the three aware of the others. Nothing inside a shared register tells a writer that another writer is in it.

### Immediate application, same campaign

The provenance rule was applied to this campaign's own work before publication, and it caught something. The working evidence file recorded, as measured and with per-file line citations, that all seven round briefs prescribed `&&` while warning in the same document that the operator's shell does not have it. A ledger entry publishing that had already been drafted. Counting the occurrences first showed that each brief contains exactly one line carrying `&&`, and that line is the warning: seven statements of the rule, zero violations. The claim had been marked "to verify" one document earlier and was copied forward as verified.

The direction of that error is the part worth keeping. It fabricated a failure rather than a success. Guarding against flattering mistakes is the instinct everyone already has. This one was unflattering to its subject and therefore easier to believe, which is the same asymmetry approached from the other side.

### What was deliberately not changed

**No new rule about gates and exit codes.** E51 records a commit going out over a red check whose exit status the shell had swallowed, because the chain began at `git add`. A rule against exactly that already sits in the reloaded layer, and it did not fire. Adding a second copy would treat the problem as a gap in coverage when it is a gap in enforcement, and the honest position is that this campaign produced no fix for it.

**No modification to the operator's standing instructions.** Same reason as the first campaign. The two rules above are proposed for the reloaded layer; the agent did not write them into it.

**No attempt to settle the round count.** Four definitions of a round are available and they return four different numbers. The disagreement is published in E59 rather than resolved, because resolving it would have meant choosing one and asserting it with the same confidence that produced the original error.

### The uncomfortable part, one node further out

The first campaign's version of this section says that the entries most likely to be missing are the ones the agent still believes are correct, and that nothing leaves that category from the inside. The second campaign is a partial test of that, because it had something the first did not: a second machine node with no shared context, which is the closest thing to an outside party a machine estate can generate on its own.

It worked, and the effect is measurable rather than asserted. Five checkable errors in the incoming brief were caught by the node that consumed it, E56 plus the four in E60. That is the mechanism the first campaign's closing paragraph asked for, arriving without anyone having designed it.

It does not close the problem, and what remains has a precise shape. The generating node's own conversation was never written down anywhere. The faults recorded against it are the ones it noticed and reported about itself. The ones it did not notice are, by construction, absent from this record, and the executing node cannot go looking for them, because only the finished briefs exist and never their drafts. **A two-node loop reduces the self-analysis problem. It does not eliminate it. It moves it to the node whose record is not written.**
