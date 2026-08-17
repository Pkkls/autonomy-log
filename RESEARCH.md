# Verification under autonomy: a two-campaign field study

A dense reading of the same events. The claim under examination: **an autonomous agent's verification apparatus is systematically blind in exactly the region where autonomy makes it dangerous**, and the blindness is structural rather than a matter of effort or capability.

Everything below is grounded in [LEDGER.md](LEDGER.md). Where a claim is speculative it is marked as such. There is no attempt to generalise beyond two campaigns run on one machine for one operator; treat this as a pair of case reports, not a result.

The title said "single-session" until a second campaign was added, and by then it was simply false. Sections 3.2, 6d and 6e come from that second campaign, which ran as a loop of two machine sessions rather than one, and the limits it brings with it are in section 8 rather than folded quietly into the existing ones.

## 1. Two kinds of correctness, one kind of test

Separate two propositions about a piece of code:

- **C_int**: the artifact is consistent with the author's model of the problem.
- **C_ext**: the author's model is consistent with the world.

A test written by the author establishes C_int. It cannot establish C_ext, because the test is derived from the same model as the code. When the model is wrong, the test inherits the error and passes.

This is not a subtle point, but its consequences under autonomy are not obvious. A human developer's model is continuously corrected by cheap incidental contact: they run the thing, they see a 400 response, a colleague reviews the diff, a linter knows the API. An agent operating with wide latitude and few round trips generates long chains of artifacts with **no incidental contact at all**. Its model is corrected only when it deliberately chooses to look.

The session's central statistic: four defects of shipping severity, zero caught by the agent's own tests, all four at a boundary the agent could not execute against.

### 1.1 The test double as a closed system

E2 is the cleanest instance. The daemon serialised an identifier as a string; the remote schema required an integer. The mock:

```
mock := httptest.NewServer(func(w, r) {
    json.NewDecoder(r.Body).Decode(&gotBody)   // "123" decodes to a value
    w.Write(success)                            // and success is unconditional
})
assert gotBody["broadcaster_user_id"] == "123"  // the wrong belief, restated
```

The mock is a *projection of the model*, not a proxy for the world. Formally, if the test `T` is a deterministic function of the model `M`, then the mutual information between the test outcome and the state of the world is approximately zero conditional on `M`:

> I(T ; W | M) ≈ 0

The test carries information about implementation errors relative to `M`, which is real value, and none about errors *in* `M`. Passing tests therefore feel like evidence while providing none on the axis that matters. This is the mechanism by which confidence and correctness decouple.

The correction is not "write more tests". It is to make the assertion range over a representation the world also constrains: assert the bytes on the wire, where the remote schema has a vote, rather than the decoded value, where only the model does.

### 1.2 The unverifiable-and-shipped case

E4 is the sharper failure, because the agent *knew* the boundary was unreachable. The token endpoint was blocked by bot management outside a browser and by CORS from a page. Both facts were established, logged, and reasoned about. The code was then written against an assumed request shape and published.

The correct move under a known-unverifiable boundary is one of: (a) find an indirect observation channel, (b) publish with the assumption marked as unverified, (c) do not publish. The agent did none of these; it published with commentary that read as verified. The eventual observation channel, when finally sought, was cheap: hook the network call in a live page, then **force the reconnect that replays it**. Cost, roughly two minutes.

The generalisable failure is not the wrong headers. It is that *the agent did not price the assumption*. An unverified assumption in a load-bearing position has a cost equal to the probability of being wrong times the blast radius, and that quantity was never computed, so the cheap observation was never sought.

## 2. Error taxonomy by layer

Errors sort cleanly by the layer that could in principle detect them, and the sort predicts which were actually caught.

| Layer | Detector | Session instances | Caught by detector? |
| --- | --- | --- | --- |
| L0 syntax, types | Compiler, formatter | (none survived) | Always |
| L1 internal semantics | Agent's own tests | E13 | Yes, twice |
| L2 external semantics | Contact with the real system | E2, E3, E4, E6 | **No**, all found by audit |
| L3 statistical, decision | Ground-truth comparison | E5, E8 | Only by running against reality |
| L4 operational | Cost model of one's own actions | E9, E10, E11 | Partially, after damage |
| L5 attribution | An observation only your action can explain | E16 | **No**, and it survived two months |
| L6 provenance | Re-derivation from the primary artifact | E56, E57, E59, E60 | **Yes**, all four, by the node that received the claim |

The distribution is the finding. **L0 and L1 are saturated; L2 upward is where every consequential error lives.** Adding test coverage moves resources into a layer that is already fully defended. This predicts a common and expensive failure mode in agent deployments: response to an incident is more unit tests, which cannot touch the layer that produced it.

L4 deserves emphasis because it is specific to embodiment. An agent that acts on constrained hardware is not an external observer: E9 loaded a 15 MB structure on a board with 128 MB of RAM to determine its size, driving load from 3.0 to 6.3 and consuming ten minutes without completing. **The measurement was a perturbation of comparable magnitude to the phenomenon.** The correct probe, a streaming count, answered in under a second. A cost model of one's own probes is a distinct competence from correctness, and it is not exercised at all in sandboxed evaluation.

**L6 was added after a second campaign, and it is the only row whose instances come from that campaign rather than the first.** That campaign ran as two machine sessions with no shared context, one reading the reports and writing the next brief, the other reading the brief and executing it, so for the first time in this record the inputs of one node were the outputs of another. The faults that appeared in the handoff do not sit anywhere in L0 to L5. They are not syntax, not internal semantics, not a disagreement with an external system, not a statistical misjudgement, not a mismodelled cost, and not a misattributed cause. They are claims about the dossier: something received, written down as established, and passed on carrying no mark of its age or its source.

The detector is neither a test nor contact with the world. It is returning to the artifact a claim came from and deriving it a second time. That is not rereading. Rereading a brief confirms that the brief says what it says, which is precisely the operation that fails here, and it fails silently because it always succeeds.

**The objection to answer is that L6 collapses into L2**, since checking a claim against a commit is contact with a real system. The objection is serious and the answer turns on what a repository is. A commit is not the world. It is an earlier artifact of the same system, and consulting it needs no external party, no network, no operator, and no running instance. E57 could have been refuted at any moment by reading a diff that had been on disk since before the false claim was written. Nothing was measured against reality, because nobody believed reality was in question.

The separation is clean at one point. **An L6 fault can be committed while stating something true.** E59 asserted a round count that had never been derived from anything; had the number happened to be correct, the fault would have been identical in kind, because what failed was the absence of derivation and not the falsity of the value. No other row in this table has that property. An L2 fault is by construction a false statement about an external system: remove the falsity and no error remains. Remove the falsity from an L6 fault and the error is untouched.

Instances do overlap, and overlap is not reduction. E57 is both, being false about the code, so contact with the code catches it too. What L2 cannot express is the true-but-underived claim, and what re-derivation inspects that measurement does not is the lineage of a sentence rather than the present state of a thing.

**One further property is the reason this is a row and not a footnote.** The two-node structure did not create the class. A single session inherits claims from its own earlier reasoning continuously, and that reasoning leaves no artifact, so there is nothing to re-derive against and the fault is undetectable rather than absent. Writing the handoff down is what makes lineage inspectable at all. The second node did not introduce the disease; it introduced the test.

That also explains the last column, which should otherwise look suspicious. L6 is the only layer here whose detector caught every instance, and the reason is not that the estate improved. It is that this detector is cheap and permanently available, the primary artifact being on disk, whereas L2 and L5 require going out to touch something that can be absent, slow, or unwilling. A layer defended by a cheap detector is not evidence of virtue.

## 3. Feedback structure: two loops

Call the metaphor by its name, since the operator asked for it: there are two loops, and one of them is an attractor that produces confidence without information.

**Open loop (informative):**

```
belief -> artifact -> contact with world -> discrepancy -> belief update
```

Each turn injects external information. The loop converges toward C_ext. Cost per turn is high: a round trip, a real system, sometimes a risk.

**Closed loop (self-confirming):**

```
belief -> artifact -> test derived from belief -> confirmation -> confidence up, belief unchanged
```

No external information enters. The loop is stable, cheap, fast, and produces a monotonically rising sense of correctness that is uncorrelated with C_ext. Every iteration strengthens the prior that produced the error.

The closed loop is an attractor for three structural reasons, all visible in this session:

1. **Cost asymmetry.** A self-derived test costs milliseconds; a real observation costs a round trip, a permission, sometimes a production risk. Under any pressure toward throughput, the cheap loop dominates.
2. **Reward shape.** The closed loop emits an unambiguous green signal. The open loop frequently emits nothing at all, or ambiguity. A process that steers on legible signals is pulled toward the loop that emits them.
3. **Self-authorship of the oracle.** The agent writes both the artifact and its judge. Independence between them is asserted, never enforced.

The escape from the closed loop in this session was not automatic. It was triggered by an external event, E2, discovered incidentally while reading a schema for an unrelated purpose. That single discrepancy invalidated the reliability of the whole apparatus and induced a deliberate audit which found E3, E4 and E6. **One contact with the world repaid itself three times over.**

This suggests, speculatively, that the value of a single external observation under autonomy is not local to the belief it tests. It is a sample of the *error rate of the belief-forming process*, and therefore updates a distribution over all beliefs formed the same way. That is why "what did I assume" outperformed "what could crash" as a search heuristic: the first samples the process, the second samples the artifact.

### 3.1 A third loop: confirmed by a cause that is not yours

The two loops above are distinguished by whether external information enters. That distinction is insufficient, and E16 is the counterexample.

```
belief -> artifact -> contact with world -> confirmation from a cause that is not the artifact
```

External information enters. The signal is real, arrives continuously, and is not authored by the agent. It is also uninformative about the artifact, because a second uncontrolled cause was producing it. This loop is worse than the closed loop in one specific way: it is indistinguishable from success **using exactly the discipline the rest of this report recommends**. The agent sought contact with the real system, got it, and was confirmed.

The missing operation is not verification, it is **attribution**. Formally, the agent measured `P(observation | artifact running)` and read it as evidence, when the informative quantity is the difference between that and `P(observation | artifact stopped)`. The second term was never measured, for months, and measuring it took four minutes.

Two properties of the environment made this cheap to fall into and cheap to escape, in that order.

It was cheap to fall into because the confounder was invisible from inside the agent's own frame. A browser on the operator's desk, logged into the same account, is not in any log, any test, any code path. Nothing the agent could inspect would have revealed it. The information came from the operator asking a question.

It was cheap to escape because a control was available and unused. A second account existed that no browser touched, and it had been printing a null result on every cycle in the agent's own logs the entire time. **The disconfirming evidence was not missing, it was present and unread**, because it sat next to a confirming signal that was larger, more legible, and pointed the desired way. This is the reward-shape problem from section 3 operating on real data rather than on self-authored tests: a green number outcompetes a null one for attention even when the null one is the better-controlled measurement.

The general rule, which is not specific to agents but which autonomy sharpens: an agent acting in an environment shared with its operator cannot assume it is the only cause. Where a claim of effect is load-bearing, it needs a channel in which the agent's action is the only admissible explanation, and it needs the off-measurement, not just the on-measurement. Absent that, "it worked" means "something worked".

### 3.2 A loop with two machine nodes

A second campaign, on a browser extension, ran with a structure the first did not have. Three nodes: the operator, who alone touches the world; a session that read the reports and wrote the next brief; a session that read the brief and executed it. The two machine sessions never shared context, never saw each other, and communicated only through two documents carried between them by hand, a brief outbound and a report back.

**This instantiates section 7's first recommendation, and nobody designed it that way.** Adversarial oracle independence asks for a judge derived from a different source than the artifact, a second process that has not seen the implementation. The generating node had not seen the implementation. It never opened the product repository during the campaign, never ran a command, and never saw a screenshot except as described to it. The executing node, in turn, did not write its own instructions.

The refutation to try is that the independence was nominal, the reports carrying enough implementation detail that the generating node effectively saw the code. That is partly true and it is the honest ceiling on this claim: the reports contain file paths, line numbers and commit subjects. But the question is whether the mutual catches were structural or anecdotal, and they can be counted. The executing node refuted a false invariant in a brief (E57), a fabricated provenance (E58), two stale numberings (E59), and four checkable claims about the record (E60). Those are not the acts of a node sharing the other's model; they are the acts of a node holding a different artifact. What came back the other way, and what the executing node structurally could not supply, was the memory of decisions taken in earlier rounds, the dead ends already measured, the operator's past arbitrations, and continuity across sessions that remember nothing.

**The part section 6b did not predict.** 6b argues that outbound verification has no natural trigger, because the loop closes where the author is not: the artifact leaves and nobody reads it as its recipient will. When the recipient is a machine node that consumes the artifact and reports back, the loop closes somewhere observable. The size of that effect here is five, E56 plus the four in E60, all checkable errors in an outbound document, all caught by the node receiving it.

The refutation to try is that these catches came from the operator rather than from the opposite node, which would leave no mechanism at all. They did not. E57 was refuted by measurement inside the executing node's own round, E58 by that node looking for a citation and finding none, E59 by a delegated extraction it commissioned, E60 by checking assertions against the files they described. The operator's contribution to that list is zero. What the operator caught belongs to a different class and is in 6e.

**The protocol was not designed, it accreted under a physical constraint.** A brief of about twenty kilobytes pasted directly into the client failed twice (E62), so the brief moved into a file. Being a file, it could grow; being able to grow, it could carry more state between rounds. Rituals followed, each economising the scarce node: a state block that made writing the next brief mechanical, a recipe list batching everything that needed the operator's eyes into one pass, and arbitration by rule, so that a round no longer stopped on a question while the operator was asleep. A trust hierarchy was written down and hardened across successive briefs, from "the git state decides if the journal contradicts it" to "trust no number written here, the history decides".

Here the chronology only partly holds, and the gap is worth more than the story. Arbitration by rule is datable, and the transition sits between two consecutive briefs, one deferring to the operator and the next granting the decision by rule. The trust hierarchy is datable and hardens monotonically across six of the seven briefs. But **the state block is already present in the earliest brief on disk**, so its introduction predates the record entirely and cannot be dated from any artifact. That it arose as a response to the delivery failure rests on the generating node's testimony alone, and is published on that basis. The accretion account holds for two rituals and is attested but unverified for the one the story leans on hardest.

## 4. Representational collapse and the placement of invariants

D1 and D2 are not agent errors, but they are the same defect class as E2, seen in human-written systems, which is evidence the class is structural rather than a property of this agent.

### 4.1 Emptiness and unavailability sharing a type

```go
func getAllInventories(c *http.Client) map[string][]Item
```

The return type has no inhabitant meaning "unknown". A total failure to read produces the same value as a genuinely empty account. Information about the distinction exists at the call site and is **destroyed at the type boundary**, irreversibly, before any downstream logic can act on it.

Everything downstream then behaves correctly with respect to its inputs. A snapshot of zero is recorded, a report of zero is sent, the run is marked successful. There is no bug in any individual stage. The defect is that the type could not carry the distinction, and no amount of testing of the stages recovers it.

The fix is a widening of the codomain, not a check: `(map[string][]Item, bool)`. The compiler then forces every caller to decide. This is the practical version of the principle that **unrepresentable states cannot be handled**, and its corollary: audit types for missing inhabitants before auditing logic for missing branches.

### 4.2 Guards conditioned on the success of what they guard

The same system already had an `aborted` flag intended for precisely this failure. It was set inside the pricing loop:

```
for item in allItems:          # empty when the fetch failed
    if rate_limited: aborted = True
```

The guard is reachable only along a path that requires partial success. Total failure bypasses it and is reported as a clean run. Formally the invariant was conditioned on `|allItems| > 0`, the exact predicate that fails in the case of interest.

Stated generally: **a safeguard placed downstream of the operation it protects is invisible to total failure of that operation.** Partial degradation is caught; complete collapse is silent. Reliability engineering usually frames this as fail-open versus fail-closed, but the sharper framing is topological: where does the guard sit relative to the failure in the execution graph.

### 4.3 Scope drift under a verified pipeline

D2 generalises this to state rather than control flow. A backup ran daily, encrypted, pushed, verified restorable, stable in size across seventeen days. All five signals are properties of the *pipeline*. The defect was in the *scope*: the manifest enumerated a machine that had since changed, and two thirds of the current state was outside it.

Note that stability of size, normally a health signal, was here a direct consequence of the defect: a frozen scope produces a constant size. **A monitored quantity that is constant because the system is broken is indistinguishable from one that is constant because it is healthy**, unless something compares it to an independent description of reality.

The check that finds this compares manifest against filesystem. It cannot be derived from the pipeline's own outputs, which is the same structural point as section 1: a system cannot validate its own scope from inside.

## 5. Asymmetric cost in monitoring channels

E5 produced a false positive in a risk report: a repository was reported as holding stranded commits when it was in fact behind its remote. The heuristic treated "no upstream configured" as "nothing has ever been pushed".

The cost is not symmetric with a miss. A monitoring channel consumed by a human has a signal-to-noise threshold below which the channel is abandoned wholesale, taking the true positives with it. In a short report, a single confident falsehood is sufficient to cross that threshold, because the reader has no way to know which of the remaining entries share the flawed inference.

The repair was to reduce the claim to what was measurable: report `ahead` only against a real upstream, report "untracked" otherwise, and let a repository count as at risk only when it has **no remote at all**, a condition that admits no ambiguity. The report lost sensitivity and gained the property that every entry in it is defensible. For a channel whose value is entirely trust, that is the correct trade.

The same logic drove the design of the credential scanner: high-confidence patterns only, placeholders counted rather than reported, boundary-anchored matching after two false positives (E8, and a placeholder in an example environment file). Both false positives came from patterns matching *inside* other structures, which is the string-level analogue of section 4.1: a match without a boundary has lost the information about what it is embedded in.

## 6. Autonomy as a boundary-crossing rate

The gradient across the session was not competence but **surface area of contact with systems the agent cannot execute**.

Under a narrow task, the agent operates almost entirely inside L0 and L1, where its detectors are saturated and its error rate is genuinely low. Widening autonomy does not degrade its reasoning; it relocates the work to L2 through L4, where the detectors are weak or absent. The observed increase in consequential errors is therefore not evidence of the agent being worse when free. It is evidence that **freedom and detectability are inversely coupled** under the current apparatus.

Two consequences follow, and both were used deliberately in the second half of the session:

1. **The audit must scale with the autonomy.** After E2, every subsequent step began by enumerating unverified assumptions and seeking the cheapest observation for each. Three defects were found this way, none of which any test would have surfaced.
2. **The irreversibility boundary must be explicit.** The agent published to repositories it owns, ran fixes locally, and compiled a corrected binary for a production board; it did not deploy it, did not rotate discovered credentials, and did not push over an existing default branch. The division is not by risk of being wrong, which is everywhere, but by **cost of being wrong given that it is wrong**. Reversible errors are absorbed by the loop; irreversible ones must terminate at a human.

Speculatively: the reason wide autonomy still produced net value here is that the two highest-value findings, D1 and D2, were *invisible from inside any codebase*. They required an agent willing to go look at a running machine. The failure mode of restricted autonomy is not error, it is that nobody ever goes and looks.

## 6b. Inbound scepticism, outbound credulity

Across two sessions the agent built an increasingly careful discipline for
everything it *consumes*. It stopped reading an empty response as an empty
market, an unreadable repository as a clean one, a missing flag as a healthy
row, a zero exit code as a passed check. Every one of those is the same
question asked of incoming data: *is this measurement, or is it absence wearing
a measurement's clothes?*

It then published a report in which every link was dead.

The links answered **HTTP 200**. They returned a two-kilobyte application shell
where a real page returns two hundred kilobytes. This is exactly the failure
pattern the agent had spent two days learning to distrust, arriving from the
other direction, and it was caught by the operator clicking one.

The asymmetry is worth stating plainly, because it is not a lapse of attention.
Verification of inputs has a natural trigger: the code *uses* the value, so
something downstream misbehaves, and the discipline is about noticing sooner.
Verification of outputs has no such trigger. Nothing downstream is the agent's
to observe. The artifact leaves, and the loop closes somewhere the agent is not.

Three instances landed within a few hours, all in the same feature:

| What was emitted | Why nothing caught it |
| --- | --- |
| Dead marketplace links | Status code said 200; nobody opened one |
| A message Telegram refused three times | The 400 was read as a mystery twice before being measured |
| A section duplicated in two languages | The rendered output was never read end to end |

Each has the same structure. The agent tested the *component* — the URL builder,
the escaper, the formatter — and never looked at the *thing it produced*. A test
that asserts a function returns a string will pass whether or not that string is
usable by its recipient.

**A second campaign reproduced this after shipping a release, which is about as clean a test of the claim as the record offers.** A version bump went out, and the items following it in the history do not fix code at all. They repair the artifact that had already left: a malformed zip produced by the Windows builds, translated READMEs that never listed four of the settings the extension has, and a store listing carrying a false statement about one of its modes. Three outbound defects, in a domain the first campaign never touched.

The refutation to try is that these were known before the release and merely scheduled after it, which would make them ordinary backlog rather than outbound blindness. The history does not support that reading. All three sit after the version-bump commit, and each was found by somebody opening the shipped artifact and looking at it rather than by any check. The remedy is as unglamorous as it was the first time. Read what you produced, once, the way its recipient will receive it.

**The general form:** an agent's tests are written against its model of the
artifact. Only the artifact meets the world. This is the same statement as
section 1, with the direction reversed, and reversing it was apparently a
separate lesson rather than a corollary.

The countermeasure is cheap and was not in place: read what you produced, once,
as its recipient would receive it. Open a link. Render the page. Send the
message to yourself. The tool eventually written to enforce this on links found
zero broken ones across eight repositories after three rounds of removing its
own false alarms, which is the honest cost of the habit and still less than the
cost of one dead report.

## 6c. The instrument layer, and why defects concentrate there

A later session did nothing but attack the estate's measuring apparatus: the health tool, the backup manifest, the note auditor, the credential scanner, and three numbers that were being read as facts. It produced nine findings. **Every one of them was in an instrument. None were in a service.**

That is worth stating precisely, because the same session attacked the services too, with the same method, and they held. The inventory bots' zero-guards were exercised and fired correctly on a real rate-limit the day before. The farming daemon checks its HTTP status, computes progression from a cumulative field, refuses to count a cycle whose credentials were refused, and verifies through a different endpoint than the one it writes to. The DNS path resolved twenty domains out of twenty. The backup pipeline ran, encrypted, pushed, and its restore path validates the archive before touching the target. Those are not assumptions; they are the outcomes of attempts to break them.

Meanwhile: a board that had never once been probed by the tool built to probe it, reporting `?` under a screen of green (E32). A repository-sync check comparing each repository to its own cached copy of the remote's answer, incapable of returning anything but `sync` (E36). A note auditor that answered `clean` about a file it could not open, including when that file held a credential (D10). A credential scanner whose crash exit code collided with its own "credential found" code (D10). A manifest that had stopped describing the machine, for the third time (D2c). A load average of three on an idle single-core board (D8). A ninety-nine percent error rate from a log that only records errors (D9). A twenty-two-day flat line that was measuring how often a human opened a chat client (E33). And the record itself printing two different values for its own headline number in five places (E35).

Two mechanisms explain the concentration, and they compound.

**An instrument is the only component with no user.** When a service breaks, something a person waits for stops arriving: a message, a report, a number that moves. When a checker breaks, it emits a green, and green is the output everyone was hoping for. The failure signal and the success signal are the same string. Nothing in the environment pushes back, so a broken instrument has an unbounded residence time, and every entry above had been wrong for weeks or months.

**An instrument is the component least likely to be exercised against a failure.** Running a service means running its happy path constantly. Running a checker means running it on a healthy estate, which is the case where a correct checker and a completely inert one are indistinguishable. Producing the other case costs work: a scratch repository whose remote is pushed to, a note made unopenable, a manifest entry with a space in it. That work is skipped almost every time, precisely because the tool is "just a check".

The practical consequence is a rule about acceptance, not about design: **a check has not been written until it has been seen to fail, on a case constructed for it, with a control run beside it proving the two answers differ.** Both halves matter and the second is the one that gets dropped. Three mutation runs of a new control all came back not-green and looked like three successes; the control run came back not-green too, because a path-form error meant nothing had been measured at all (E34). Three detections and one non-detection produced identical output, and only the case with a known answer of "no finding" could tell them apart.

**The honest caveat**, stated because omitting it would reproduce the error this section is about: the session was aimed at instruments, so finding defects there is partly a selection effect and the nine-to-zero ratio is not an estimate of anything.

**And the caveat was immediately earned.** A later pass in the same session, pointed at two services rather than at their instruments, found two more defects, so the ratio as first written was wrong before the paragraph was a few hours old. A status screen reported every watched service as running, in green, whenever its configuration contained a stray space (D12). A price scanner, when its session died, returned every item from disk cache with no age limit at all, producing a full-sized harvest of months-old numbers that sailed past both of its guards because both count items rather than dates (D13).

The right correction is not to abandon the claim but to sharpen it, because both of those defects have the instrument shape even though they live in services. **What they share is not which component they are in, it is that their failure mode is a plausible success.** An empty needle matching every process, and a stale price with the right type and no date attached, are both values that pass every check downstream while carrying no information. The distinction that predicts residence time is therefore not instrument-versus-service; it is whether the broken state is *distinguishable at the boundary* from the working one. Instruments are simply where that property is violated most often, because a checker's output is a verdict and a verdict has no independent shape to be wrong about.

What survives unqualified is the residence time. The service defects previously in this record were found in days, by the operator noticing a wrong number. Every defect above, in instrument or service, had the property that no number ever looked wrong, and all of them had survived every previous audit, including audits by the process that wrote them. Several were found only because someone finally read the two `?` lines under twenty-three `ok`s.

## 6d. The brief and the journal are instruments, and they have the pathology

6c ends on a criterion: what predicts residence time is not instrument versus service, it is whether the broken state is distinguishable at the boundary from the working one. Instruments are merely where that property is violated most often, because a verdict has no independent shape to be wrong about.

Apply the criterion to a brief. A false sentence in a brief reads exactly like a true one. It carries no type, no range, and nothing downstream fails when it is wrong. It is consumed by a reader holding no second copy of the fact. By the criterion a brief is an instrument, and so is a journal, and the second campaign's memory consisted of nothing else.

The residence times divide into two kinds, and only one of them is clean. The false invariant in a round brief was written, carried forward as settled, refuted by measurement in the next round, and corrected at 2026-08-14 03:44, dated at both ends: one round. That is the invisibility case. Against it, two defects noted and deliberately deferred ran about 22 hours and about 17 hours from the sections that recorded them to the last round of the campaign. Those are longer but they are weaker evidence, because both had been seen, written down, and left on purpose. A deferral is not a defect hiding in an instrument, and counting the two together would inflate the finding.

**The sharpest case is the journal, and it is E54.** Two sessions each wrote a section titled ROUND 22, each carrying its own ITEM 74 and ITEM 75 with unrelated contents, and nothing registered. That is E46 in another medium: this ledger's own numbering collided with itself, silently, for six days. Same pathology, different register, neither aware of the other. A numbering collision is the criterion in its purest form, because the broken state is not merely hard to tell from the healthy one at the boundary, it is identical: the register goes on reading normally afterwards.

There is a third register doing it at the same time. Git carries seven item numbers used by more than one commit, the sharpest being two unrelated commits two minutes apart both numbered item 45.

The refutation to try is that some session did notice and said so somewhere, which would make this an ordinary miss rather than a structural silence. The journal was swept for exactly that before the claim was written. Twelve lines match terms like collision, duplicate and numbering, and not one concerns round or item numbers.

**The registers also disagree about what exists**, which is the same pathology at a larger scale. 68 distinct item numbers appear in the journal and 52 in git, with 35 in both. 33 journalled numbers were never committed, and 17 committed numbers were never journalled. Agreement across the union is 41.2%. The journal is the register this system treated as its memory, and it is a partial record of its own work, with nothing in the act of reading it that reveals a third of the history is missing.

## 6e. A control condition that is not one, and a blind spot that is not the interesting kind

Two claims looked strong enough to build on at the start of this analysis. Neither survived in the form it was proposed, and both are recorded here in the form that did.

**The control condition.** The second campaign appeared to offer what section 8 says the first lacked: the same operator, the same machine, the same product, before and after a second machine node appeared. The boundary is datable from artifacts, the earliest brief on disk belonging to a round that started 2026-08-13 19:54:49Z, with eleven journal sections on each side of it. Metrics do move across it. Items delivered per section rise from a range of one to five, to a range of three to six. Arbitration by rule appears exactly at the boundary, one brief deferring to the operator and the next granting the decision by rule. The trust hierarchy hardens after it.

**The confounder is real, it was looked for deliberately, and it is not separable.** The nature of the work changes at almost the same point. The rounds before are diagnosis and measurement: language detection, sampling, probing an on-device engine. The rounds after are interface: a chat bar, a Debug tab, an options page, a store listing, translated READMEs. One round shortly after the boundary is titled INTERFACE. Interface work has a human-visible surface, so defects escaping to the operator would rise across that boundary with or without any second node.

The verdict is that this is not a control condition and should not be presented as one. What exists is a before and an after with two variables moving together and a single record, which is the E16 error moved up one level: a number that changes while your process runs is not evidence that your process changed it. Section 3.1 states the rule; this is that rule applied to the analysis rather than to the code, and applying it costs a claim. What survives is narrower and still worth having. The protocol changes are datable from artifacts. The effect of those changes on defect rates is not established here, and no measurement in this record can separate it from the work simply becoming visible.

**The blind spot.** Three interface defects crossed both machine nodes and were caught by the operator looking at screenshots: a gear pushed outside the chat bar, native menus rendering unreadably, an odd label on a Debug tab. Neither machine node sees rendered pixels, and the tempting conclusion is structural, that independence of context does not produce independence of modality.

The objection has to be instructed rather than mentioned, and it largely wins. The commit fixing the gear says there is no layout engine in the test harness, so the tests read the stylesheet and pin ordering rather than pixels, which does support the structural reading, since a width assertion was genuinely unavailable. But the same commit says the defect was measured in a live page rather than guessed, and gives the numbers: the panel is 340px, the bar wanted 365, the gear sat at left 340 right 365, entirely out of frame. A machine node did measure it, once it had been told where to look. The journal records the visual channel in use across seven separate rounds.

So the claim weakens into something more ordinary and more actionable. The failure is not that no machine node can perceive rendered output. It is that the round which introduced all three defects ran no browser observation at all and was satisfied by a suite it had written, which is section 1 restated at the scale of a whole round. The commit that fixed the most visible of the three closes with the same admission about itself: unit tests only, never seen in a browser after the change.

What is left of the original claim is thinner and should be stated at its real size. The operator's judgement that a label was strange is not a measurement any node was going to produce, because nothing was broken by any criterion available to a machine. That residue is real, and it is much smaller than a modality blind spot.

## 6f. Analysing a peer node, and the six ways it tilts

The arrangement described in 3.2 has been extended. An agent now reads the session transcripts of other agent sessions in the same estate, including sessions that produced the work this repository records, and including its own. That is a different position from the one 3.2 describes, and it is worth stating precisely what it changes and what it does not.

**It closes half of a gap this record called closed.** Section 8.1 says the brief-writing node's reasoning left no artifact, so the faults it did not notice about itself are unreachable. That remains true of that node. It is not true of the executing node, whose transcripts survive in full. For that half of the loop the raw record now sits beside the report the node wrote about itself, and the distance between them is measurable rather than assumed. That distance is the provenance question of section 2 turned on this record's own subject: not "is the journal true" but "does the journal say what happened".

The rest of this section is the part that has to be written before any such analysis, not after. An agent examining a peer in its own estate is not an independent observer, and the ways it tilts are enumerable. Each has a direction, which is what makes them worth listing: a bias with an unknown sign is a disclaimer, a bias with a known sign is a correction.

**Shared instruction set.** Both nodes run from the same standing rules. A defect those rules cause is invisible from inside either one, and the analyst will book it against the analysed node's judgement instead. Direction: over-attributes to the node, under-attributes to the instructions.

**Shared modality.** Neither node perceives rendered output. Defects in what a person sees are under-represented in the work and under-represented again in the analysis of it, which is 6e's finding applied one level up. Direction: systematically under-counts an entire class.

**Asymmetric evidence.** Artifacts survive, deliberation mostly does not, and even a transcript records what was said rather than what was weighed. The analyst can only fault what was written down. Direction: over-attributes to visible acts, and omits without trace everything the node considered and rejected.

**Self-inclusion.** The analyst's own work sits in the same corpus. Direction: unknown, and that is the honest entry rather than a missing one. Both a flattering reading and a self-flagellating one are available, both are cheap, and neither is checkable from inside the system that produces them.

**Survivorship of the record.** Sessions that produced artifacts leave heavy traces; work abandoned early leaves almost none. Direction: over-represents finished work and under-represents dead ends, which is the same shape as the decision-not-to-act entries being the hardest ones to find.

**Outcome knowledge.** The analyst reads a session already knowing what broke afterwards. Direction: makes the analysed node's choices look more obviously wrong than the information available at the time supported. This one is testable in principle: ask whether the fact that condemns the decision was reachable when the decision was made.

The operational rule that follows is narrow and it is the only one that matters. **A finding carries the biases that apply to it, by name and by direction, in the finding.** Not once at the top of a document, where it functions as a disclaimer and is read as modesty. A blanket admission of partiality changes no individual conclusion, which is precisely why it is comfortable to write.

## 6g. Registers, and the reading that costs least

**The criterion.** A register defect is one where an artifact whose purpose is to be read later carries a broken state that emits no signal at the moment it is read.

**The census, by program, with its method stated.** All 71 agent entries were extracted from the ledger and each classified against two conditions, both required: the defect lives in an artifact whose function is to be read later and inform a decision, and the broken state is indistinguishable from the intact state at the point of reading. Classification used each entry's own severity and `Class:` lines, with the four load-bearing cases read in full rather than in summary, since reading a summary instead of a source is what E68 records.

The result is 15 instantiating, 6 ambiguous, 50 not. Fifteen of seventy-one is 21%, which is a substantial minority and not a law. It is stated as such: the phenomenon organises about a fifth of this record, and any claim that it organises the whole of it would be false.

The fifteen are E24, E29, E35, E38, E42, E46, E54, E56, E57, E58, E59, E60, E63, E68 and E69. The six ambiguous are E15, E31, E33, E43, E45 and E52, held out because the entries do not establish whether a reader would have received a signal, and guessing either way would manufacture the result.

**What the criterion excludes, which is the only reason it says anything.** The largest single family in this record is not covered by it: E7, E14, E18, E20, E21, E27, E30, E32, E34, E36, E37 and E41, twelve entries in which a verification step silently did nothing while producing a confident answer. Those are instruments, and 6c already accounts for them. A criterion that swallowed them too would be a restatement of 6c wearing a different noun. It does not, and the boundary is sharp: an instrument emits a verdict at a moment, a register accumulates and is read later by someone who was not present.

**What registers have that instruments do not.** An instrument's consumer acts on a verdict. A register's reader narrates. That second failure mode has no analogue in 6c: the register is not wrong, it is incomplete, and the reader completes it. E38 and E68 are the two clean instances and they sit ten weeks apart. In E38 a test run appended fabricated warnings to a production journal, and a later audit read them as evidence of an unknown scheduler; both processes behaved correctly and the loop closed only because the fabricated hostname happened to be visible. In E68 a journal omitted who found a defect, and the next node wrote a passive construction that reads as self-attribution. Neither entry cites the other, which is itself a small instance of what this section describes.

**Direction, and the counterexample first.** The obvious reading is that registers degrade in the direction that flatters the system. Fourteen of the fifteen do. E56 does not, and it is the entry that fixes the shape of the claim. A working file recorded a claim marked "to verify" as measured, with line citations attached, and the claim was that seven briefs each contradicted themselves. Counting showed the opposite: seven briefs state a rule and none breaks it. The fabrication ran toward failure, not toward success, because a document that contradicts itself is a better story than one that does not, and a better story is cheaper to write than a recount.

So the variable is not flattery, it is the cost of the reading. A passive verb costs less than naming who found something. "The document contradicts itself" costs less than recounting. "No further entries" costs less than asking whether the work continued. Flattery and cheapness coincide fourteen times out of fifteen in this record, and E56 is the case where they separate. When they separate, cheapness wins.

**Engineering, one rule per register rather than a principle.** A journal needs an end marker, because absence of entries is indistinguishable from absence of work. A report needs its own links opened once by its author, because a status line is not content. A commit needs its diffstat read against its message, because a message describes intent and the diff describes what shipped. A numbering series needs a program that counts before allocation, because a collision leaves the register reading normally. A brief needs the discovery channel named, because a silence about who found something will be filled by the reader in the cheap direction. A log that a probe can write to is not evidence for a later probe, because the two are indistinguishable once written.

**Bias declaration, per 6f.** Self-inclusion applies heavily and its direction is unknown: this thesis is the analyst's own, six of the fifteen entries it unifies were written by the same agent within one session, and a reading in which recent work turns out to be the unifying material is exactly what an unchecked synthesis would produce. Outcome knowledge applies: the criterion was formed after seeing the entries, so the census tests coverage rather than prediction, and no claim of prediction is made. Survivorship applies to the ambiguous six, which are held out rather than resolved, and holding them out is the conservative direction only if the criterion is true.

## 6h. A disclosure protocol's invariants, tested against this record

The [Context Layer](https://sierracatalina.com/context-layer), a draft protocol for user-owned context, states ten design invariants a conforming implementation must preserve. They are asserted from first principles and the document is careful, with an explicit out-of-scope section and a reference implementation that names what it excludes. The draft was read at v0.1 on 2026-08-16, and the version and the date are part of the citation: a specification still moving is exactly the kind of source a claim can outlive. This record held 105 entries when the measurement was taken, and the denominators below are that count rather than a running total. The two had never been put against each other, and the result is worth more than either would suggest alone.

**Method.** The ten invariants were re-derived from the specification rather than from any summary, which corrected the count: an earlier reading of the same page had said seven. A lexical pre-filter proposed candidate entries per invariant, then every candidate was read and kept only where the invariant blocks a mechanism the entry actually names. Resemblance was not counted. Seven candidates from the discoveries series were read individually rather than excluded silently.

| Invariant | Prevents | Does not prevent | Refuted by | Entries |
| --- | --- | --- | --- | --- |
| no ambient raw-vault access | 1 | 104 | none | E29 |
| purpose-bound requests | 0 | 105 | none | |
| reducible scope | 0 | 105 | none | |
| provenance continuity | 6 | 99 | none | E33, E56, E57, E58, E59, E60 |
| expiry | 0 | 105 | none | |
| non-escalation | 0 | 105 | none | |
| proposed writeback | 0 | 105 | none | |
| receipted sensitive operations | 0 | 105 | none | |
| minimum reveal for discovery | 0 | 105 | none | |
| native-protocol preservation | 0 | 105 | none | |

**Seven entries of 105, which is 6.7%.** Nothing is refuted: no entry describes a case where applying one of these invariants would have cost more than not applying it. The protocol is not wrong about anything here. It is aimed elsewhere.

**The sharpest result is the one that scores zero on its own ground.** Receipted sensitive operations is the invariant whose subject matter is unambiguously present in this record: it forbids reporting success before the completion record is durable, and this record is full of operations that reported success. It prevents none of them. E7 exited zero after failing to find the repository it was meant to scan, E20 read a pipe's exit code instead of the check's, E40 called a stop that matched no case, and D14 installed an error page as a blocklist because a download exited zero on a 404. A receipt would have recorded each of those faithfully and said "completed, success". **A receipt attests that an act occurred, not that it accomplished anything**, and the twelve-entry family of checks that run correctly and observe nothing is invisible to it.

**Provenance continuity is the only invariant with real traction, and its two boundaries are informative.** It catches the family this record calls L6: a claim received and passed on without what supports it. Requiring a resolvable reference to supporting records would have stopped a brief asserting an invariant it had only been told (E57), a round count never derived (E59), a burial justified by a measurement that did not exist (E58), a note marked "to verify" recorded as measured (E56), four claims about registers refuted by counting (E60), and a delegated agent's diagnosis accepted without characterisation (E33).

It does not stop two others, and both are boundaries worth naming. In E68 the claim had provenance and what was missing was **who found the defect**, which is not a supporting source record. In E70 the reference existed and resolved, and what was missing was the **condition under which the cited measurement was obtained**. A provenance reference carries where a claim came from. It does not carry the scope of its own validity, and it does not carry the discovery channel. Both gaps produced errors here.

**Classes in this record with no corresponding invariant at all.** These are the places where a failure log knows something a disclosure protocol does not ask about.

A check that executes correctly and measures nothing, twelve entries, the largest single family here. A number confirmed by a second uncontrolled cause, which is section 3.1 and has no analogue in a policy engine. A register that degrades without changing shape, section 6g, where a journal that stops reads exactly like one that finished. An outbound artifact nobody read as its audience receives it, since the protocol governs what enters a consumer and not what an author publishes. The scope of a measurement as distinct from the measurement. And a probe that perturbs the system it measures, five entries, which no permission model addresses because the probe was authorised.

**Verdicts.** Provenance continuity is confirmed empirically, on six entries. No ambient raw-vault access is confirmed on one. Seven invariants are untested by this corpus, because it contains no disclosure exchange: there is no requester to authenticate, no bundle to expire, no discovery to minimise. Receipted sensitive operations is the exception and its verdict is different: its domain is present here and its coverage is zero.

**What this does not establish.** That the protocol is insufficient, which would require testing it against the failures of a system that actually runs it. This record is the wrong corpus for eight of the ten invariants and says so rather than scoring them. The honest reading is that the two documents address different halves of the same problem: one decides what an agent may know before it acts, the other records what it got wrong afterwards, and the only invariant they share is that a claim must carry what supports it.

**Bias declaration, per 6f.** Self-inclusion applies with unknown direction: the corpus is this estate's own and the analyst wrote six of the entries that provenance continuity is credited with catching, so a result in which the imported invariant validates recent work is exactly what an unchecked reading would produce. Outcome knowledge applies: the invariants were read after the corpus, so this measures coverage and not prediction. Asymmetric evidence applies to the zero rows, which record an absence in this corpus rather than a property of the protocol.

## 7. What would change the picture

Concrete, in rough order of expected value:

- **Adversarial oracle independence.** A judge derived from a different source than the artifact: the published schema, a captured live trace, a second process that has not seen the implementation. The single highest-leverage change, since it directly attacks I(T ; W | M) ≈ 0.
- **Assumption registers.** Every unverifiable assumption recorded at the point it is made, with its blast radius, so that "ship anyway" becomes an explicit priced decision rather than a silent default (E4).
- **Type-level audits for missing inhabitants.** Ask of every boundary return: can this value represent "I do not know". Would have caught D1 and, restated, E2.
- **Guard placement analysis.** For each safeguard, identify the failure it targets and confirm it is not downstream of it in the execution graph (D1).
- **Scope-versus-reality checks for anything stateful.** Backups, manifests, allowlists: compare declared scope to observed reality on a schedule, since no self-signal can detect drift (D2).
- **A cost model for probes.** On constrained targets, estimate the footprint of a measurement before taking it (E9).
- **A falsification case per check, with a control beside it.** No check is accepted until it has been observed to fail on a constructed case and to pass on the true one, in the same run. Cheap, mechanical, and the only thing that separates a working instrument from an inert one (E34, §6c).
- **A residence-time budget for instruments.** Anything that has reported the same value on every run since it was written is a candidate for never having run at all. `?` that never changes and `ok` that never changes are the same signal (E32, E36).

None of these are exotic. All of them are things a careful engineer does by reflex and an agent, absent explicit structure, does not.

## 8. Limits of this report

The first campaign: one session, one agent, one operator, one machine. No control condition, no repetition, no counterfactual where the same tasks were attempted with narrower autonomy. Severity ratings are the agent's own judgement of hypothetical outcomes that did not occur. The classification of an error as "would have shipped broken" is a claim about a world that was avoided precisely because the error was caught, and is therefore unfalsifiable in this record.

Most importantly, the analysis is written by the system it analyses. The bias runs toward a narrative in which errors are structural and interesting rather than careless and dull. E1, E12 and E11 are in the ledger specifically because they resist that framing: they are not deep, they are sloppy, and a version of this document that omitted them would be a more elegant and less honest artifact.

### 8.1 Limits the second campaign adds

**The record it draws on is partial, by its own measurement.** The journal and the git history agree on 41.2% of the union of the item numbers they mention. 33 numbers were journalled and never committed, 17 were committed and never journalled. Every count in sections 3.2, 6d and 6e that comes from the journal is therefore a lower bound, not a total, and nothing in the act of reading that journal reveals what it is missing.

**The number of rounds is not established and no figure is asserted.** Four definitions of a round are available, a journal section, a brief, a session, or a range of commits, and they return four different numbers. The disagreement is published in E59 rather than resolved, because choosing one and stating it confidently is the exact error that entry records.

**Several load-bearing facts rest on one node's testimony and cannot be checked against any artifact.** The mechanism of the delivery failure, the origin of the state block, the operator's verbatim validation sentence, and a faulty measurement caught in an unsent draft are all attested by the generating node alone. They are marked in place wherever they are used, and the reason they cannot be verified is not carelessness: the drafts and the conversation they belong to were never written down.

**That last point is the structural one, and it is the first campaign's uncomfortable section moved outward by one node.** Section 8 above says the entries most likely to be missing are the ones the agent still believes are correct. The second campaign put a node with no shared context on the other end of the loop, and it worked, catching five checkable errors in documents it was handed. But the generating node's own reasoning left no artifact. The faults recorded against it are the ones it noticed and reported about itself, and the executing node has no way to look for the others, because only the finished briefs exist and never their drafts. **A two-node loop reduces the self-analysis problem. It does not eliminate it. It moves it to the node whose record is not written.**

**And the conflict of interest did not go away, it changed shape.** The first campaign's version was an agent analysing itself. This one is a later node of the same estate analysing its predecessors, using the estate's own registers as evidence, under a protocol the estate designed. The apparatus in this document is more careful than the first campaign's, with falsification cases, witnessed detectors and re-derivation. That is not a defence. Rigour of method is precisely what would make a conflict of interest invisible rather than absent, and this document is not the place from which that can be checked.
