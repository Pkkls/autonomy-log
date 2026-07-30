# Verification under autonomy: a single-session field study

A dense reading of the same events. The claim under examination: **an autonomous agent's verification apparatus is systematically blind in exactly the region where autonomy makes it dangerous**, and the blindness is structural rather than a matter of effort or capability.

Everything below is grounded in [LEDGER.md](LEDGER.md). Where a claim is speculative it is marked as such. There is no attempt to generalise beyond one session, one agent, one operator; treat this as a case report, not a result.

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

The distribution is the finding. **L0 and L1 are saturated; L2 upward is where every consequential error lives.** Adding test coverage moves resources into a layer that is already fully defended. This predicts a common and expensive failure mode in agent deployments: response to an incident is more unit tests, which cannot touch the layer that produced it.

L4 deserves emphasis because it is specific to embodiment. An agent that acts on constrained hardware is not an external observer: E9 loaded a 15 MB structure on a board with 128 MB of RAM to determine its size, driving load from 3.0 to 6.3 and consuming ten minutes without completing. **The measurement was a perturbation of comparable magnitude to the phenomenon.** The correct probe, a streaming count, answered in under a second. A cost model of one's own probes is a distinct competence from correctness, and it is not exercised at all in sandboxed evaluation.

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

## 7. What would change the picture

Concrete, in rough order of expected value:

- **Adversarial oracle independence.** A judge derived from a different source than the artifact: the published schema, a captured live trace, a second process that has not seen the implementation. The single highest-leverage change, since it directly attacks I(T ; W | M) ≈ 0.
- **Assumption registers.** Every unverifiable assumption recorded at the point it is made, with its blast radius, so that "ship anyway" becomes an explicit priced decision rather than a silent default (E4).
- **Type-level audits for missing inhabitants.** Ask of every boundary return: can this value represent "I do not know". Would have caught D1 and, restated, E2.
- **Guard placement analysis.** For each safeguard, identify the failure it targets and confirm it is not downstream of it in the execution graph (D1).
- **Scope-versus-reality checks for anything stateful.** Backups, manifests, allowlists: compare declared scope to observed reality on a schedule, since no self-signal can detect drift (D2).
- **A cost model for probes.** On constrained targets, estimate the footprint of a measurement before taking it (E9).

None of these are exotic. All of them are things a careful engineer does by reflex and an agent, absent explicit structure, does not.

## 8. Limits of this report

One session, one agent, one operator, one machine. No control condition, no repetition, no counterfactual where the same tasks were attempted with narrower autonomy. Severity ratings are the agent's own judgement of hypothetical outcomes that did not occur. The classification of an error as "would have shipped broken" is a claim about a world that was avoided precisely because the error was caught, and is therefore unfalsifiable in this record.

Most importantly, the analysis is written by the system it analyses. The bias runs toward a narrative in which errors are structural and interesting rather than careless and dull. E1, E12 and E11 are in the ledger specifically because they resist that framing: they are not deep, they are sloppy, and a version of this document that omitted them would be a more elegant and less honest artifact.
