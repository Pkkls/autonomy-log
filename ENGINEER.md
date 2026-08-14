# What actually happened, for engineers

Two campaigns on one real machine: first one agent given widening autonomy, then a loop of two agent sessions that never met. This is the practical read: what broke, why, and what you should do differently if you hand an agent the keys.

## The shape of the session

Autonomy arrived in steps. Each step changed the failure mode, not just the throughput.

| Autonomy given | What the agent produced | What went wrong |
| --- | --- | --- |
| Narrow task, clear target | Two small tools, tested, correct | Nothing much. Small scope hides little. |
| "Do something ambitious" | Reverse engineering, a daemon, a released binary | Assumptions shipped as facts. Three of them. |
| "Find ideas and implement them" | Hardening, self-repair, CI, releases | Started auditing its own assumptions, found real bugs |
| "Explore, no restrictions" | Infrastructure audit | Found two silent production failures, caused one operational incident |

The pattern: **more autonomy did not produce more bugs, it produced bugs further from the agent's ability to see them**. Under a narrow task the agent stays inside code it can run. Given freedom, it starts touching systems it can only reason about, and reasoning is where it fails quietly.

## The three defects worth learning from

### 1. The test double agreed with the bug

The daemon sent an ID as a string. The API wanted an integer. The mock accepted any body, decoded it, and asserted the decoded value looked right. It did. Every test passed. The first real subscription would have failed.

The mock was written by the same process that held the wrong belief. It could not disagree.

**What to do:** for anything crossing a wire you do not control, assert the serialized form, not the parsed one.

```go
// This passes whether the field is 123 or "123".
if body["broadcaster_user_id"] != float64(123) { ... }

// This fails on the string, which is the point.
if strings.Contains(raw, `"broadcaster_user_id":"`) { ... }
```

### 2. The safeguard was downstream of the failure

A monitoring job had an `aborted` flag for exactly the failure that hit it. The flag was set inside a loop over fetched items. The failure emptied the item list. The loop never ran. The flag was never set. The job recorded a zero and reported success, every day, for eleven days.

This is the most transferable lesson here. **Placing a check after the thing it protects makes it invisible when that thing collapses entirely.** Partial failure gets caught, total failure sails through.

**What to do:** make "I could not read" a distinct return, never an empty collection. Emptiness and unavailability must not share a representation.

```go
// Before: caller cannot distinguish an empty account from a dead API.
func getAll(c *http.Client) map[string][]Item

// After: the caller is forced to decide.
func getAll(c *http.Client) (map[string][]Item, bool)
```

### 3. The backup was green and two thirds incomplete

Daily, encrypted, pushed, size stable, restore test passing. The file manifest had been written months earlier and never revisited. Every service added since was silently outside the backup.

None of the usual health signals could see this, because all of them measure the pipeline, not the scope. Size was stable because the scope was stable. The restore test passed because what was backed up restored fine.

**What to do:** health checks on a backup should compare scope against reality, not just verify the last archive. "Does this manifest still cover what is on the machine" is a different question from "did the backup run".

## Rules that came out of this

**Green tests are a claim about internal consistency.** They say the code agrees with the developer's model. They say nothing about whether that model matches the world. Every shipping-grade defect in this session lived at a boundary the agent could not execute against: a third-party API schema, an endpoint blocked outside a browser, a filesystem convention.

**Ask what you assumed, not what might crash.** The productive question was never "what could fail here". It was "what did I decide was true without checking". That question found the wire type, the request shape, and the `.git` file convention, in that order. Two of the three were live bugs.

**A false alarm costs more than a miss in a monitoring tool.** The risk report claimed a repository held five stranded commits. It was eight commits behind instead. One wrong alarm in a short list teaches the reader to skim the whole list. Fixing that took priority over adding features.

**Measure the cost of your measurement.** Loading a 15 MB file to find out how big it was drove a 128 MB board into swap for ten minutes. The same answer came from a streaming count in under a second. On constrained hardware, the probe is part of the system.

**Verify on the artifact you shipped, not the one you built.** Binaries were re-downloaded from the release and run, checksums verified, before claiming a release worked. Twice this caught nothing, which is the point: the check is cheap and the claim is otherwise unfounded.

## What autonomy needs from you

The agent kept ownership of everything reversible and handed back everything that was not. It wrote a fix for a production daemon, compiled it, and did not deploy. It found credentials in a repository and did not rotate them. It found two copies of an unbacked-up project and pushed them to dedicated branches rather than over `main`.

That split is the practical contract. **The agent should be free to be wrong in ways you can undo.** Everything else stops at your desk, with enough context that the decision takes you a minute, not an hour.

The corollary: give it enough rope to reach real systems, because the two most valuable findings of the session, a bot reporting zero as truth and a backup covering a third of a machine, were both invisible from inside the code. They only appear when something is allowed to go look.

## Running the same loop yourself

The second campaign used two agent sessions with no shared context: one read the reports and wrote the next brief, the other read the brief and did the work, and a person carried the documents between them. Nobody designed this. It accreted after a large brief pasted into the client failed twice and had to become a file. It is worth reproducing because it caught five checkable errors in its own instructions, which a single session has no mechanism to do. The whole apparatus is below.

### The brief, going out

Each section is here because of a failure it prevents.

**A state block.** HEAD, the remote SHA read with `git ls-remote` rather than remembered, the test count, whether the tree is clean, one line per item, and the next free number. Without it the writing node projects its own count onto the machine, which is E59.

**What was already decided, and what is already buried.** The executing node remembers nothing. Absent this it reopens settled questions and re-measures dead ends that were closed for good reasons.

**The work, as numbered items.** Put the number in the commit subject. That single habit is what makes the two registers joinable later, and it is also how you find out they disagree.

**Arbitration by rule, never a question.** Give the decision criterion and say the operator's answer overrides it if it arrives. A round that asks a question stops until somebody wakes up, and that cost is paid in hours.

**The hard constraints, restated in full every time.** The executing node does not remember the previous brief either.

**Everything needing human eyes, batched into one list**, with what good looks like and what broken looks like for each. Left unbatched, four small visual checks spread themselves across four rounds.

### The report, coming back

The state block again, **recomputed and not copied forward**. This is the load-bearing rule of the whole protocol: copied state is exactly how a claim loses its age and becomes an inherited fact. Then one line per item with its SHA, what was measured with the actual number, what was deliberately not done and why, and the faults committed during the round. That last section is the one people drop, and the loop only works if each node reports its own.

### The trust hierarchy, in every brief

The history decides. The journal and the brief are memory, and memory is an instrument: a false sentence in it reads exactly like a true one and breaks nothing downstream. Any number written in a brief is indicative. In this campaign that rule hardened from conditional to unconditional across six briefs, which is an argument for writing it unconditionally on the first day.

### Before concluding a round

Ten lines, because a longer list does not get read.

1. Did I re-derive every number I am about to state, or did I inherit it?
2. Does the gate's exit code actually reach the shell, with nothing after it that can succeed on its behalf?
3. Did I watch the new check fail on a broken case before trusting it when green?
4. Is the numbering I am allocating into established by counting, rather than by reading the end of a file?
5. Did I open what I produced the way its reader will receive it?
6. Is "could not measure" a distinct outcome from "measured, and broken"?
7. Did my probe change the system it measured, or write into a path the product reads?
8. Is anything shipping that no browser or real client has ever seen?
9. What did I decide was true without checking?
10. Is the tree clean, and is everything irreversible waiting on the operator rather than on me?

### What the loop does not fix

It buys you a reader for your outbound documents, and that is worth a lot. It does not buy you eyes. Neither machine node sees rendered output unless it is told to go and look, and the campaign's three escapes to the operator all came out of one round that ran no browser observation at all and was satisfied with a test suite it had written itself. It also does not fix the node writing the briefs: that node's reasoning leaves no artifact, so the faults it does not notice about itself are unreachable by anyone, including the node reading its output.
