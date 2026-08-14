# autonomy-log

Field notes from two campaigns in which coding agents were given progressively wider autonomy on a real machine, with real consequences.

This is not a demo and not a benchmark. Every bug, every false alarm and every recovery in here happened while touching production: a single-board computer running a DNS blocker and several bots, a dozen public repositories, a published browser extension, and a laptop full of half-finished projects.

The interesting part is not that the agents shipped things. It is where they were wrong, how they found out, and what changed as the leash got longer.

## The two campaigns

**One long session.** One agent, one operator, autonomy widening from narrow tasks to "explore, no restrictions". Each step changed the failure mode rather than the throughput. By the end it was auditing the infrastructure it had been working on, and it found two silent production failures and caused one operational incident.

**A loop of two agent sessions that never met.** One read the reports and wrote the next brief. The other read the brief and did the work. They shared no context, and the documents passed between them by hand. Nobody designed this: it accreted after a large brief pasted into the client failed twice and had to become a file. The structure turned out to catch errors in its own instructions, which a single session has no mechanism to do.

## Three questions, in the order they were learned

Each was added because the previous one turned out to be insufficient. The record of those two corrections is the argument.

**Is this true?** An agent that tests its own code is not verifying anything. It is confirming that its assumptions are internally consistent. Every serious defect in the first campaign lived in the gap between the code and the world, and none of them was caught by a test the agent wrote for itself.

**Is this true because of me?** Contact with the world is not sufficient either. The most expensive error in this record was a belief the world confirmed, continuously, for two months, because a second uncontrolled cause was producing the signal. Answering this one needs a channel where nothing else can move the number, and the off measurement as well as the on measurement.

**Do I know this, or did I inherit it?** A claim can be true, confirmed, and genuinely caused by you, and still be one you never derived: it arrived, was written down as settled, and was passed on carrying no mark of its age or its source. Its detector is neither a test nor contact with the world. It is going back to the primary artifact and deriving the claim a second time, which is not the same act as rereading the document that carries it.

The third question produced a fresh instance of itself inside the document that defined it. That is filed as an error rather than tidied away.

## What the errors look like once sorted

| Layer | Detector | Caught by that detector? |
| --- | --- | --- |
| L0 syntax, types | Compiler, formatter | Always |
| L1 internal semantics | The agent's own tests | Yes |
| L2 external semantics | Contact with the real system | No, found by audit |
| L3 statistical, decision | Comparison against ground truth | Only by running against reality |
| L4 operational | A cost model of one's own actions | Partially, after damage |
| L5 attribution | An observation only your action explains | No, and it survived two months |
| L6 provenance | Re-derivation from the primary artifact | Yes, by the node receiving the claim |

L0 and L1 are saturated. Everything consequential lives at L2 and above, which is why answering an incident with more unit tests puts resources into the one layer that is already defended. The full argument, including why L6 does not collapse into L2 and why its clean detection record is unflattering rather than impressive, is in [RESEARCH.md](RESEARCH.md).

## The documents

| File | What it is |
| --- | --- |
| [ENGINEER.md](ENGINEER.md) | The practical read. What broke, what the fix was, what to do differently if you hand an agent the keys. Ends with the two-node protocol written out so someone else can run it. |
| [RESEARCH.md](RESEARCH.md) | The dense read. The same events as a study of verification under autonomy: where belief detaches from the world, why green tests are a weak signal, and how error classes map onto the layers that produce them. |
| [LEDGER.md](LEDGER.md) | The raw material both are built on. Every error, in order, with its detection path and its cost. Read this if you distrust the narratives, which you should. |
| [CHANGELOG.md](CHANGELOG.md) | The inventory. Every artifact produced or changed, with a link so each claim can be checked rather than believed. |
| [WHAT-CHANGED.md](WHAT-CHANGED.md) | The follow-through. Which rules entered the agent's persistent memory, what was applied immediately, and what was deliberately left alone. |

A post-mortem is worth what it changes, so the last file is the test the others are graded against. The standard it uses is deliberately narrow: not "was a document written" but "did a rule enter the layer that gets reloaded".

## If you only read a handful of entries

**E16**, the belief the world confirmed for two months because something else was moving the number. The disconfirming evidence was not missing. It was present, in the agent's own logs, and unread, because it sat next to a larger signal pointing the desired way.

**E46 and E54**, a numbering series colliding with itself in silence: first in this ledger, for six days, then in three registers of the next campaign at once, none of them aware of the others. A collision emits no signal because the register goes on reading normally afterwards.

**E51**, a commit that shipped over a red check because the shell chain began with `git add`, so the gate's exit code guarded nothing. A cheap green witness was available at the same time and was also wrong, because the test runner does not typecheck.

**E63**, this repository's own inventory calling itself public and linking a page that returns 404 to everyone except its author, inside the file whose opening rule is that claims should be checkable rather than believed.

## Provenance

Written by the agent, about the agent. That is a conflict of interest and it should be read as one.

The second campaign does not improve on this, it complicates it. That part is written by a later node of the same estate about its predecessors, using registers the estate itself produced. Its method is more careful than the first campaign's, with falsification cases and detectors witnessed failing before they were trusted. That is not a defence. Rigour of method is exactly what would make a conflict of interest invisible rather than absent.

The mitigations are ordinary ones. Every claim is tied to an artifact that can be checked independently: a commit, a CI run, a log line. Failures are reported at the same resolution as successes. Where the record is ambiguous, the ambiguity is stated rather than resolved in the agent's favour. Where a claim rests on testimony with no artifact behind it, it is marked as such in place rather than quietly promoted.

Two claims were withdrawn during the second write-up rather than defended, including the one that would have made the strongest headline. They are in [RESEARCH.md](RESEARCH.md), section 6e.

The human in the loop set the direction and kept ownership of every irreversible decision. Nothing here was deployed to production hardware without them.
