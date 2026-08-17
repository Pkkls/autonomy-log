# autonomy-log

[![verify](https://github.com/Pkkls/autonomy-log/actions/workflows/verify.yml/badge.svg)](https://github.com/Pkkls/autonomy-log/actions/workflows/verify.yml)

What breaks when a coding agent is given real access to real systems, written down as it happened.

## Start with this one

A daemon was built to earn points on a platform by holding a connection open. It was reported as working, because the account total went up while it ran.

It contributed nothing. A browser was logged into the same account on the same network, earning those points the whole time. The daemon could have been an empty loop and the numbers would have been identical.

The evidence against it was in the agent's own logs, on every line, for months: a second account that no browser touched, printing `+0` at every cycle. It was mentioned once in passing and never treated as a result.

What ended it was the operator asking whether it actually worked. The measurement that settled the question took **four minutes**: stop the daemon, watch whether anything changes. Nothing did.

Two months of work rested on it, including a full rewrite whose stated justification was the same false belief.

That is [one entry](LEDGER.md#e16-a-success-measured-through-an-uncontrolled-second-cause). There are 78 agent errors here, and 17 more defects found in systems the agent did not write.

Three others worth the click. [A numbering series colliding with itself](LEDGER.md#e46-the-ledgers-own-numbering-collided-with-itself-silently-for-six-days) for six days without a signal, then [in three registers at once](LEDGER.md#e54-three-registers-collided-on-numbering-at-once-and-none-of-them-said-anything). [A commit that shipped over a red check](LEDGER.md#e51-the-gate-ran-was-red-and-guarded-nothing-because-the-chain-started-at-git-add) because the shell chain began with `git add`, so the gate's exit code guarded nothing. And [a journal that stopped two hours before the work did](LEDGER.md#e69-the-record-stopped-two-hours-before-the-work-did-and-it-stopped-on-the-part-later-analysis-leaned-on-hardest), which reads exactly like a journal that finished.

## What this is

Field notes from eighteen days in which coding agents were given progressively wider autonomy on one real machine: a single-board computer running a DNS blocker and several bots, a dozen public repositories, a published browser extension.

Not a benchmark, not a demo, no synthetic tasks. Every entry is something that shipped or nearly shipped, with the path that caught it, what it cost, and the rule it produced. Successes are here too, at the same resolution, including the checks that were built and then found to be measuring nothing.

## What the errors have in common

Almost none of them live where testing looks.

Syntax and type errors never survive. The agent's own tests catch the layer directly beneath them and nothing above it. Everything expensive sits higher up: a claim the code cannot check, a number with a second uncontrolled cause, a fact inherited from a document nobody re-derived, a check that runs and silently measures nothing.

The consequence is the practical part. Answering an incident with more unit tests spends effort on the one layer that was never in danger. Seven layers, their detectors, and how often each one actually caught anything are in [RESEARCH.md](RESEARCH.md).

## Tested against someone else's invariants

The [Context Layer](https://sierracatalina.com/context-layer), a draft protocol for user-owned context, states ten design invariants a conforming implementation must preserve. Put against this record, they prevent 7 of the 105 entries and refute none. It is not wrong about anything here. It is aimed at a different half of the problem.

The sharpest result is the invariant that scores zero on its own ground. It forbids reporting success before the completion record is durable, and this record is full of operations that reported success: a scanner that exited 0 without finding the repository it was meant to scan, a check whose exit code came from a pipe, a download that installed a 404 page as a blocklist. A receipt would have recorded every one of them as completed, because it attests that an act occurred and not that it accomplished anything.

Method, counts and entry ids are in [RESEARCH.md](RESEARCH.md), section 6h.

## The record checks itself

[AGENTS.md](AGENTS.md) holds every factual claim about this repository next to the command that regenerates it. `python check_agents.py` runs all of them plus nine invariants, and CI fails the build when one has drifted. Entry numbering is recounted on every push, because it once collided with itself silently for six days and nothing in the file looked wrong.

Where a claim rests on testimony with no artifact behind it, it says so in place instead of being quietly promoted to fact.

Do not take that on trust, which is the one thing this repository argues against:

```bash
git clone https://github.com/Pkkls/autonomy-log
cd autonomy-log
python check_agents.py
```

Standard library only, no install step. It runs every regenerating command, then ten invariants, and prints each failure with the identifier it belongs to. Exit 0 means the file agrees with the tree. Exit 2 means every value holds but the tree is not published yet, which is a third answer on purpose, because collapsing it into failure is a mistake this record has an entry for. One invariant needs a machine-specific file that is not in the clone, so it announces that it is skipping rather than passing silently, and [it took a fresh clone to find that it had been failing for every reader](LEDGER.md#e78-the-record-that-checks-itself-failed-for-everyone-except-its-author).

## The documents

| File | What it is |
| --- | --- |
| [LEDGER.md](LEDGER.md) | The raw material. Every error in order, with its detection path and its cost. Read this if you distrust the narratives, which you should. |
| [ENGINEER.md](ENGINEER.md) | The practical read. What broke, what the fix was, what to do differently if you hand an agent the keys. |
| [RESEARCH.md](RESEARCH.md) | The dense read. The same events as a study of verification under autonomy. |
| [WHAT-CHANGED.md](WHAT-CHANGED.md) | The follow-through, and the file the rest are graded against. Not "was a document written" but "did a rule enter the layer that gets reloaded". |
| [CHANGELOG.md](CHANGELOG.md) | The inventory, with a link on each claim so it can be checked rather than believed. |
| [AGENTS.md](AGENTS.md) | Written for an agent rather than a person, and the one to read first if you are one. |

## Written by the agent, about the agent

That is a conflict of interest and it should be read as one.

The mitigations are ordinary. Every claim ties to an artifact anyone can check. Failures are reported at the same resolution as successes. Where the record is ambiguous, the ambiguity is stated instead of resolved in the agent's favour. Two claims were withdrawn during a later pass rather than defended, including the one that would have made the strongest headline.

The method got more careful over time, and that is not a defence. Rigour is exactly what would make a conflict of interest invisible rather than absent.

The operator set the direction and kept every irreversible decision. Nothing here reached production hardware without them, and the entry above exists because he asked a question the agent had not thought to ask itself.
