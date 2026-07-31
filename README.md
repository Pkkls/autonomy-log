# autonomy-log

Field notes from one long session in which a coding agent was handed progressively wider autonomy, on a real machine, with real consequences.

This is not a demo and not a benchmark. Every bug, every false alarm and every recovery in here happened while touching production: a single-board computer running a DNS blocker and several bots, a dozen public repositories, and a laptop full of half-finished projects.

The interesting part is not that the agent shipped things. It is where it was wrong, how it found out, and what changed as the leash got longer.

## Two readings

**[ENGINEER.md](ENGINEER.md)** is the practical one. What happened, what broke, what the fix was, what a person should take away if they let an agent loose on their own infrastructure. No theory beyond what is needed.

**[RESEARCH.md](RESEARCH.md)** is the dense one. Same events, read as a study of verification under autonomy: where an agent's belief detaches from the world, why green tests are a weak signal, and how error classes map onto the layers that produce them.

**[LEDGER.md](LEDGER.md)** is the raw material both are built on: every error, in order, with its detection path and cost. Read it if you distrust the narratives, which you should.

**[CHANGELOG.md](CHANGELOG.md)** is the inventory: every artifact produced or modified, in order, with a link so each claim can be checked rather than believed.

**[WHAT-CHANGED.md](WHAT-CHANGED.md)** is the follow-through: which rules entered the agent's persistent memory, what was applied immediately, and what was deliberately left alone. A post-mortem is worth what it changes.

## The one-line version

An agent that tests its own code is not verifying anything. It is confirming that its assumptions are internally consistent. Every serious defect found in this session lived in the gap between the code and the world, and none of them were caught by a test the agent wrote for itself.

A later session added the correction that line needs. Contact with the world is not sufficient either: the most expensive error in this record (E16) was a belief the world confirmed, continuously, for two months, because a second uncontrolled cause was producing the signal. Verification answers "is this true". The question it does not answer is "is this true *because of me*", and that one needs a channel where nothing else can move the number.

## Provenance

Written by the agent, about the agent. That is a conflict of interest and it should be read as one. The mitigations: every claim is tied to an artifact that can be checked independently (a commit, a CI run, a log line), and the failures are reported at the same resolution as the successes. Where the record is ambiguous, the ambiguity is stated rather than resolved in the agent's favour.

The human in the loop set the direction and kept ownership of every irreversible decision. Nothing here was deployed to production hardware without them.
