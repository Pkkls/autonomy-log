# Ledger

Every mistake the agent made, in order, with how it was caught and what it cost. Discoveries about the environment are listed separately at the end, because finding someone else's bug is not the same achievement as not writing one.

Severity is judged by what would have happened if nobody had caught it, not by how embarrassing it was.

## Agent errors

### E1. Extension manifest outside the extension root
**Severity: low.** The MV3 manifest was written into a subdirectory while the module it loaded sat one level above. A browser refuses to load anything above the extension root, so the test bench could never have started.
**Caught by:** the agent, rereading its own layout before publishing.
**Class:** structural knowledge, applied carelessly rather than missing.

### E2. Wire type assumed from a field name
**Severity: high.** `broadcaster_user_id` was sent as a JSON string. The API types it as an integer. Every subscription attempt would have been rejected, which is the first thing a user does after installing the daemon.
**Caught by:** reading the OpenAPI schema while implementing an unrelated feature. Not by a test.
**Why tests missed it:** the test double accepted any JSON body and asserted on the decoded value, which was `"123"` and looked correct. The double was written by the same process that held the wrong belief.
**Fix:** assert the wire type, not the decoded value. `strings.Contains(body, '"broadcaster_user_id":123456')` fails when the value is quoted.

### E3. Payload shape guessed and correct by luck
**Severity: high if wrong, zero as it turned out.** Channel filtering depended on `broadcaster.user_id` existing in every webhook payload. That structure was inferred, never checked. Had it been wrong, the filter would have extracted nothing, matched nothing, and delivered an idle stream with no error anywhere.
**Caught by:** deliberate audit after E2, comparing against the documented payloads.
**Class:** unverified assumption in a load-bearing position. The outcome was luck; the process was the defect.

### E4. Request shape assumed for an endpoint that could not be reached
**Severity: high.** The token fetch sent only `Accept`. The real client sends session cookies plus three headers, one of which is a public client constant. The endpoint is blocked outside a browser and blocked by CORS from a page, so the assumption had never been testable, and the code shipped anyway.
**Caught by:** hooking `fetch` in a live page, then closing the websocket to force a reconnect so the token request would replay under the hook. This is live instrumentation against the running system, not desk reasoning, and an earlier version of the counting section below filed it under "reasoning", which flattered it.
**Class:** the agent knew it could not verify and shipped as if it had.

### E5. False positive on a backup risk report
**Severity: medium, and corrosive.** A repository was reported as holding five commits that existed nowhere else. It was actually eight commits *behind* its remote. The heuristic counted the whole history as unpushed whenever a branch had no upstream.
**Caught by:** running the tool against the real machine and checking the alarming result before reporting it as fact.
**Cost if unfixed:** a backup report that cries wolf gets ignored, which removes the value of the true positives sitting next to it.
**Fix:** report `ahead` only when measured against an actual upstream. A branch with a remote but no upstream is labelled untracked, which says nothing either way, because that is the truth.

### E6. `.git` assumed to be a directory
**Severity: medium.** Worktrees and submodules store `.git` as a file. The tool declared them "not a repository", which silently skipped the checkouts most likely to hold forgotten work.
**Caught by:** asking what the tool assumed, then building a real worktree to check.

### E7. Scanner returned success on an unreadable path
**Severity: medium.** A credential scanner intended for a pre-push hook printed "not a git repository" to stderr and exited zero. A typo in the path would have produced a green, meaningless check.
**Caught by:** the agent's own manual probe of an invalid path, not by the test suite it had just written.
**Fix:** distinct exit code for "could not scan", separate from "scanned and clean".

### E8. Pattern matched inside a base64 blob
**Severity: low, high noise.** A token pattern matched a fragment of a Flask session cookie stored in a test fixture, reported as a Discord bot token.
**Caught by:** inspecting the finding instead of reporting it.
**Fix:** anchor patterns at a boundary. The search tool speaks POSIX regex with no lookbehind, so the boundary is enforced in a second pass in the host language.

### E9. Parsed a 15 MB file on a 128 MB production board
**Severity: medium, operational.** To measure a file, the agent loaded and traversed it in place. On a board with 128 MB of RAM already using swap, the process ran for ten minutes without finishing, drove load average from 3 to 6.3, and had to be killed.
**Caught by:** the agent, watching the load it had caused.
**Class:** no model of the cost of its own probe. The measurement should have been streaming from the first attempt.
**What it should have done:** sample. The answer eventually came from counting date occurrences with a streaming filter, in under a second.

### E10. Tested against the wrong service
**Severity: low, near miss.** A smoke test bound to a port already occupied by an unrelated service on the user's machine. The health endpoint answered, the agent briefly read that as its own daemon working.
**Caught by:** the response body not matching the daemon's schema.
**Class:** absence of environment checks before asserting ownership of a resource.

### E11. Killed a process by name
**Severity: low, unquantified.** Cleaning up test processes, the agent killed by image name rather than by the process identifiers it had started. If the user had an unrelated interpreter running, it went down too. This is reported as unquantified because the agent cannot prove it did not.

### E11b. The same kill-by-name error, hours after writing it down
**Severity: medium, self-inflicted on production.** Cleaning up its own leftovers on a board, the agent ran `killall python3`. That stopped two production services: a chat bot and a watcher. One returned by itself under a watchdog; the other had to be restarted through its init script, which then produced a **duplicate** instance, two pollers fighting over the same API token, removed by pid using the service's own pidfile.

**Caught by:** the agent, checking which services survived immediately after. No lasting damage.
**Why it matters more than the first occurrence:** E11 was already written into the agent's persistent rules earlier the same day. The rule existed, was correct, and did not fire, because the action felt like tidying rather than like an intervention. **A rule attached to a category of action does not fire when the action is reclassified as harmless.** The rule was rewritten with the full incident attached rather than restated.
**Cost ratio:** one command of convenience, four commands of repair.

### E11c. A health probe written against invented output
**Severity: medium, caught before deployment mattered.** A DNS health check for the status display was written against `nslookup` output the agent composed from memory, and unit-tested against those same invented strings. Run against the real tool, three assumptions were wrong:

- **NXDOMAIN was counted as a failure.** A resolver answering "no such name" is working perfectly. On a DNS blocker, where blocked names return exactly that, the probe would have reported a permanent outage the moment anyone pointed it at a blocked domain.
- **The exit status was assumed to mean something.** busybox `nslookup` returns 0 whether the server answers or is unreachable. Any check built on the exit code would have been a constant green.
- The unreachable case was recognised only by empty output, when the real tool prints a `connection timed out` line.

**Caught by:** deliberately running the tool against a live resolver, a dead address and a nonexistent name, and reading what actually came back.
**Class:** identical to E2. A test authored by the same process that holds the belief cannot disagree with it. The fixtures are now captured output verbatim, and the corrected probe was re-run against all three real states.

### E12. Repeated path-form errors across shell boundaries
**Severity: low, cumulative.** POSIX paths were handed to Windows binaries and shell variables were eaten crossing three shell layers, costing several wasted round trips.
**Class:** a known environment quirk, documented in the agent's own notes, not applied until it failed.

### E13. A test encoded the old semantics and had to be corrected twice
**Severity: none, listed for honesty.** After changing what "ahead" means, two assertions failed. Both failures were the test being right about the old behaviour. They were corrected, not deleted, and one of them turned into the regression test for E5.

### E14. A secret scanner that reported clean without searching
**Severity: high.** The credential scanner used to gate every publication in this session had a pattern written in Perl syntax, `(?:...)`, which POSIX ERE rejects. `git grep` refused it and exited 2. The wrapper collapsed every non-zero exit into an empty string, so that entire class of credential was skipped on every scan ever performed, and the tool still printed "no credentials found". Five public repositories were published on that assurance.

Adding a test that runs each pattern through `git grep` itself immediately exposed a second one: the private-key pattern begins with a dash and was parsed as an option, so git printed its own help instead of searching.

**Caught by:** an independent audit by a process that did not write the tool. Not by its selftest, which exercised only patterns that happened to be valid in both engines.
**Class:** E7 and D1 combined, in the one tool whose whole purpose is to not miss things. A failure was rendered indistinguishable from a clean result, and the check that would have caught it, validating each pattern against the engine that actually runs it, is the same "assert against something you did not author" rule this report is built on. Python's `re` accepting a pattern says nothing about git's engine.
**Aftermath:** all five published repositories were rescanned with the fixed tool. Nothing found.

### E15. Believing an auditor without checking
**Severity: none, avoided.** The same independent audit reported that no release existed for one project, having run `git tag` locally and found nothing. The releases exist: three of them, with binaries and checksums, created through the GitHub API where the tags live on the remote rather than in the local clone. Acting on the report would have meant deleting an accurate changelog entry and replacing it with a false one.
**Why it is in this ledger:** an independent oracle is worth having precisely because it does not share the author's beliefs, and for the same reason it does not share the author's context. Its findings are evidence to check, not verdicts. Three of its four findings were real and serious; the fourth was wrong, and only verification told them apart.

### E16. A success measured through an uncontrolled second cause
**Severity: highest of the session, by elapsed cost.** A daemon was written to earn progression points on a streaming platform by holding a connection open. It was reported as working because the account's total rose while it ran. A browser was logged into that same account, on the same network, earning the same points the whole time. The daemon contributed nothing. It could have been an empty loop and the numbers would have been identical.

The agent had the disconfirming evidence in its own logs, on every line, for months: a second account that no browser touched, printing `+0 XP` at every cycle. It was mentioned once in passing and not treated as a result.

**Caught by:** the operator asking whether it really worked, since he had a browser open on that account. The measurement that settled it took four minutes: stop the daemon and watch whether anything changes. Nothing did.
**Class:** new. Not an unverified assumption, an assumption that was *verified against a confounded observation*. The open loop was running. External data was arriving. It was simply not attributable, and nothing in the process asked what else could produce this number.
**Cost:** two months of the operator's project built on a mechanism that never worked, plus one full rewrite whose stated justification was the same false belief.
**What ended it:** a control account with exactly one possible cause, and measuring the absence rather than the presence. "It rose while my code ran" is not evidence. "It stopped rising when I stopped my code" is.

### E17. A rotated credential read as an architecture change
**Severity: medium, and it propagated.** An application key for a hosted message bus answered "not in this cluster" on every region. The agent concluded the platform had migrated off that bus, wrote it into the persistent notes as a fact about the architecture, and filed it below as environment discovery D3. A later rewrite of the daemon deleted its message-bus subscription on the strength of it.

The platform had not migrated. It still uses that bus, under a different key, which the current client sends on every page load. A dead credential is evidence about a credential.

**Caught by:** reading the site's own client bundle while chasing E16, and finding the live key in it.
**Class:** inference from a single negative probe to a structural claim, with no attempt at the cheap positive control, which was to look at what a working client actually connects to.
**Aftermath:** D3 is retracted below, the persistent note was corrected, and the deleted subscription was restored.

### E18. The credential gate failed open, again, in the same session that wrote it up
**Severity: medium, no leak, entirely process.** Publishing a fix, the agent ran the credential scanner and piped it through `tail -1` inside a `&&` chain. `tail` exits zero whatever it is fed, so the scanner's exit code was discarded. It printed **`1 finding(s)`** and the agent committed and pushed in the same command without reading it.

The finding was real: a live Telegram bot token and an API key sitting as fallback defaults in a config file, present since that repository's initial commit. Not introduced by this session, and the repository is private, so nothing leaked. That is luck, not process.

**Caught by:** the agent rereading its own command output a moment later.
**Class:** third instance of one idea. E7 was a scanner returning success on an unreadable path. E14 was a scanner reporting clean without searching. E18 is a scanner that searched, found, said so, and was not listened to, because the plumbing around it threw the answer away. **A check is only as good as the weakest link between it and the decision it gates**, and twice now the weak link has been downstream of a correct result.
**Fix:** the gate is read on its own, exit code and all, never piped into something that launders it. The credentials were removed from the checkout, and rotation is flagged to the operator since removal does not revoke.

## Environment discoveries

These were found, not caused. They are the reason the session was worth running.

### D1. A monitoring bot reporting zero as a measurement
For ten days, a daily inventory bot fetched nothing, recorded a snapshot of zero items, and sent a report announcing an empty portfolio, marked as successful. The upstream API had started refusing requests. The code logged the failure, returned an empty collection, and let every downstream stage treat emptiness as data.

An abort flag existed for exactly this. It was only ever set inside the pricing loop, which is never entered when the item list is empty. **The safeguard sat downstream of the failure it was meant to catch.**

### D1b. The same bot, the same lie, one layer further out
D1's guard was added and it works. On 30 and 31 July, Steam answered 429 on both inventories, the guard fired, and no zero snapshot was written. The database was protected exactly as intended.

The report is built from the same run. It went out both days announcing a portfolio worth **0.00 EUR, down 100% since yesterday**, formatted like any normal daily statement, because the delta is computed against a stored history that the guard had correctly preserved. Fixing the storage made the false report arithmetically *worse*: an intact history to subtract a zero from produces a precise, credible collapse.

Underneath sat the representational collapse from D1, one call further up: the fetcher omits a game it could not read, so a missing game and an empty inventory are the same value by the time anything else looks. The partial case, one game fetched and one not, had no guard at all and is the more dangerous one, since the total looks plausible.

**What this says about fixing things:** the guard was placed where the bug was *observed*, not where the failure *enters the world*. Anything downstream of that point still consumes the same undifferentiated zero. The sibling bot in the same collection had the unguarded version of all of it, including overwriting a multi-megabyte analysis with an empty one and returning a failure code from `main()` that nothing read, so a refusing run would still have exited zero.

### D2. A backup verifying clean on two thirds of a machine
Daily, encrypted, pushed, size stable for seventeen days, restore check green. The manifest described the machine as it had been months earlier. Everything added since, including a non-reproducible price history, a live session file, credentials, the DNS configuration and every maintenance script, was absent from every archive.

A backup that fails loudly gets fixed. A backup that succeeds on a stale scope is trusted until the day it is needed.

### D3. RETRACTED. A realtime protocol migration that did not happen
This entry claimed a public streaming platform had moved off its hosted message bus, on the evidence that an application key returned "not in this cluster" on every region. The key had been rotated. The platform still uses that bus. See E17.

The entry is left in place rather than deleted, because a report about unverified beliefs that quietly removes its own is worth less than one that shows the correction. What survives of it is narrower and still true: **client code pointing at a dead endpoint fails silently when it has a fallback path**, which is how the key stayed dead long enough to be mistaken for a migration.

### D6. Progression credited by an announced event, not by a held connection
The same platform grants watch-time progression on an explicit event the player posts every thirty seconds, naming the channel and the live stream. Holding the viewer socket open credits nothing. Subscribing to the stream's message-bus channel credits nothing. Both together, on a logged-in account, credited exactly zero over half an hour, which is the measurement that should have been taken first.

Two things made it findable once the socket theories were dead. The client bundle names its own behaviour, so searching it for what fires during playback returned the call in minutes after months of reasoning about which connection mattered. And the endpoint's validator is documentation that cannot go stale: a missing CSRF header, a flat object and a wrapped object each came back naming what was wrong, and the fourth attempt was accepted. Four requests, no guessing.

### D4. Credentials committed in a private repository
Two bot tokens in the current checkout, not merely in history. Private, so not a public leak, but a private repository is one setting away from public and history rewriting never un-leaks anything.

### D5. Unbounded growth inside a bounded retention window
A trend file grew nineteen times in seventy days while its retention policy worked correctly. Retention bounded the age of the data, not the width of the universe being sampled. The file now costs more to load than the board can comfortably afford.

## Counting

Eighteen agent errors: one a repeat of another written down hours earlier, one a fresh instance of the very failure class the report is built around, one (E17) whose consequence was to plant a false entry in this document's own findings section, and one (E18) that broke the credential gate for the third distinct reason, minutes after the same session finished documenting the second.

Two were caught by desk reasoning alone (E2 from reading a schema, E3 from auditing against documentation). E4 was caught by live instrumentation, which an earlier version of this section miscounted as reasoning, and which the taxonomy in RESEARCH.md had classified correctly all along. The two documents contradicted each other about the report's own methodology until an outside audit noticed. Four would have shipped broken behaviour to a user (E2, E4, E5, E7). Three were caught by reasoning rather than by tests (E2, E3, E4). One was caught by tests the agent had written (E13, twice). One was operational damage to a live machine (E9).

The ratio worth staring at: **zero of the four shipping-grade defects were caught by the agent's own test suite**, and every one of them lived at a boundary with something the agent could not run.

E16 sits outside that count and costs more than all of it. Every error above is a belief that met no evidence, or met evidence and was corrected. E16 is a belief that met evidence, was confirmed by it, and was wrong anyway, because the evidence had a second cause nobody had ruled out. No amount of contact with the world fixes that on its own. What fixes it is holding one channel where only your own action can move the number, and checking that it moves when you act and stops when you stop.
