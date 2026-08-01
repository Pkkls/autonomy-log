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

**Correction, later.** That sentence was true and read as broader than it was. Five repositories were published *in that session*; the account has fifteen public ones, and the other ten had never met the fixed tool. They were finally scanned across full history, not just HEAD, since on a public repository history is the exposure. All fifteen are clean. Two matches came back and both survive inspection as benign: the scanner matching its own pattern table, and a unit test whose subject is redacting PEM blocks.

The scanner was left exactly as sensitive as it was. Two explainable matches out of fifteen cost about ten seconds of reading; trading sensitivity away in a tool that has already failed open three times would be the wrong side of that exchange. **"Rescanned everything" deserves the same suspicion as any other completeness claim, including one's own from an hour earlier.**

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

### E19. Obeyed the letter of its own rule and broke it anyway
**Severity: low, unquantified, and the most instructive error here.** Deploying a new build to a board, the agent needed to stop the running daemon. It had a rule from E11 and E11b, written twice, in its persistent memory: **kill by process id, never by image name.** It did exactly that.

The process id was computed by a pipeline sent from a Windows shell, through WSL, through ssh, into the board's shell. The quoting was eaten on the way, as it had been roughly a dozen times already in this session. The pattern matched nothing it was supposed to, the extracted id was not the daemon's, and the agent killed **pid 1263 without ever knowing what it was**. Most likely a getty, since one had been respawned with a new id by the time anyone looked. It cannot be proven.

The same mangling then produced `instances: 0`, so the agent concluded the daemon was down, tried to restart it, saw nothing happen, and started diagnosing a startup failure that did not exist. The daemon had been running and farming the whole time, on the process the kill had missed.

**Caught by:** printing raw `ps` output instead of a count derived from a pattern, after the count and a separate check disagreed.
**Class:** new, and worth naming. E11 was a rule about *which verb to use*. Following it is not enough when **the argument to the safe verb is computed by an unreliable channel**. A rule that says "kill by id" silently assumes the id is trustworthy, and nothing had ever checked that assumption. The pipeline was the known-broken part; the rule pointed at the other end of the command.
**Fix:** the restart runs as a script file copied to the board, so no pattern crosses a shell boundary, and it reads `/proc/<pid>/cmdline` to confirm the target is what it thinks before signalling it. It also waits for the process to actually disappear, because the previous attempt relaunched while the old one was still dying and the guard correctly refused, which had looked like a second failure.

### E20. A check that checked nothing, twice over, hours after the rule was written
**Severity: none, and the timing is the point.** Verifying a dashboard's embedded JavaScript, the agent extracted it to a file and ran `node --check` on it. The command was piped through `tail`, so the exit code read was `tail`'s. It printed "syntax valid" and moved on.

The output visible on screen was in fact node's error dump. The script had never been parsed at all, because the file had been written to a path that did not resolve the same way for both tools, and node reported the file missing. **Two independent failures stacked into one confident green**: the wrong exit code, and a check whose input did not exist.

E18, recorded earlier the same session, is a credential gate piped through `tail`. The rule was written into the agent's persistent memory hours before this. It did not fire, for the same reason E11b did not: the action felt like a quick sanity check rather than a gate, and rules attach to categories, not to shapes.

**Caught by:** rereading the output rather than the summary, and noticing that a syntax-error dump was being reported as success.
**Fix:** absolute paths on both sides, exit code read directly, and then the check was taken further than syntax. The helpers were run against the board's real JSON, including the empty and never-set cases, which is what "verified" should have meant in the first place.

**What that stronger check then found:** the dashboard's amber threshold was 180 seconds for both the watch event and the XP gain. Measured from the board's own history, gains arrive 121 seconds apart at the median and 241 at the ninetieth percentile, so amber lit on roughly one healthy cycle in ten, while the same threshold was far too loose for an event posted every 30 seconds. A warning colour that appears during normal operation trains the reader to ignore it, which is precisely what this dashboard was built to prevent. The thresholds now come from the measurement.

### E21. A mutation test that mutated nothing
**Severity: none, and it is the technique's own blind spot.** Mutation testing has carried a lot of weight in this session: change the fix, watch the test fail, keep the test. Twice in a row a mutation reported a guard as untested. The guard was fine; the substitution had matched nothing and written the file back unchanged, so the "mutated" run was the original code passing its own test.

Both times the conclusion drawn was about the test. It was about the probe.

**Caught by:** counting the occurrences of the target string before and after the edit and printing whether it had actually changed. With that in place the mutation killed the test immediately, on two separate assertions.
**Class:** the same shape as the `grep` false negatives earlier the same day, and as E18 and E20: a step in the verification chain silently did nothing, and its silence was read as a measurement. **A tool used to check other tools is not exempt from being checked.** Mutation testing answers "would this test notice", and it can only answer it if the mutation happened.
**Fix:** the mutation asserts that it changed the file before the test is run. One line, and without it the technique quietly degrades into running the suite twice.

### E27. Third instance of the same empty check, minutes after reading the warning against it
**Severity: none, and it was still the right answer, which is the worrying part.** Auditing a backup manifest against the machine it describes, the agent asked the board which of thirteen paths existed, with a shell loop over a variable. Every one came back absent, including four it had listed itself moments earlier from a directory listing.

The loop variable arrived empty. Passing a single-quoted `$f` through `wsl.exe` strips it, so the test run thirteen times was `[ -e "" ]`, which is false, thirteen times. The output was well formed, plausible, and measured nothing.

Four of the thirteen paths really were gone, so the conclusion drawn from it happened to be correct. That is worse than being wrong: an identical printout would have appeared if all thirteen existed, and the conclusion was acted on before anything distinguished the two cases. **A broken check does not usually error. It answers.**

The warning is written in the script the agent was editing at that moment, at line 120, in the comment explaining why that script feeds its remote commands over stdin: `wsl.exe mangles inline single-quoted '$f', stdin does not`. It had been read, in full, in the same session, a few minutes before.

**Caught by:** noticing that a path listed as present by `ls` seconds earlier was reported absent, and that the absent lines had no filename in them.
**Fix:** the paths were passed to `ls` as explicit arguments, with no shell variable anywhere. That run separated the four genuinely missing from the nine present, and turned up a tenth thing nobody had asked about.
**Class:** E20, E21, E27. Three instances of a verification step that silently did nothing while producing a confident answer, all within the same body of work, each caught by reading the output rather than the summary. The common thread is not carelessness about checking; every one of these *was* a check, deliberately written. It is that a check is itself a program, and nothing was checking the checkers.

### E28. The estate's own health tool, wrong on both of the questions it was built to answer
**Severity: low, and it is the last place this should have been found.** The healthcheck exists so that "is the estate sound" gets the same answer every time, and its opening line is that a procedure which varies cannot tell you whether anything got worse. Two of its checks were audited against independent measurements. Both were wrong.

The Steam session check ended in `else: OK, "valide"`. Anything it did not recognise was reported as a healthy session: an empty pipe, a crashed binary, a flag that disappeared, a reworded message. The failure it exists to catch is a session that expired quietly and let eleven days of reports go out wrong. **A check for a silent failure had a silent success.**

The uncommitted-work count, which answers "what disappears if the disk does", read 102 files across ten repositories. The real number was 2. The checkouts sit on a Windows disk with `core.autocrlf` set, so CRLF on disk and LF in the blobs; git invoked from WSL does not inherit that, hashes the raw bytes, and calls every file of every repository modified. Forcing the setting corrected it, and revealed the second fault underneath: git then prints one conversion warning per file on stderr, and the helper merged stderr into stdout, so twenty-three warnings were counted as twenty-three filenames.

**Caught by:** asking the same question through a second channel. Native Windows git said 0 where the tool said 69, and the two numbers could not both be right.
**Fix:** the session classifier is its own function with `--selftest` over six cases, and mutating it back to the old branch turns four of them red, which is what makes the six worth keeping. The file count forces the line-ending setting and reads stdout alone. Both verified twice in a row and against Windows git on all ten repositories.
**Class:** the first half is D1's collapse, in the tool written to detect D1's collapse. The second half is E18 and E20's plumbing, a third time: a diagnostic stream folded into a data stream and then counted. **Neither fault was in a check that was missing. Both were in checks that ran, passed, and printed a number.** The estate had been green for hours on a measurement that was 98 percent invented.

### E29. Swept someone else's uncommitted work into a commit about something else
**Severity: low, and the history is what pays.** Refreshing a configuration mirror from the machine it describes, the staging step was `git add -A`. It picked up a 128-line rewrite of an unrelated file that had been sitting uncommitted since before the session began. Nothing was lost and nothing broke; the commit message describes seven configuration files and says nothing about the eighth change it carries.

**Caught by:** reading the commit's own diffstat afterwards, which is one step later than it should have been.
**Fix declared rather than applied:** splitting it means rewriting a commit already pushed, so it was reported and left to the operator to decide.
**What it cost beyond the commit:** an attempt to turn it into a rule failed honestly. Staging everything is correct whenever the whole tree is yours, which is nearly always: the pattern fired on 117 of 5084 real commands, almost all of them fine. Whether it is dangerous depends on what the repository holds at that instant, which no amount of reading the command can reveal. The rule was dropped rather than shipped at a rate that would have taught its reader to ignore the two rules that do work. See D7.

### E30. A pattern that could never match, inside the guard written against patterns that never match
**Severity: none, and it is the shortest distance yet between a lesson and its repetition.** The guard described in D7 has a rule for verifiers whose exit code is thrown away before a claim of success. The pattern behind it was assembled by a script that wrote `\b` inside a non-raw Python string, so what compiled was a literal backspace character where the word boundary belonged. It compiled cleanly. It ran against all 5084 commands. It could not match anything, ever.

The measurement it produced looked entirely reasonable, which is why it survived: the other half of the rule was working, so the totals moved when the rule was tightened, and nothing in the output said that one branch was dead. Three separate attempts to fix it appeared to succeed and did not, because the replacement text carried the same escaping fault, and because `str.replace` returns the original string unchanged when it matches nothing and says so to no one.

**Caught by:** the tightened rule producing exactly the same count as the loose one. Two different rules cannot give identical answers on five thousand inputs.
**Fix:** the pattern is a raw string, the byte is gone from the file, and the check is that the compiled pattern contains no backspace and matches the historical command. Both are asserted, not observed.
**Class:** E20, E21, E27, and now E30, in the file whose entire purpose is to catch that class. Four instances. What separates this one is speed: the file's own docstring was already explaining that writing an error down does not prevent it, in the same commit that shipped an example.

### E22. Concluded absence from a search that was looking for the wrong string
**Severity: medium, and the operator caught it.** Asked whether the inventory bot sees items bought in the last seven days, the agent queried the live inventory for Steam's trade-hold notice, found the phrase nowhere across 1259 items, and reported that nothing was currently held.

Four items were held. The notice reads **"Tradable/Marketable After 5 Aug @ 5:00am"**. The search was for `"Tradable After"`, which does not occur.

The operator replied "FAUX !!!" and pasted three of them.

**Class:** the same shape as the `grep` false negatives and E21, in the one place it had been named a day earlier: **a probe that returns nothing is not evidence of nothing**. The difference here is that the agent had already written that rule down, published it, and stored it in memory that morning. It fired against tooling and did not fire against a substring it had invented itself.

**The correction was also wrong.** The first explanation offered was that the API had answered in French, since the operator's Steam is French and the cookie says so. It had not: the request passed `l=english` and the response was English. The real cause was the substring, and blaming the locale was a second confident answer produced without checking.

**What the mistake was covering:** the deduction attached to it was right. Those four items carry `marketable = 0`, and the scanner dropped every such item, so a purchase was invisible for a week and then arrived as an unexplained jump the day the hold lifted. Being wrong about "are any held right now" hid a real defect behind a reassuring answer.

**Fixes:** held items are kept, counted, valued and named with Steam's own date; permanently non-marketable items are still excluded, because a held purchase and a bound skin are different things. The matcher is deliberately loose on "After", and the test asserts against the verbatim sentence, so restoring the narrow pattern fails it.

### E23. Re-merged two states an hour after separating them everywhere else
**Severity: low, caught by looking at the output.** The first version of the trade-hold counter incremented only when the item also had a price. Three of the four held items are stickers too new for the price feed to list, so the report announced **"1 item on trade hold"** while four were held.

Whether an item is held is a fact about the item. Whether it can be priced is a fact about the market. This program had spent the previous two days pulling exactly that pair apart in six other places, and the agent merged them again sixty minutes later, in code written to fix a bug of the same family.

**Caught by:** reading the rendered report against the known answer of four, rather than trusting the change that had just been tested.
**Class:** the rule was known, published, and had just been applied. Knowing a pattern is not the same as recognising an instance of it, which is E11b's lesson in a different domain.

### E24. Shipped links without opening one
**Severity: low, user-facing, and entirely avoidable.** Rebuilding a report so it names items rather than just totalling them, the agent linked every item to a marketplace search URL it had constructed by reading the site's URL shape. Every link was dead. The operator clicked one and said so.

They were not obviously dead: the URL answers **HTTP 200** with a 2145-byte application shell that renders nothing. Checking the status code would have confirmed the mistake rather than caught it. The working alternative returns 213 KB of actual listings, so the two are distinguishable in one request by anything other than the status line.

**Class:** the same shape as the empty-feed and unreadable-repository cases this log is built on, with the agent on the wrong side of it: **200 is not "it works"**, exactly as "no output" is not "nothing found". The rule had been applied to every service the program consumes and to none of the links it emits.

**What makes it worse than a broken link:** the whole point of the change was to make the report actionable. A list of names that cannot be opened is a list of names.

### E25. Three sends refused before the cause was measured
**Severity: medium, the report stopped arriving.** The rebuilt report grew from a few hundred characters to about 17500, and Telegram refused it three times with a bare 400.

Two causes, both known and both already written down somewhere in this repository:

- **An unescaped ampersand in a link.** One item is called "Dreams & Nightmares Case". URL-escaping leaves `&` alone, correctly, and a bare `&` inside an HTML attribute ends the parse. The comment above the escaping helper said exactly this, an hour before it happened; the escape had been applied to the visible text and not to the href beside it.
- **A splitter that cut every 4000 bytes.** Past the limit it landed inside a tag and inside a multibyte character at once. The sibling Python bot hit this in June and fixed it by splitting on line breaks. The report content was ported; the delivery fix that content requires was not.

**Caught by:** measuring the message (17557 bytes against a 4096 limit) instead of guessing at the 400 for a third time.
**Class:** porting a feature without porting the constraints it lives under. Both failures were solved problems in code sitting twenty metres away.

A smaller one rode along: the new French movers section was added without removing the English block it replaced, so the same price moves were listed twice, once in euros and once labelled in dollars. Nobody had read the rendered message end to end.

### E26. Three tightenings before a checker was worth reading
**Severity: none, and it is the counterweight to E24.** After shipping dead links, the obvious move was a tool that checks them. Its first run over everything published returned six failures, of which **four were its own false alarms**: three CI badges, which are SVGs of two kilobytes and entirely healthy, and a short page carrying a canonical link, which is a redirect rather than an empty shell. A fifth batch came from `${item.icon_url}` in an href, which is a template hole and not a URL.

Two thirds noise on the first run. This log has argued repeatedly that in a monitoring tool a false positive costs more than a miss, and the tool written to enforce that lesson opened by breaking it.

**What the tightenings were:** the empty-shell test applies to pages and not to images; a page that points elsewhere is redirecting, not empty; a code template is not a link; and a file git ignores is not published, so its links are nobody's business.

**Caught by:** reading all six findings before believing any of them, which is the same act that turned two earlier "discoveries" today into nothing.
**Kept, not smoothed over:** a rule that needed three corrections before it was usable is worth recording as such. The end state is twenty links across eight repositories, none broken, and a check that runs in CI so the next dead link is caught by a machine rather than by the operator clicking one.

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

### D1c. A fix that would have deployed cleanly and done nothing
The same bot's other implementation, the one that actually sends the daily message, had a prepared fix waiting: flag the run as aborted, store the row, and let readers skip it. Correct in isolation.

The eleven zero rows already in the database all carry `aborted = 0`. The binary that wrote them, the one still running, never set the flag. Filtering the baseline on the flag alone would have passed its tests, deployed without incident, and left every reader still treating those zeros as valuations.

The clause that does the work is `total_items > 0`. **A flag is only as trustworthy as the version that wrote the row**, and a schema column is not evidence that anything ever populated it. The item count, by contrast, has been written by every version there has ever been.

Two smaller things surfaced in the same fix. Its warning message claimed no snapshot had been recorded while the code recorded one, so the report about unreliable numbers was itself inaccurate. And the first test written for the filter passed without the filter: three rows inserted in the same second collided on `CURRENT_TIMESTAMP`, which resolves to whole seconds, so `ORDER BY timestamp` broke the tie arbitrarily and happened to pick the right answer. It was caught by mutating the code and watching the test not fail, which is the only reason it is not still there.

### D1d. The same collapse, third instance, same program
Chasing why nobody noticed the outage for eleven days, the cause turned out to be a session cookie that expired on 20 July at 17:02, twenty-four hours after it was issued. The last good scan was that morning. Every 429 since was a symptom.

The program could have said so from day one. It computes the cookie's expiry and warns when it is close. Three things stopped the message landing:

- An expired cookie rendered as **"expires in -11 day(s)"**. Arithmetically correct, and it reads as a formatting glitch rather than as the reason nothing works.
- A cookie that could not be parsed produced **no warning at all**, because the expiry helper returned "could not determine" and the caller only warns when it *can* determine. Unreadable and healthy shared an answer.
- The repeated-failure escalation blamed an IP throttle, contradicting the cookie line beside it. **Two alarms that disagree are read as noise**, and noise is the state this whole report is about.

The middle one is the finding. This is the third appearance of the same collapse in one program: D1 was an empty inventory indistinguishable from an unreachable one, D1b was the report layer repeating it, and this is the credential check doing it a third time, in code written *after* D1 was diagnosed and fixed.

**Fixing an instance does not fix a pattern.** The lesson from D1 was recorded as a rule about that bot's snapshot, so it was applied to that bot's snapshot. A collapse between "absent" and "fine" is a property of a *type*, and it will reappear at every boundary where that type is produced until someone goes looking for the shape rather than the incident.

A related honesty note: the agent's own persistent memory asserted the cookie "contains no JWT", which sent the search toward a format problem. It decodes perfectly. It is simply out of date. The note was written from a plausible inference and stored as an observation, and it cost part of an evening pointed the wrong way.

### D1e. Below a false report: no report, and no trace either
The same bot has a third deployment, a scheduled job in CI. Every scheduled run for as long as the logs go back is marked **cancelled**. Every step succeeds except the scan, which the runner kills at its fifteen minute timeout, because five retries sleeping 30, 60, 120 and 240 seconds run twice, once per inventory. Whenever the upstream answers 429 the job cannot physically finish.

This ranks below everything else in this file. A false report at least arrives and can be doubted. A cancelled job sends nothing, writes nothing legible, and shows up in a list as a grey icon among green ones. Nobody disbelieves it, because it never says anything.

Retrying now stops at a deadline sized to leave room for the report, and the backoff sleep is clamped to whatever is left of it, since sleeping 480 seconds with 100 remaining makes a cap decorative.

One detail is a small lesson on its own. The comment first written next to the new deadline said the retries totalled 930 seconds. Mutating the cap made the test print the real figure, 450: five attempts sleep four times, not five. **The number was wrong in the very comment justifying the fix**, and it was the test, not the reasoning, that produced the correction.

### D1f. Counting the instances
Following the shape rather than the incidents, the same collapse turned up six times across two programs that do the same job:

1. An empty inventory indistinguishable from an unreachable one.
2. The report layer recomputing it a level up, after (1) was fixed.
3. The credential check, written after (1) was diagnosed, where unreadable and healthy returned the same answer.
4. The monthly report, which builds its message inline and never touches the guarded formatters.
5. The watcher, which compares item counts and read a refused fetch as "-369 item(s)": a theft alert for a read failure.
6. The pricing loop, one level below all of them, where an item whose price did not arrive counts as scanned and contributes zero. A healthy run leaves seven of 692 unpriced; if the price source falls over, the portfolio shrinks and no counter moves.

The sibling program had its own copy of (1) and of the partial case, the second one left open for a day after the first was closed, in a fix written by the same process on the same morning.

Two thresholds here were taken from the run history rather than invented, and both times the data contradicted the number that sounded right. A healthy harvest analyses 128 names of 177, so an absolute floor would have rejected normal runs; the guard compares against the last successful run instead. A healthy scan leaves about one percent of items unpriced, so the twenty percent trigger is twenty times the observed rate rather than a figure that felt safe.

**Where the boundary is, is the only question worth asking.** Each fix above was correct and none of them generalised, because each was aimed at a place rather than at a shape.

### D1g. Enumerating the question instead of patching the answer
After the fifth instance, the method changed: instead of fixing the query that had just bitten, list every query that asks the same question and every place a status field is written. That found three more, two of them live.

- **The weekly comparison.** Fixing the "latest measurement" lookup left its sibling, which asks the same thing about a different date, unfiltered. On the real database it would have compared the last true valuation against a zero written during the outage and announced a gain from nothing, the -100% bug reflected. Sunday would have delivered it.
- **The dashboard's recent-runs table.** It showed those zeros as "ok" beside "$0.00", reading a flag the binary of the time never set. Hiding them would be the opposite lie, so they are labelled unreadable and the money column shows a dash. One of the five queries deliberately reads the unreadable rows to count consecutive bad days; it was left alone, which is the point of enumerating rather than filtering everything.
- **A boolean that only ever went up.** In the other daemon, `connected` was set true when the socket opened and assigned nowhere else, so the panel reported "connected" from the first dial until the process restarted. A status that cannot say the bad thing is not a status.

Two of these had been sitting behind fixes made hours earlier by the same process, aimed at the place rather than the shape.

**Testability turned out to be part of the defect.** The weekly report always sent, so its only output channel was the operator's phone: the only way to see what it said was to publish it. That is why a baseline bug lived in it unseen. A flag that prints instead of sending costs one line, and with it the corrected report could be read straight off the board before anyone received it.

### D1h. The tool that decides what gets deleted
The audit lens was finally turned on the survey tool itself, the one whose HTML table is read to decide which directories can go. Its git helper returned an empty string both when git said nothing and when git could not run, so a repository whose status was unreadable rendered as **"0 changed"** and was counted among the clean ones in the summary line.

That is the same collapse as everywhere else, in the one place where the consequence is deleting work rather than misreporting it. It was found hours after spending an evening discovering uncommitted changes sitting in five separate projects, any of which a wrong zero would have hidden.

An unreadable checkout now says so, in the colour reserved for work at risk, and the summary counts it in neither column. The mutation that restores the old helper prints the old answer verbatim: `dirty: 0, unreadable: False`.

**Nine instances now, across five programs**, three of them written or last touched by the process that then failed to see the pattern in its own output. The ninth is in D2b, and it is the one with teeth: a backup script reading "the key is not here" as "there is no key yet", where the consequence is not a wrong number on a screen but an archive nobody can open. The lens works; what took this long was pointing it at things that were not currently on fire.

### D2. A backup verifying clean on two thirds of a machine
Daily, encrypted, pushed, size stable for seventeen days, restore check green. The manifest described the machine as it had been months earlier. Everything added since, including a non-reproducible price history, a live session file, credentials, the DNS configuration and every maintenance script, was absent from every archive.

A backup that fails loudly gets fixed. A backup that succeeds on a stale scope is trusted until the day it is needed.

### D2b. Why the scope went stale, and the recovery path that would have destroyed the archive
The scope was audited again against the live machine. It had drifted in both directions: four paths in the manifest no longer existed on the board, and nine live ones were covered by nothing, including the file holding the bot's credentials and the account file of a farmer whose sessions cannot be regenerated. The credentials had been moved out of the program and into their own file in May, for good reasons; the manifest kept describing the machine as it had been before that.

The mechanism is worth more than the list. The remote side skips a path that is not there, in silence. So a manifest that has stopped describing the machine prints exactly like one that still does, and the drift costs nothing visible until a restore. Absent and backed-up now print differently, and the four dead entries were removed rather than left to make that report cry wolf. The archive went from twenty-three files to thirty-two, verified by decrypting the last one made before the change and the one made after, and counting both.

**The larger find was in the recovery path.** The script generated a fresh encryption key whenever the keyfile was not found. A missing keyfile has two meanings: nothing to lose yet, or the key is missing *from here*, which is what happened when the script was run from a shell where the Windows path to it does not resolve. In the second case it would have encrypted every future backup with a key that opens none of the existing archives, printed success, and kept doing so daily until someone tried to restore. The keyfile survived by luck, not by design. It now refuses when archives exist, and still generates on an empty series; both branches were exercised.

The same collapse as D1 and its seven relatives, in the one program whose entire purpose is to still be correct on the worst day. **A tool that protects against loss has to be read as capable of causing it.**

### D3. RETRACTED. A realtime protocol migration that did not happen
This entry claimed a public streaming platform had moved off its hosted message bus, on the evidence that an application key returned "not in this cluster" on every region. The key had been rotated. The platform still uses that bus. See E17.

The entry is left in place rather than deleted, because a report about unverified beliefs that quietly removes its own is worth less than one that shows the correction. What survives of it is narrower and still true: **client code pointing at a dead endpoint fails silently when it has a fallback path**, which is how the key stayed dead long enough to be mistaken for a migration.

### D6. Progression credited by an announced event, not by a held connection
The same platform grants watch-time progression on an explicit event the player posts every thirty seconds, naming the channel and the live stream. Holding the viewer socket open credits nothing. Subscribing to the stream's message-bus channel credits nothing. Both together, on a logged-in account, credited exactly zero over half an hour, which is the measurement that should have been taken first.

Two things made it findable once the socket theories were dead. The client bundle names its own behaviour, so searching it for what fires during playback returned the call in minutes after months of reasoning about which connection mattered. And the endpoint's validator is documentation that cannot go stale: a missing CSRF header, a flat object and a wrapped object each came back naming what was wrong, and the fourth attempt was accepted. Four requests, no guessing.

### D7. Forty-seven exit codes lost upstream of something irreversible
Asked why the documented errors were never worked on directly, the honest answer was that this ledger had only ever been an output. It was written, published, and loaded into memory at the start of every session, and it stopped nothing: E27 was committed minutes after re-reading the warning against it in the file being edited.

So the errors were treated as a specification instead. Two of them have a signature visible in the command text, and a matcher for those shapes now runs outside the process that keeps making them. It was measured, not assumed: 5084 Bash commands were extracted from 617 real session transcripts and every rule run against all of them.

That measurement returned a finding nobody had asked for. **A verifier's exit code was piped away and then chained into an irreversible action 47 times**, and into an explicit claim that the check had passed 19 more. E18 and E20 were not two accidents; they were the two instances that happened to be noticed. The same shape had been running all along at roughly one command in a hundred.

A third rule was written for the case where staging the whole tree sweeps in someone else's work, and dropped. It fired on 117 commands that were almost all fine, because whether that command is dangerous depends on what the repository holds at that moment and not on anything in the text. Shipping it would have taught its reader to skim past the other two. **A guard is not free to be approximately right: the cost of a false alarm is the credibility of every true one.**

What this does not do is make anyone better. It is a net, placed where the same three shapes keep arriving.

### D4. Credentials committed in a private repository
Two bot tokens in the current checkout, not merely in history. Private, so not a public leak, but a private repository is one setting away from public and history rewriting never un-leaks anything.

### D5. Unbounded growth inside a bounded retention window
A trend file grew nineteen times in seventy days while its retention policy worked correctly. Retention bounded the age of the data, not the width of the universe being sampled. The file now costs more to load than the board can comfortably afford.

## Counting

Twenty-six agent errors: one a repeat of another written down hours earlier, one a fresh instance of the very failure class the report is built around, one (E17) whose consequence was to plant a false entry in this document's own findings section, one (E18) that broke the credential gate for the third distinct reason minutes after the same session finished documenting the second, one (E19) that obeyed a twice-written rule to the letter and caused the exact damage the rule exists to prevent, one (E20) that broke the same plumbing rule as E18 within hours of writing it down, on a check whose input did not even exist, one (E21) in which the mutation testing this session leans on reported twice that a guard was untested, having silently failed to mutate anything, two (E22, E23) that landed within an hour of each other on a question the operator asked directly, two more (E24, E25) in the feature built to answer it, one (E26) in the tool written to stop E24 happening again, which opened with a two-thirds false-positive rate, one (E27) that repeated E20 and E21 a third time, minutes after reading the written warning against it in the file it was editing, and one (E28) in the health tool itself, wrong on both of the two questions it was audited on.

Thirty, and the distribution says more than the total. Four of them (E20, E21, E27, E30) are one defect repeated: a verification step that quietly did nothing and returned a confident answer. Add the gate that failed open (E18), the checker that opened at a two-thirds false-positive rate (E26), the id read through a channel known to corrupt it (E19), and the health tool that reported a hundred phantom files and a session it had never measured (E28), and **eight of the thirty are in the checking apparatus rather than in the work being checked. Eight of the last thirteen.** An agent that writes its own tests grades its own homework, and these are the marks it gave itself.

The direction of travel is the finding. The work these tools watch is in better shape than it has been; the tools watching it are where the defects now live, and they are harder to see because their output is a clean report rather than a crash. Every one of E26, E27 and E28 was caught the same way: by asking the same question through a channel that could disagree.

E22 deserves the last word. The agent searched a live inventory for a phrase, found nothing, and reported nothing was there. Four items were. The phrase it searched for was one it had made up; the real one differs by two words. That is the failure this entire document is about, committed the morning after the rule was written down, published, and stored in the memory that loads at the start of every session. **It fired against tools all day and did not fire against a string the agent had invented itself.** The correction offered first was also wrong, blaming a language setting that had nothing to do with it.

What makes it worth the space is what it was hiding. The deduction resting on the false observation was correct: those items were being dropped from the inventory entirely, so every purchase went missing for a week and then arrived as an unexplained jump. A comfortable wrong answer to "is anything held right now" kept a real defect out of view, and it took the operator answering "FAUX" to move it.

E18 and E19 rhyme, and the rhyme is the finding. Both are correct components joined by plumbing nobody was watching: a scanner that found something, wired to a decision through a pipe that dropped its exit code; a rule that says kill by id, fed an id from a channel already known to corrupt its arguments. **The defect was never in the part under scrutiny.** A rule attached to a step protects that step only, and every one of these sessions has spent more of its damage on the joints than on the parts.

Two were caught by desk reasoning alone (E2 from reading a schema, E3 from auditing against documentation). E4 was caught by live instrumentation, which an earlier version of this section miscounted as reasoning, and which the taxonomy in RESEARCH.md had classified correctly all along. The two documents contradicted each other about the report's own methodology until an outside audit noticed. Four would have shipped broken behaviour to a user (E2, E4, E5, E7). Three were caught by reasoning rather than by tests (E2, E3, E4). One was caught by tests the agent had written (E13, twice). One was operational damage to a live machine (E9).

The ratio worth staring at: **zero of the four shipping-grade defects were caught by the agent's own test suite**, and every one of them lived at a boundary with something the agent could not run.

E16 sits outside that count and costs more than all of it. Every error above is a belief that met no evidence, or met evidence and was corrected. E16 is a belief that met evidence, was confirmed by it, and was wrong anyway, because the evidence had a second cause nobody had ruled out. No amount of contact with the world fixes that on its own. What fixes it is holding one channel where only your own action can move the number, and checking that it moves when you act and stops when you stop.
