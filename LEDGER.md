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

### E31. Explained a symptom that was never characterised, with a mechanism that was never measured
**Severity: low in consequence, high in what it says about the method.** Told that a machine felt slow, the agent went straight to measuring disks, found the system volume at 98 percent, and delivered a causal account: these drives are QLC with a dynamic write cache, the cache shrinks as the disk fills, therefore filling it does not cost a little performance but collapses it.

Every clause of that is true in general and none of it had been measured on this machine. When a write benchmark was finally run, the volume wrote at 1606 MB/s, which is healthy. The mechanism was real, plausible, well-matched to the complaint, and not what was happening.

Underneath it sits the larger fault. **The symptom was never characterised before it was explained.** Nobody asked when it was slow, in what application, doing what, or how far from normal. "Slow" was accepted as an observation when it was a report, and the search went looking for something wrong on a machine where something is always wrong: a full disk is a real finding and a satisfying one, which is exactly why it was seized. Hours later the operator said the machine was not slow at all.

**Caught by:** running the benchmark, which was only run because the claim had been stated confidently enough to be worth checking. Then by the operator, flatly: *tu fais de fausses assumptions*.
**Class:** related to E16 but not the same. E16 was a belief confirmed by evidence that had a second cause. This is a belief that met no evidence at all and was dressed as a conclusion because the mechanism was textbook. **A plausible mechanism is a hypothesis, and stating it in the indicative turns it into a finding without anything being learned.**
**What survives:** the disk really was at 98 percent, and the page file really did peak at 13.8 GB, so memory really did run out at some point. Those are measurements. The causal story joining them to the complaint was not.

### E32. A board that was never checked, by the tool built to check the boards, for as long as it existed
**Severity: medium, and it had been running green the whole time.** The estate health tool covers two single-board machines. It resolves each board's ssh key as `~/.ssh/<key>`. One of those keys is in the Windows profile, the other only in the WSL one. So `nano` was probed on every run and `claw` was never probed on any run.

The tool reported this honestly. It printed `?` and the summary line said "2 non mesurables" at the bottom of twenty-five checks, under twenty-three `ok`. Nobody read it, including the agent that wrote it and ran it. **An unmeasurable that never changes is indistinguishable from a check that does not exist, and it is worse, because the check appears in the inventory.**

The detail that makes this one uncomfortable: the file's own module docstring says the ssh keys "live in WSL". It says so four lines above the constant that reads them from the Windows home. The correct fact was written down, in the same file, by the same process, and the code did the other thing. Writing it down is not the mechanism that makes it true.

Two further checks rode on the same failure. `clawd` (is the XP farmer running in exactly one instance) collapsed to `?`, and the screen-daemon freshness check never even reached the report. Restoring the key resolution turned six board controls green that had never once been evaluated — including the duplicate-instance guard, which is the only thing standing between the farmer and two copies of itself.

A second collapse sat behind the first. A missing key and an unreachable board both arrived at the caller as a failure and printed as `injoignable`, so the tool's one word for "this board is down" was also its word for "this workstation is not set up". Those now print differently: `non sonde` when the probe never happened, `injoignable` when it happened and failed.

**Caught by:** deciding that the two `?` lines were the only interesting output of a run that was otherwise entirely green, and chasing them instead of the twenty-three `ok`.
**Fix:** the key is located across both filesystems and the ssh is routed through `wsl` when only that side has it; an absent key returns a distinct "not probed" rather than a connection failure. Verified by the two boards and four dependent checks reporting measured values for the first time.
**Class:** the D1 family, one layer up. D1 was a guard that could not fire because the thing it guarded had collapsed entirely. This is a whole probe that could not fire, for months, while sitting in a list of checks that were passing. **The summary line "0 en echec" was true and meant almost nothing; the number that carried the information was the one nobody looked at.**

### E33. A defect confirmed on a metric that was measuring the operator
**Severity: none in the end, and it consumed the most careful part of the night.** A delegated agent came back with a defect it called confirmed: a Telegram bot on the board, process alive, its log file zero bytes, its state file last written twenty-two days ago. Alive but doing nothing for three weeks, in an estate whose most expensive entry is a bot that reported zero as truth for ten days. The shape matched perfectly.

The state file counts *wakes*, and a wake is logged when a human sends the bot a message. Its own history contains a twenty-day gap and a five-day gap. **The number was a measurement of how often the operator had opened Telegram, and it was read as a measurement of the bot's health.** Twenty-two days of silence from a bot nobody had messaged is the correct output.

The bot was in fact fine, and proving it took two attempts. The first probe listed established TCP connections and found none to Telegram, which fit the defect story exactly. It read `/proc/net/tcp`. The board reaches Telegram over IPv6, and those connections live in `/proc/net/tcp6`, a file the probe never opened. **Had the CPU sample not already shown the process consuming time every cycle, that absence would have been published as the confirmation.** E22 was concluding absence from a search for the wrong string; this is concluding absence from a search in the wrong file, one screen after re-reading E22.

**Caught by:** refusing to accept "confirmed defect" from a delegated agent without re-deriving it, then asking what the metric's expected cadence actually was before treating a flat line as a stall.
**Fix:** none in code. The finding is retracted. The bot holds two live connections to `api.telegram.org` and its CPU time advances every polling cycle.
**Class:** E31, arriving from a new direction. E31 explained a symptom that was never characterised. This accepted a *diagnosis* that was never characterised, from a subordinate, and delegation is what made it easy: the report arrived with evidence attached, in the vocabulary of the estate's own worst incident, which is exactly the form a wrong answer takes when it is going to be believed. **A delegated finding is a hypothesis with citations, and the citations are the part that makes it feel finished.**

### E34. The control run was the only thing separating a working check from a fake one
**Severity: none, caught in the same minute, recorded because of how close it was.** A new health control was written to compare the backup manifest against the machine. To earn its place it had to be seen going red, so it was run against three mutated manifests: the real bug reintroduced, a dead entry added, the manifest emptied.

All three came back not-green. Read on their own, that is three passes and a check that works.

A fourth run had been included against the unmutated file, and it came back not-green too. Every run had failed for one reason: the paths were in MSYS form and the Windows interpreter could not open any of them, so the tool answered "manifest not found" four times. **Three mutations detected and one control detected are the same output, and only the control says which one it is.** Without it the check would have been committed, believed, and would have reported the estate's backups healthy no matter what happened to them.

**Caught by:** the control run, and nothing else. There was no other signal in the output.
**Fix:** Windows paths, then the four runs separated into four distinct answers: green on the truth, red on the reintroduced bug, red on the dead entry, `?` on the unreadable manifest.
**Class:** E21, the mutation test that mutated nothing, inverted. There the mutation was inert and the test passed. Here the mutation was real and the *measurement apparatus* was inert. Both produce a green check with nothing behind it, and both are invisible without a case whose expected answer is "no finding". **A test suite with no negative control cannot distinguish detection from breakage.**

### E35. The document disagreed with itself about its own headline number, and both numbers were printed
**Severity: low in effect, structural in what it exposes.** The most cited incident in this repository is the bot that reported zero as a measurement. Three files said it ran for ten days. Two said eleven. Nobody had noticed, including through several passes whose stated purpose was auditing this record for accuracy.

The board settles it. Its scan log holds **eleven** `Scan complete: 0/0 items priced` lines, dated 21 to 31 July inclusive, each followed by `Report sent!`. Eleven days, eleven false reports. The two files saying eleven were counting database rows and were right; the three saying ten were repeating a summary of a summary.

**What makes it worth an entry:** this is the second time the narrative documents have been caught contradicting each other on a fact both were describing, after the earlier disagreement about how E4 was detected. Both times the contradiction survived because each document is internally consistent and nobody reads them side by side against the artifact. **A number that appears in five places has five chances to drift and one source of truth, and the source of truth was a `grep` away the entire time.**

**Caught by:** counting the lines on the machine rather than trusting any of the five prose copies.
**Fix:** all five now say eleven, and D1 carries the dates and the command that produces the count, so the next reader can check it in one command instead of choosing between two paragraphs.

### E36. Ten repositories reported in sync with a remote that was never contacted
**Severity: medium, and the check had never once been able to fail.** The estate tool compares each repository's `HEAD` against `@{u}` and prints `sync` when they match. `@{u}` is a local ref: a cached record of what this machine last heard from the server. Nothing in the tool fetches. **The comparison was between the repository and its own copy of the answer, and two values from the same source cannot disagree.**

Demonstrated rather than argued: a scratch clone, a second clone that pushes a commit, and the check pronounces `sync` while `ls-remote` shows the remote two commits ahead. The same repository, the same command, run again after a `fetch`, correctly reports `DIVERGE`. Nothing changed but whether the machine had asked.

The practical consequence is precise. The check exists to answer "is any of this work only on this disk", and it would have answered "no, everything is pushed" for a repository whose remote had moved, forever, without any state on the machine ever becoming inconsistent.

**Caught by:** a delegated adversarial pass, given one instruction: for each control, construct the case where it prints `ok` while the thing is broken. That instruction found this in the second control it examined.
**Fix:** `ls-remote` asks the server and writes nothing locally. Offline is now `distant injoignable` reported as unmeasured, not as `sync`. Verified in both directions: red when the remote is genuinely ahead, green after the pull, on the same repository within one minute.
**Class:** E32's twin, and arguably worse. E32 was a probe that never ran and said `?`. This one ran, every time, and produced a confident green from a tautology. **A check that compares a thing to itself is not a weak check, it is not a check.**

### E37. Shipped the space-splitting bug into the checker written against silent drift
**Severity: none, caught within the hour, and it is the third time this exact byte has done this.** The backup-scope control built the remote command by joining the manifest with spaces: `for p in /etc/passwd /etc/my config.conf`. Any path containing a space stops being a path and becomes two.

Both outcomes are bad and one is invisible. The fragments produce a permanent false `DEAD` for a path that never existed, which is alarm fatigue in a report whose entire value is being short and trustworthy. And the real file is then never tested at all, so if it genuinely vanished from the board the control would not notice, while still printing a failure about something else.

This repository already contains two entries about splitting on spaces: a directory literally named `02 - Projects` broke a path detector, and a merged stderr stream turned twenty-three warnings into twenty-three filenames. Both are in the same file this control was added to.

**Caught by:** the same delegated adversarial pass, which mocked the ssh transport and read the command that would have been sent, rather than running it against the board where every real path happens to be space-free and it would have passed.
**Fix:** both lists cross the wire base64-encoded, one entry per line, read back with `read -r`. Verified with a manifest entry containing spaces: one dead entry reported, under its full name.
**Class:** E27 and E30, the errors committed inside the guard written against that error. What is new is the delivery: this was found by testing the *message* rather than the outcome. The board would have said green.

### E38. The probe wrote into the log that the next probe read as evidence
**Severity: low, and it is the cleanest closed loop in this record.** An audit of the inventory bot ran its regression suite. The suite imports `main`, and `main` configured logging at module level, attaching a file handler to the production journal. So the test run appended to that journal a sequence of rate-limit warnings and a `Surveillance annulee: fetch echoue pour CS2, RUST`, against a fabricated URL, using the same logger name, level and format as a real incident.

An hour later a second audit, of the estate's scheduled jobs, found the bot's Windows task disabled and its journal modified more recently than that task had ever run. It reported, correctly from what it could see, that some other trigger must be producing the log. There is no other trigger. **The first probe manufactured the evidence the second one reasoned from, and both were behaving properly.**

The loop closed only because the fabricated URL is visible in the log line and does not exist. Had the fixture used a plausible hostname, the conclusion "an unknown scheduler is running this job" would have gone into a report and been believed, and nothing in the estate could have contradicted it.

**Caught by:** reading the log content rather than accepting the delegated conclusion about the log's timestamp.
**Fix:** logging setup moved under `__main__`. Verified in both directions: the suite now writes zero bytes to the journal, and a real invocation still writes it, confirmed by size before and after each.
**Class:** E9 restated at the level of records rather than resources. E9 was a measurement heavy enough to disturb the machine it measured. This is a measurement that wrote into the machine's memory of itself. **The probe is part of the system, and a journal is part of the system too.** A test suite that cannot be told apart from production in the artifact a human reads is not a test suite, it is a second writer.

### E39. The probe took down the daemon it was written to watch
**Severity: real, two minutes of production downtime, and the tests were green.** The attribution measurement of D17 runs at startup, before the poll loop. The TLS client each account uses is built at the top of that loop. So the probe called into the HTTP path on a runner whose client was still `nil`, dereferenced it, and the daemon died on its first real start.

Three tests shipped with that code. All three covered the pure comparison helpers: does a gain during downtime read as non-exclusive, does an unreadable state file read as unknown, does the file round-trip. Every one of them passed, then and now. **Not one of them called the only function that runs on the board.** The function with no coverage was the function with the side effects, which is the ordering that always happens when coverage follows what is easy to write.

The immediate cause is dull: an object built from three fields where the working code path builds four. What makes it worth an entry is that it was written *during* a session whose entire subject is probes that lie, in a file whose own docstring says a probe that kills what it observes is worse than no probe. That sentence was in the commit that crashed the board.

**Caught by:** the daemon not being there afterwards. No test, no review, no alert. The `ps` count in the deployment script, which existed only because an earlier step that night had shown a stop command silently doing nothing.
**Fix:** the probe builds its own client and skips an account it cannot build one for; and the HTTP helper returns "no response" instead of dereferencing a nil client, so a caller that forgets loses a measurement rather than the process. A test now calls `checkAttribution` with exactly the object `main` builds. It reproduces the panic against the previous commit and passes against the fix.
**Class:** E9 and E38 again, and worse than both. E9 was a measurement heavy enough to disturb the machine. E38 was a measurement that wrote into the record it then read. This one is a measurement that stopped the thing being measured. **The estate now has three instances of the probe damaging the system, which is enough to stop calling it a coincidence: anything added to observe production is production.**

### E40. A stop command that stopped nothing and reported success
**Severity: low alone, and it is why the first deployment silently did nothing.** The board's init script for the farming daemon has a `start` and no `stop`. Calling `stop` on it therefore matches no case, does nothing, and exits **0**.

The deployment used it, saw success, replaced the binary underneath a process that was still running, called `start`, and watched the keepalive decline because a daemon was already up. Everything reported fine. The version string queried afterwards came from the file on disk, not from the running process, so even that agreed. What gave it away was `/proc/<pid>/exe` reading `/root/clawd/clawd-riscv64 (deleted)`: the old process, holding the old inode, still farming.

**Fix in procedure, applied immediately:** stop by pid, poll `/proc/<pid>` until it disappears, refuse to continue while any instance survives, and verify the deployed checksum on the board before swapping anything. Every later step of that deployment used it.
**Class:** E11 turned inside out. There the failure was killing by name and hitting the wrong thing; here it is asking politely and hitting nothing, with the same exit code either way. **A command whose success and its no-op are the same value is not a command, it is a comment.**

### E41. A probe that reported the DNS blocklist did not exist, minutes after installing it
**Severity: none to the estate, and it is the entry this record was missing.** The closing check of the session asked the board how many domains were blocked. It answered:

```
grep: /etc/hosts.blocklist: No such file or directory
```

Read straight, that says the file replaced an hour earlier had vanished and the house was no longer blocking anything. It was written down as a live incident before anything else was run.

The file was there the whole time: 2,978,616 bytes, the 99,276-domain list installed at 06:38, with `doubleclick.net` still resolving to nothing. The command had crossed Git Bash, then WSL, then ssh, then the board's shell, carrying double quotes nested inside double quotes. The outer layer consumed them, the remote shell re-split the arguments, and `grep` was handed something that was not the path. Reproduced deterministically: the nested form fails, single quotes return `99276`, base64 returns `99276`.

**Every other instrument failure in this record lies toward reassurance.** A board never probed prints `?` under green. A sync check compares a repository to itself and says `sync`. An auditor that cannot read a file says `clean`. A blocklist script installs an error page and logs `OK`. This one lies the other way, and it is worth its own entry because the defence against it is different. A reassuring lie is caught by going and looking. **An alarming lie is caught by not believing your own tools first**, and it is much easier to act on, because alarm feels like diligence and the reflex is to fix the estate rather than to re-run the measurement.

The failure mode is also the nastier of the two in one respect: it is not a syntax error, a stack trace, or an empty result. It is a specific, plausible, well-formed factual claim about production, from a tool that had been right all morning.

**Caught by:** re-running the same question through the base64 path, which this project's own notes have prescribed for exactly this reason since before the session started, and which the failing command had skipped because it was one line.
**Fix:** none in the estate. The rule already existed and was not followed: anything crossing the Windows, WSL and board shells goes over as base64, always, including the one-liner at the end when everything is finished.

### E42. A documentation claim invented one turn after the rule restating it had just shipped
**Severity: low in the artifact, telling in the timing.** A README edit for the drops miner added "seven languages, picked from your system locale." No locale detection exists anywhere in that repository: `config.py` hardcodes English, and only the settings dropdown changes it. The sentence was written from what a desktop app usually does, not from what this one does, and it was published.

What earns it an entry of its own rather than a footnote is when it happened. It was written in the same hour as three corrections running the other way, where reading the source killed a plausible sentence before it shipped: an API table listing four connection states the gateway never emits, a `go install` line the module path makes impossible, a "160p" that is off by default. Three caught, one not — and the one that got through was the only claim nobody thought to check, because it read as a fact about the interface rather than about the protocol, and the session's own scrutiny had been aimed at protocols all day.

**Caught by:** a subagent instructed to build or run each project and cite file and line for every claim, rather than to read the README and judge whether it sounded right.
**Fix:** the line was removed; there being no locale detection to describe correctly.
**Class:** E15 and E31 combined. A claim taken on the strength of how ordinary it sounds, written by the same process that had just finished demonstrating it knew better.

### E43. Five sixths of a repository's advertised languages were never read
**Severity: medium, silent, and live.** Chasing the claim behind E42 found a second, real defect under it. `APP_DIR` resolved to `utils/` when the program ran from source, so the language loader scanned `utils/locales`, found nothing there, and returned an empty table. Five of the seven shipped translations were never loaded by the running code.

Nothing looked broken, which is the point. A missing language falls back to the French table rather than to the raw key, so selecting German rendered the interface fully in French: every string translated, into the wrong language, with no error anywhere a user or a log would show one. Eight interface keys did render as raw identifiers under the working two languages, and even those had been sitting unremarked in the shipped interface.

**Caught by:** the same file-and-line audit that found E42, tracing the "seven languages" claim into the loader instead of accepting the README's number.
**Fix:** `APP_DIR` resolution corrected; a check added that every language file on disk is actually loaded, and that every key the interface requests resolves in all seven. Verified both ways: reintroducing the path bug turns the check red, restoring the fix turns it green.
**Class:** D1's shape in a UI rather than a bot. A fallback that produces a complete, well-formed, wrong answer is indistinguishable from a correct one at every layer that isn't the one comparing against the key.

### E44. The test suite that should have caught E43 imported modules that no longer existed
**Severity: medium.** The repository carried a `tests/` directory. Its test file imported `core.kick` and `core.store`, modules that had not existed for some time under those names. The suite failed at import, before a single test ran, and had been doing so for long enough that the language-loading defect in E43 lived under it the whole time.

A failing import and a passing suite of zero tests produce different exit codes, but nothing in the ordinary workflow was reading the exit code; the presence of a `tests/` directory was doing the reassuring, not its result.

**Caught by:** the same audit, told to run the project rather than to read that it had tests.
**Fix:** imports corrected to the current module paths; the suite now runs and includes the E43 coverage.
**Class:** E43 in the meta-repository, the tool built to catch this failure mode. See D10 for the same collapse in this estate's own auditors.

### E45. One navigation out of seven skipped the guard the README uses as its main selling point
**Severity: medium, and it undercuts the repository's central claim.** The drops miner's privacy section states that every HTTP request and every Chrome navigation passes through `assert_allowed()`, a single choke point meant to guarantee the browser never goes anywhere but Kick. Six of the seven call sites do. The seventh, the sign-in window, called `driver.get()` directly with a raw queue URL, unchecked.

A malformed or non-Kick entry reaching that path would have opened the sign-in window at an arbitrary address, which is exactly the outcome the guard exists to make impossible, and the one sentence in the README a cautious reader would trust without checking is the one that was not quite true.

**Caught by:** the same per-call-site audit, checking the claim against all seven sites rather than against a sample.
**Fix:** the sign-in navigation now routes through `assert_allowed()` like the other six. Witnessed against both an allowed URL and a blocked one, so the guard is shown to pass and to refuse, not merely to be present.
**Class:** E19, obeying the letter of an internal rule while missing one of the places it applies.

### E46. The ledger's own numbering collided with itself, silently, for six days
**Severity: none in consequence, structural in what it says about unchecked self-reference.** E42 through E45 above were first recorded on 2026-08-03, in CHANGELOG.md, as prose narrating a session — and there labelled E41 through E44. E41 was already taken: it names the DNS blocklist entry earlier in this file, written the day before. The four new findings were never given real entries here. For six days, this ledger's own index disagreed with the document that cites it, and nothing compared the two.

The mechanism is the same one this file keeps finding elsewhere: a number written down was trusted as a fact rather than checked against the one canonical list it was supposed to belong to. CHANGELOG.md is the narrative log; LEDGER.md is the numbered catalog the narrative is supposed to cite, not duplicate independently. Nothing enforced that the two stayed in agreement, so a session that ran without access to this file's current tail picked the next number it assumed was free.

**Caught by:** reconciling the two files by hand while adding entries for E42-E45, and noticing the citations in CHANGELOG.md's prose did not resolve to anything here.
**Fix:** the four findings given real, currently-unused numbers (E42-E45) and full entries in this file. CHANGELOG.md's prose still reads "E41" through "E44" in place for the historical record of what that session wrote and believed at the time; it is not silently rewritten, because a log that edits its own past to match a later correction stops being a record of what happened.
**Class:** E35, one level up. E35 was this document disagreeing with itself about a headline number. This is the document disagreeing with itself about the numbers it uses to refer to its own entries — the index checking nothing about the thing it indexes.

### E47. The health tool's own subprocess calls decoded a different alphabet than the one arriving over the wire
**Severity: medium, and it had been silently wrong since the tool existed.** `run()` called `subprocess.run(..., text=True)` with no `encoding=` argument. Python's default in that case is `locale.getpreferredencoding()`, which on this machine is cp1252. Everything ssh and git actually send is UTF-8. Any byte sequence outside plain ASCII — an em dash, an accented letter — was silently decoded under the wrong table before a single line of this file's own logic ever saw it.

Live consequence, not a theoretical gap: the Steam cookie classifier looks for a literal em dash in the board's own log line. Over cp1252 that dash arrived as a replacement character, matched nothing, and a session with one full day left — measured minutes after a real scan had completed successfully — reported as `sortie non reconnue`. The classifier was correct; the bytes it was handed were already wrong by the time they reached it.

**Caught by:** re-running the exact command the classifier uses by hand, seeing the same em dash render correctly in a terminal, and asking why the two didn't agree — then reproducing the mismatch directly: `subprocess.run(["python","-c","print(chr(0x2014))"], text=True)` on this machine returns a replacement character, not an em dash.
**Fix:** `encoding="utf-8", errors="replace"` on the one subprocess call every check in this file routes through. `errors="replace"` rather than a strict decode, because a check that crashes on one stray byte is worse than a check that loses one byte and keeps going — the file's founding rule, applied to itself.
**Class:** E12, the shell-boundary path-form bug, one layer down: not the shape of an argument crossing a boundary, but the alphabet of the bytes crossing it. Both are invisible until the specific byte that exposes them shows up, and both were caught by refusing to believe a plausible-looking mismatch without re-deriving it by hand.

### E48. A scheduled task's own "still running" code was read as a failure
**Severity: low, and a clean instance of collapsing three answers into two.** `CS2SkinRadar-Asia` reported `dernier code 267009` as FAIL. 267009 is `0x41301`, `SCHED_S_TASK_RUNNING` — the Windows Task Scheduler's own code for "this run has not finished," not an error of any kind. The task's own `Status` field said `Running`; it had started that morning and was still inside its configured two-hour stop-after window. One region simply took longer than the other two that run.

The check's logic had a two-way branch where the outcome needed three: succeeded, failed, or not yet decided. A non-zero code fell into the same bucket regardless of which of those it meant, and the one code that means "ask again later" was read as the same thing as a code that means "this broke."

**Caught by:** looking up what 267009 actually is instead of trusting that a non-zero exit code is by definition a failure — the same discipline this estate keeps having to relearn about probes, applied to a number instead of a claim.
**Fix:** `267009` gets its own branch, reported UNKNOWN with the recorded start time. Verified live, before and after, against the same task: FAIL, then correctly UNKNOWN, on a run that was in fact still in progress both times. No synthetic selftest exists for this check; it has always been verified against the real scheduler, and was here too.
**Class:** the estate's oldest lesson, still finding new call sites. "Could not measure yet" and "measured, broken" are different answers, and a checker that only has room for two will eventually put one where the other belongs.

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

### E49. A Firefox build left in a shared output folder killed the operator's live extension
**Severity: high, and the probe broke the system it was measuring.** Mid-round, the operator reported that translation had stopped and the toolbar button was inert. The console said `Could not establish connection. Receiving end does not exist.` The content script was alive and had processed 26 lines out of 36. The service worker was dead.

The cause was a shared path. `npm run build:firefox` writes into the same `dist/` as `npm run build`, and the final validation of the two preceding rounds each ended on `build:firefox`, so the folder the operator's Chrome loads from held a Firefox build. An MV3 service worker is restarted constantly and re-reads its file from disk, so at its first restart it found no valid Chrome service worker entry and never came back.

**The fuse and the damage are two rounds apart.** The commands that broke the extension ran in rounds 9 and 10; the extension went down in round 11, in a browser no machine node inhabits, and was reported by the person using it.

**Caught by:** the operator, using the product. No machine node saw it and none could: the corrupted folder is on the operator's disk and a dead worker is only visible in a browser session neither machine node has.
**Fix:** reloading the extension, `dist/` having already been rewritten as a Chrome build by the setup's own `release:check`. Verified after the fact by watching translations arrive across eight samples, 2 then 5, 6, 8, 9, with the loading indicators cycling. The rule was written the same round: any sequence that runs `build:firefox` must end on `npm run build`. It was broken again, see E53.
**Class:** D17's lesson with a delay fitted to it. A probe is part of the system it measures, and when the probe's output shares a mutable path with the product, the probe is not an observation but an edit. The delay is what made it hard: the session that broke the extension was not the session that ran the command.

### E50. Fifteen seconds of a channel that had gone quiet, read as a broken feature
**Severity: medium, and the operator refuted it in the same round.** After shipping a fix, the session declared that translation did not work. It was false. The claim rested on a single snapshot taken at 15 seconds, in a tab the session had itself created and which did not have focus, on a channel that had stopped emitting, so no message was arriving to be translated at all. The operator corrected it and was right.

The re-measurement is the control the first one lacked, and the contrast is the whole entry: repeated sampling over about 22 seconds on a live channel gave 31 lines, 31 processed, 16 translated, loading indicators cycling 2, 4, 3, 5, 0, with zero duplicates and zero errors. The first measurement did not disagree with this one. It had no content.

**Caught by:** the operator contradicting the report.
**Fix:** the rule recorded in place, that no "it does not work" may be concluded from a point measurement in an unfocused tab without first establishing that the data source is alive. A structural limit was recorded beside it: the session sees only the tabs it creates, never the operator's.
**Class:** E22, with the false negative manufactured by a sampling window instead of an invented substring. A probe that returns nothing is not evidence of nothing, and a channel that has gone silent renders exactly like a translator that has stopped.

### E51. The gate ran, was red, and guarded nothing, because the chain started at git add
**Severity: high, and the trap was already written down before it was walked into.** A commit went out over a red `release:check`. The shell chain began at `git add`, so the exit status that propagated belonged to the last command in the chain rather than to the check, and the gate's red never reached anything with the power to stop the commit. The round's own notes record that this trap had been described in an earlier brief and was hit anyway.

**Why nothing else caught it either:** the test witness stayed green under vitest while `tsc` was broken, because vitest does not typecheck. Only `release:check` sees that class of breakage. A cheap green witness was available and it was wrong, which is worse than having none.

**Caught by:** reading the round's own retrospective against the commit that followed it.
**Fix:** `42f16c9` removed the duplicate import that had broken the build. The method fault itself is recorded and not fixed: nothing structural prevents the next chain from beginning at `git add`.
**Class:** a gate whose exit code is not the exit code the shell propagates is decoration. This estate has the rule already and this is its instance in a second codebase: never place a gate where a later command can succeed on its behalf.

### E52. Four of the five places a language lives, three languages running
**Severity: medium, and the failure mode was a menu disagreeing with its own page.** Adding an interface language touches four display sites, `UI_LOCALES`, `UI_LOCALE_NAMES`, `UI_MESSAGES` and `scripts/i18n-check.mjs`, plus one authorisation site, the zod enum `uiLang` at `settings.ts:83`. The first four were done and the fifth missed, for three consecutive languages. The visible result was a menu showing one language while the page rendered another, because zod refused the new value and storage kept the last one it had accepted.

The two lists are duplicated deliberately, since importing `UI_LOCALES` into `settings.ts` would pull 67 KB of catalogue into the content script bundle. The duplication is a priced decision and is not the defect. The defect is that nothing asserted the two lists agreed, so the fifth site could fall behind the other four without any signal.

**Caught by:** the disagreement becoming visible in the options page, after three languages had already shipped carrying it.
**Fix:** a test that walks `UI_LOCALES` and requires the schema to accept every entry, plus the reverse direction. Witnessed red on exactly es, tr and ko before it was made green.
**Class:** when a value must be listed in several places and only some of them are load-bearing at write time, the others fail silently and later. The guard belongs on the invariant that the lists agree, not on remembering the procedure, which is E23's separation of two facts seen from the other side.

### E53. The rule written in round 11 was broken again in round 25
**Severity: medium, and it is the same folder as E49.** `dist/` was again left holding a Firefox build, the final `npm run build` having failed on the same duplicate import without the session noticing. The rule that any sequence running `build:firefox` must end on `npm run build` had been written into the record immediately after that same folder took the operator's extension down.

The two are about twenty-six hours apart, round 11 having started 2026-08-13 14:48Z and round 25's repair commit landing 2026-08-14 16:59Z. In between, the rule sat in a file that the second session had access to and no reason to reread.

**Caught by:** the round's own retrospective, which listed it as one of that round's method faults.
**Fix:** none structural. The rule remains a sentence in a document.
**Class:** a rule written into a journal is not a rule in force. It has no runtime, nothing consults it before the command runs, and the only thing between it and the next repeat is whether the session that read the journal is the session that runs the build. E56 is the same failure one level up, in how the rule was worded rather than whether it was enforced.

### E54. Three registers collided on numbering at once, and none of them said anything
**Severity: medium, silent, and it reproduces E46 in two further media.** E46 recorded that this ledger's own numbering collided with itself, silently, for six days. The studied campaign's registers did the same thing in parallel, none of them aware of the others.

In the journal, two sections are titled ROUND 15 and two are titled ROUND 22, written by different sessions. Beneath the two ROUND 22 headings sit two different ITEM 74 and two different ITEM 75 with unrelated contents. Two further item numbers collide across rounds. Four genuine collisions, against three apparent ones that turn out to be a success heading and a first-attempt heading narrated out of order.

In git, seven item numbers are carried by more than one commit. The sharpest is item 45: `1031257` "Stop handing the engine a source language that was only guessed" and `ae65813` "Count Korean letters written on their own as Korean", two minutes apart, unrelated work, the same number.

**The registers also disagree about what exists.** 68 distinct item numbers appear in the journal and 52 in git, of which 35 appear in both. 33 journalled numbers were never committed and 17 committed numbers were never journalled. Agreement across the union is 41.2%, and the journal is the register the system treats as its memory.

**Caught by:** counting headings by program rather than reading the files, then sweeping the journal for any line where a session had noticed. Twelve lines matched terms like collision, duplicate and numbering; none of them concerned round or item numbers. The search for a refutation was run before the claim was written, because "nobody noticed" is exactly the sort of claim that is easy to assert and cheap to check.
**Class:** E46 again, twice over. A numbering collision emits no signal because the register goes on reading normally afterwards, and the only detector is a program that counts. Nothing in a shared register tells a writer that another writer is in it.

### E55. Absence concluded from a search for the wrong identifier, again
**Severity: low in consequence, telling in that E22 is its published ancestor.** A setting was reported dead. It was not: `injector.ts:78` toggles a class on the document element and `inject.css` carries the matching rules, widened by a later item to cover third-party emote tokens. The conclusion had been reached by searching for the identifier and never for the class it drives.

The correction is recorded in place and dated, with the original claim struck through rather than deleted, which is why it is available to be counted here at all. A sister case appears in a later round, where a delegated agent reported three dead settings and verification corrected two of them.

**Caught by:** re-deriving the behaviour from its effect rather than from its name, on a later pass.
**Class:** E22 in a different codebase, and the distance is the point. E22 was published, written into memory, and the same shape still recurred against a different identifier in a different repository. What transfers is not the string but the method: search for the effect, not only for the name that is supposed to produce it.

### E56. A claim marked for verification was written down as measured, and it was false
**Severity: medium, and it happened inside this campaign's own working file.** The brief commissioning this work listed, among the things to check, that several round briefs prescribed `&&` while reminding the reader in the same document that the operator's PowerShell 5.1 does not have that operator. It was flagged as a case to verify. The working evidence file for this campaign then recorded it as measured, in the form "seven for seven", with per-file line citations attached.

It is not so. Each of the seven briefs contains exactly one line carrying `&&`, and that line is the warning itself. Seven briefs state the rule and none of them breaks it. The count was then re-run without the classifier's exclusion terms, to be sure the exclusion was not manufacturing its own answer: the total number of lines containing `&&` is one per brief, so there is no prescribed use hiding behind the filter.

**The direction of the error is the part worth keeping.** It turned a rule that worked into a rule that failed. A fabricated success is the thing everyone knows to guard against. This was a fabricated failure, and it is the easier one to believe, because a document that contradicts itself is a better story than a document that does not.

**Caught by:** counting the occurrences before publishing the entry that would have carried the claim. That entry had already been drafted from the working file.
**Class:** the same shape as E57 and E59, committed one step further along the chain by the same kind of node. A note that says "to verify" and a note that says "verified" are different objects, and nothing in a plain text file keeps them apart once the first has been copied into the second. The detector is re-derivation from the primary artifact. Rereading the evidence file would have confirmed the claim perfectly.

### E57. The brief stated as established what it had only received
**Severity: medium, and it is the cleanest single instance of an inherited claim.** A round brief asserted that since `9ce0f28` every query from the chat bar went through the panel that was on screen. False. `9ce0f28` "Mount the chat bar in the panel that is on screen" changed the mount and the remount guard, and six update functions still queried the whole document. The statement had arrived in a report, been rewritten as settled fact in the next brief, and travelled onward carrying no mark of its age or its source.

Refuted by measurement in the following round and corrected by `6db2630` "Route every bar update through the panel that is on screen", 2026-08-14 03:44. Residence: one round.

**Caught by:** the executing node re-deriving the claim from the commit instead of accepting the brief. Anyone can repeat it by reading `9ce0f28` and then `6db2630`.
**Class:** the detector here is neither a test nor contact with the world. Both nodes agreed, the code compiled, the tests passed, and nothing was measured against reality because nobody believed there was a question. What refuted it was returning to the primary artifact and deriving the claim a second time. The question that fires is not "is this true", and not "is this true because of something I did", but "do I know this, or did I inherit it".

### E58. A provenance was written for a decision that never had one
**Severity: low in the artifact, higher in what it does to a shared record.** A brief instructed that a custom dropdown be filed among the measured dead ends, as though a measurement had killed it. The executing node went looking for that measurement, found no trace of it anywhere in the record, and rewrote the entry around the evidence that does exist: item 70, where a single `color-scheme` property was sufficient, `8e62f3d` "Declare a colour scheme on every select we style", 2026-08-14 03:34.

**Caught by:** looking for the cited source before repeating the citation.
**Fix:** the entry rewritten around the evidence that exists rather than the evidence it claimed to rest on.
**Class:** a graveyard of rejected options is worth exactly the provenance of each burial. An option buried with an invented reason cannot be reopened by anyone who later has a better idea, because the record says the question was settled by measurement and the measurement is not there to inspect. E58 and E59 are one reflex pointed at two objects: this one invents a source, the other invents a number.

### E59. The count asserted and never derived, inside the document that defines that fault
**Severity: none in consequence, structural in what it says about unchecked self-reference.** The brief commissioning this campaign stated repeatedly that the studied campaign ran twenty-seven rounds. The number was never derived from anything. It came from informal counting across a conversation, was written down as established, and did so in the same document that names inherited-claim-as-fact a class of error worth a section of its own.

The record supports no single number, and that is the result rather than a failure to reach one. The journal carries 19 distinct round numbers between 4 and 26, two of them appearing twice and four missing, one of those four explicitly. Git carries 63 item commits on the integration branch, numbered up to 95. Seven briefs exist on disk. A round is a journal section, or a brief, or a session, or a range of commits, and those four definitions do not return the same figure. No replacement number is asserted here, because asserting one with the confidence of the first would be the same act performed twice.

Two smaller instances sit beside it. One brief had the next work begin at item 80 when the history already stood at 94. Another had a section written into the journal under a round number the journal had already passed. In both, the generating node projected its own count instead of having the machine's count read.

**Caught by:** a delegated extraction that counted the journal's sections. Not by proofreading, which had happened, and which cannot catch this class at all.
**Class:** re-derivation from the primary artifact, not rereading. Rereading establishes that a document says what it says. Only returning to the source establishes whether it is so. The fault produced a fresh instance of itself while its own definition was being written, which is the strongest evidence available that it is a live class rather than a tidy retrospective category.

### E60. Four claims about the record, refuted by counting them
**Severity: low individually, and together they are a measurement of the loop.** The commissioning brief made a number of checkable assertions about the two registers. Four did not survive contact with the files they described.

It said `D` entries were mixed into this ledger's agent errors section. They are not. The agent errors heading opens at line 7 and the environment discoveries heading at line 451, and every `E` heading sits above that boundary while every `D` heading sits below it. No interleaving exists.

It said the `D` series ran to at least D13. It runs to D17.

It named one item-number collision in the journal. There are four, and seven further item numbers are carried by more than one commit in git.

It read a line calling for a test that would prevent "the fourth recurrence" as evidence that a fourth had already happened, and concluded that the dossier contradicted itself. Three sources in the dossier give three occurrences and agree with one another; the line in question asks for a fourth to be prevented, not recorded. There is no contradiction.

**Caught by:** checking each assertion against the file it described, before using any of them downstream.
**Class:** E57 and E59's family, recorded separately because the count is the point. A node that consumed an artifact and reported back found four checkable errors in it, and E56 is a fifth. Section 6b argues that outbound verification has no natural trigger, because the loop closes where the author is not. When the recipient is another machine node that consumes the artifact and answers, the loop closes somewhere observable, and these five are the size of that effect in this dossier.

### E61. Three interface defects crossed both machine nodes and were caught by eye
**Severity: medium, user-facing, and the honest counterweight to anything the loop got right.** Three defects reached the operator: the gear pushed outside the chat bar, native menus rendering unreadably, and an odd label in the Debug tab. They came back in one sentence with three screenshots, and became items 70, 71 and 72, `8e62f3d`, `59c820f` and `65ae05e`, all landing between 03:34 and 03:41 on 2026-08-14.

The cause is measurable rather than inferred. The defects entered in the preceding round, through items 57 and 58, `d724999` and `012f115`, and that round's own record states that it produced no browser observation whatsoever and was entirely unit tests.

**The objection has to be instructed, because it is strong.** Could a machine node have seen these without eyes? Partly. `59c820f` says there is no layout engine in the test harness, so the tests read the stylesheet and pin the ordering rather than pixels, which means a width assertion was genuinely unavailable. But the same commit says the defect was measured in a live page rather than guessed: the panel is 340px, the bar wanted 365, and the gear sat at left 340 right 365, fully out of frame. A machine node did measure it, once it had been told where to look.

So the structural reading is too generous and is not taken here. The defect is not that no machine node can perceive rendered output. It is that the round which introduced all three ran no observation at all, having satisfied itself with a suite it had written. The fix commit closes with its own version of the same admission: unit tests only, never seen in a browser after the change.

**Class:** section 1 of the research restated at the scale of a whole round. A suite the agent wrote passing tells you the model is internally consistent, not that the product can be used. Recorded as a weaker claim than it first appeared, because the counter-evidence is in the dossier and leaving it out would have been easy.

### E62. The channel carrying every instruction was never tested at the size it would carry
**Severity: medium, two rounds lost, and each node saw a different half of it.** The generating node's account, which exists in no file, is that a brief of about twenty kilobytes pasted directly into the client crashed it twice, after which briefs moved to files and only a three-line pointer was pasted. Every brief on disk is a file, and the earliest of them is from the round where this is said to have happened, so the outcome is consistent with the account.

The executing node's record of what appears to be the same event says something adjacent and not identical. It states that the round 16 prompt arrived truncated twice, cut mid-word, after which the operator supplied the complete brief as a file. Same round, same count of two, same remedy, different failure.

**Neither account is wrong and neither is complete.** One node watched a client fall over. The other watched text arrive cut short. The failure sat on a boundary neither could observe from its own side, and the only reason both halves exist is that they were written down separately and later placed side by side. The crash remains attested by the generating node and unverifiable from any artifact. The truncation is in the record and can be checked.

**Caught by:** searching the record for the event the deposition described, and finding it filed under a different symptom.
**Class:** a transport carrying every instruction between two nodes had never been exercised at the size it would routinely carry, and it failed on the first document that was genuinely large. The second lesson is E54's from the other direction: two descriptions of one incident agreed on round, on count and on remedy while disagreeing about what actually happened, and neither node had any way to notice that they disagreed.

### E63. This repository's own inventory calls it public and links it, and the link is dead
**Severity: medium, reader-facing, and the file carrying it opens by promising the opposite.** `CHANGELOG.md` lists this repository among those created, as public and MIT, linking its GitHub page. An anonymous request for that page returns 404. The repository is private. The licence half of the claim is correct, the LICENSE file being present and MIT; the visibility half has been wrong for as long as the line has existed, and every document in this repository was written on the assumption that it was publicly readable.

The finding needed a control before it could be attributed, because a 404 can be a property of the request rather than of the target. Two other repositories from the same account, linked from the same file and genuinely public, return 200 to the identical client in the same run. `git ls-remote` against this one succeeds under the author's own credentials and reports `refs/heads/main`. So the page exists, the author reaches it, and nobody else does.

**What makes it worse than a broken link:** `CHANGELOG.md` opens by stating its own rule, that entries link to the artifact so each claim can be checked rather than believed. The single link a reader would follow to check the claim this file makes about itself is the one that fails, and it fails only for readers, never for the author. Every other claim in the file is checkable. The claim about its own availability is the exception.

**Caught by:** fetching the file's links from outside while preparing to add an entry to it. Nothing in this repository would have caught it: there is no CI here at all, and the link checker written after E24 lives in another repository and does not cover this file.
**Fix:** the line corrected to state the real visibility, and then the operator made the repository public on 2026-08-15. Verified afterwards from outside on six surfaces: the HTML page, the API reporting `visibility=public` and `private=false`, and raw fetches of two files, against the same public control repository that had been returning 200 throughout. The claim and the world now agree, which they had not done for the entry's entire existence before that.
**Class:** E24 committed by the document whose first rule is E24's lesson, and 6b at its purest. The author of an artifact is the one party who cannot experience it as its audience does, because their own access is never the access under test. A self-referential claim about availability is the one claim that verifying from inside cannot touch.

### E64. The forbidden-data sweep was scoped to what was written, not to what would be published
**Severity: medium, and it was caught with the exposure still at zero.** The second campaign ran a sweep for operator names, absolute paths, credentials and private repository names before every commit, with the detector witnessed failing on positive specimens first. It reported nothing, correctly, on every pass. It was pointed at the diff the agent had just written.

That is the wrong region and the error is in the question. Before publication the question is not "what did I add", it is "what will be readable". Rescoped to the whole tree, the same detector immediately finds four disclosures, all of them older than this campaign and none of them written by it: an operator username hardcoded in two path fallbacks in `healthcheck.py`, the two boards' RFC1918 addresses sitting next to the filenames of the SSH keys that reach them, and a private working repository's name inside a path constant.

**Severity is calibrated rather than announced.** No key material, no tokens, and RFC1918 addresses are not routable from outside the network they name. The username is the part that matters, because it links an identifier to the account publishing the repository.

**The window closed while this entry was being written, and that is recorded rather than smoothed over.** At discovery the exposure was nil, the repository being still private, checked on two independent surfaces with a cache buster. The operator made it public shortly afterwards, so the disclosure is now live and this stopped being a pre-publication finding. The paragraph above said "not an incident" and was published saying it, which was true when written and false within the hour. The correction is here rather than in place, because a ledger that edits its own past claims silently is worth less than one that shows them changing. Note also that removing the file now would not retract anything: the blob stays reachable in the history of a public repository, so the only real remedies are to stop the values being in the file at all, or to accept them as published.

**Caught by:** rescoping the sweep when the repository's visibility was said to have changed. That trigger is itself the defect. A sweep that only widens when someone mentions publishing is a sweep that depends on somebody remembering to mention it.

**Fix:** the values moved into a gitignored `estate.json`, read once at import. The board names stay in the file, because they are already throughout this record; only the addresses, the key filenames and the WSL roots left. The risk was that a missing config would silently drop rows from the report, which is the failure this same file already documents, so absence was made loud instead: a board with no entry keeps its row and reports UNKNOWN naming the missing config, and the version check refuses to guess a working directory rather than running `git log` somewhere arbitrary and comparing against an unrelated hash.

Verified both ways before committing, using the file's own selftest. With the config present: 11 cases, 0 failures, exit 0, and both keys resolve to exactly the paths they resolved to before, one native and one through WSL. With the config moved aside: exit 1, two explicit failures naming the absent configuration, and the rows still present. The gitignore entry was written before the file it protects, not after.

**What the fix does not do**, and this is the part worth keeping: the values remain in the history of a public repository. Cleaning the current file lowers how easily they are found. It retracts nothing. The only true remedies were never to publish them or to rewrite public history, and the second is an irreversible action on other people's clones, so it was left to the operator rather than taken.
**Class:** 4.2, guard placement, moved from order to scope. The sweep ran before the commit, which is the correct moment, and covered the wrong set. A guard can be correctly placed in time and still be aimed at the wrong region, and "before" is the property people check while "over what" is the one they assume. The general form: define a guard by the boundary it protects, not by the work that prompted it.

### E65. The gate rule was published, broken twenty minutes later, and caught by a hook rather than by the rule
**Severity: none in consequence, and it is the cleanest live instance this record contains.** E51 records a commit shipping over a red check because the shell chain began with `git add`, so the gate's exit status never reached anything able to stop it. E53 generalises that: a rule written into a journal is not a rule in force, because nothing consults it before the command runs.

Both entries were committed, and then, inside the same session and while verifying a change to this repository's own health tool, the agent ran the selftest piped into `tail` and read the pipeline's exit status as the check's. The same fault, against the same class, minutes after writing the entries that define it.

It never reached the record, because on this machine something does consult a rule before a command runs. A pre-execution hook refused the command and named the class back.

**Caught by:** the hook. Not the author, and not the two entries the author had written about this exact fault within the hour.
**Fix:** the verification re-run with the check's own exit status captured before any pipe, and the output read separately. Both directions were then witnessed, the configured case green and the unconfigured case red.
**Class:** E53's thesis demonstrated instead of argued. The distance between a rule written down and a rule in force is the distance between a document and a runtime, and the only thing that closed it here was a program standing before the action. Prose in a ledger did not stop the author of that ledger from committing the ledger's own subject twenty minutes after publishing it. This is also the answer to the question E53 left open, about what to do when a written rule keeps recurring: stop writing it and install it.

### E66. The audit written to enforce E64 measured the wrong tree
**Severity: medium, and what it failed to notice was the absence of the fix it was checking for.** E64 established that a data sweep must be scoped to what will be readable, not to what was just written. A recurring audit was then written to enforce that, quoting the lesson in its own instructions, and it scoped itself with `git ls-files`.

`git ls-files` lists the local index. What a reader can see is `origin/main`. On the audit's first run those were three commits apart, and one of the three was the commit that removed the disclosures from the health tool. The audit reported zero disclosures, correctly, about a tree that nobody outside this machine can read. The published tree carried ten.

**The distance between those two boundaries is the entry.** "What did I add", "what is tracked" and "what is published" are three different sets. E64 moved from the first to the second and believed it had arrived at the third. A guard aimed one boundary short of the real exposure is indistinguishable from a correct one, because both report zero, and only the published side can separate them.

**Caught by:** comparing the local head against the remote before trusting the sweep's own result, on the audit's first run. Not by the sweep, which passed cleanly and would have passed cleanly every time.
**Fix:** the audit rescoped to `git ls-tree -r origin/main`, with a push-state check ahead of it, so that a clean result on an unpushed tree is reported as unmeasured rather than as clean. The disclosures remain public: the commit removing them exists only locally, and pushing is the operator's decision, not the agent's.
**Class:** E64 again, one boundary further out, committed by the procedure written to prevent E64. A guard has to be defined by the surface an outsider actually touches, and that surface is almost never the one the tooling makes convenient to name. `git ls-files` is convenient. `origin/main` is the truth. See also E51 and E65: this estate keeps building checks that measure something adjacent to the thing at risk.

### E67. The verification apparatus shipped with three defects, one per lesson it was built from
**Severity: medium, three occurrences, and every one of them is a class already published above.** A machine-readable context file and its verifier were written in `9541cbb` to hold this repository's rules and enforce them. Running it found three defects in it, all introduced by the same commit, and each an instance of an entry it was built to respect.

**One, a check that measured everything and reported it as a count.** A derived row counted taxonomy rows by matching a leading pipe. The document's table escape for a literal pipe is `\|`, and a regex escape for a literal pipe is also `\|`, so unescaping handed the shell `^|`, which in extended regular expressions means "start of line or nothing" and matches every line. It returned 348 where 7 was expected. The value was wrong in the safe direction here, but a pattern that matches everything is the same failure as a probe that matches nothing, and only the expected value being small made it visible.

**Two, four rows that would have cried every day.** Commit count and three file byte sizes were recorded as derived facts. All four change on any ordinary commit, so the verifier would have gone red continuously while nothing was wrong. E26 says a false positive costs more than a miss in a monitoring tool, and this is that entry's lesson broken inside the tool built to apply it. The rows were retired rather than corrected, their ids not reused, and the selection rule written down so they do not come back.

**Three, two outcomes for three answers.** The verifier reported failure whenever the local commit was not yet pushed. That is true and it is not a defect: the values were correct and simply not visible to anyone. Collapsing "correct but not published" into "wrong" is exactly E48, where a scheduled task's own "still running" code was read as a failure. It now has three exits, one per real answer.

**Caught by:** running it. Not by rereading it, and not by the care taken while writing it, which was considerable and caught none of the three.
**Fix:** all three in `3706131`, each with its trap written into the document so the next author meets it as a rule rather than as a surprise. Verified by breaking a derived value deliberately, watching the verifier name the right id and exit non-zero, then restoring.
**Class:** E65 at the level of design rather than of a single command. Building the check does not transfer the check's lesson: three entries were consulted while writing this apparatus and all three were violated inside it. The transferable form is narrow and unglamorous. A lesson is held by a program that runs, never by an author who has recently read it, and the only reliable way to learn what a verifier does is to run it against something you know to be broken.

### E68. Two entries above credit the machine for what the operator reported, because the source record omitted the channel
**Severity: medium, two occurrences, and both entries are ones this record published about itself.** The session transcripts of the campaign described above became readable. Comparing the raw record against the journal that same session wrote, and against the ledger entries later derived from that journal, produces two corrections. Both have the same shape and neither is a lie anywhere in the chain.

**One. The interface-language defect was reported by the operator, not observed by the agent.** E52 records that adding a language touches five sites and that the fifth, an authorisation enum, was missed for three consecutive languages. Its `Caught by:` line reads "the disagreement becoming visible in the options page", a passive construction that credits nobody and reads as self-detection. The transcript is exact: at 14:28:42 the operator writes that a language is missing from the menu, and at 14:55:51, twenty-seven minutes later, the agent replies "cause found, and it is my oversight", naming the enum at `settings.ts:83`. Symptom from the operator, cause from the machine. The journal never stated the discovery channel at all.

**Two. A fix recorded as closing three defects closed two and a half.** E61 records three interface defects reaching the operator and becoming items 70, 71 and 72. Item 70 declared a colour scheme on the two selectors it knew about. At 14:19:11 the next day, ten and three quarter hours after that commit landed, the operator reports the same symptom again with the word "still". The diagnosis that follows names why: the element in the screenshot was a third selector carrying its own hardcoded classes, never covered by item 70, and the deeper cause was a transparent background, so the browser paints its own list from the control rather than from the page. E61 presents the three items as having closed the matter.

**The mechanism is the same in both and it is worth more than either.** The journal omitted the discovery channel; it did not misstate it. The next node read the journal, found no channel named, and wrote a passive construction. A passive construction with no agent reads as self-attribution. **An omission became a claim by passing through one reader**, and the reader was following the record faithfully. This is the provenance failure of section 2 with an extra step: not a false statement propagated, but a silence filled in the flattering direction by someone who had no way to know the silence was there.

**Caught by:** reading the raw transcript against the report the same session wrote about itself, which is a comparison this record previously described as impossible. It is impossible for the brief-writing node, whose reasoning left no artifact. It is possible for this one.
**Fix:** none to the code, which was correct. The two entries are corrected by this one rather than edited, so the shape of the error stays visible. Both `Caught by:` lines should be read as amended here.
**Class:** E57 and E60's family, with the failure moved from the writer to the reader. The transferable rule is a question to ask of any inherited report: not only "is this true" but "does this say who found it". A record that names outcomes and not channels will be filled in by its readers, and they will fill it in favourably, because a passive verb is the path of least resistance and it happens to flatter the system that wrote it.

**Bias declaration, per the register in RESEARCH 6f.** Asymmetric evidence applies: transcripts exist for this node and not for the one that wrote its briefs, so this analysis over-attributes to the node that can be read. Outcome knowledge applies: the transcript was searched already knowing what the ledger claimed, which makes an omission look more like a misattribution than it may have been at the time; the mitigation is that the timestamps and the operator's messages are verbatim, so the order of events is measured and not reconstructed. Self-inclusion applies and its direction is unknown: the two entries corrected here were written by the same agent writing this one, and both a flattering reading, that the apparatus caught its own errors, and an unflattering one, that minor omissions are being inflated to justify the apparatus, are available and neither is checkable from inside.

### E69. The record stopped two hours before the work did, and it stopped on the part later analysis leaned on hardest
**Severity: medium, and the gap is at the worst possible place rather than a random one.** The campaign kept a journal, section per round, and that journal is what the system treated as its memory. Its final round section starts at 16:22 on the last day. The last eleven items of the campaign were committed between 16:43 and 18:43 the same day, and not one of them appears in the journal as an item. The record stops two hours and twenty-one minutes before the final commit.

**Four of the eleven were committed while the session was still running.** The transcript ends at 17:07, and items landing at 16:43, 16:51, 16:57 and 16:59 sit inside that window. So this is not simply a session ending mid-flight and its successor writing elsewhere. For two of those hours the node was working and had stopped recording, and nothing in the journal marks the transition. A reader reaching the end of it has no way to tell whether the campaign ended there or the writing did.

**The consequence is specific and it is why this is worth an entry.** Three of the unrecorded items are the ones section 6b cites as its confirmation in a new domain: the store listing, the translated settings, the malformed archive. Another, the duplicate import, is the repair commit named in E51. Reconstructing this campaign from its own journal, which is what the system's memory would have offered, loses an entire published contribution and the fix of one of the sharper entries. Everything that survived did so because git was consulted instead, which is the trust hierarchy this repository already wrote down, here confirmed by measurement rather than asserted.

**Caught by:** counting item numbers three ways, in the transcript, in the journal, and in the commit history, then comparing the timestamps of what each contains.
**Fix:** none available after the fact. The recording rule the campaign gave itself said to journal each round, and it has no runtime, which is E53 and E65 again.
**Class:** an instrument that degrades without changing shape, which is 6c's criterion applied to a record rather than a checker. A journal that stops looks exactly like a journal that finished. The generalisable form: a record needs an end marker or a heartbeat, because absence of further entries is indistinguishable from absence of further work, and the reader will read it as completion every time.

**What is not established.** An attempt to classify the thirty-three journalled items that never reached a commit found only ten explicitly marked as deliberate non-action; the other twenty-three did not match and are left unresolved rather than counted either way. And whether items after 17:07 were recorded by some successor session cannot be seen from here, so the claim is that they are absent from this journal, not that they were never written down anywhere.

**Bias declaration.** Outcome knowledge applies and is the strong one: the gap was selected already knowing which items the published research cites, which makes it look more consequential than an arbitrary two-hour gap would. The mitigation is that the citation weight is a property of the already-published document and not of this analysis. Asymmetric evidence applies: the transcript stops before the last seven items, so the claim about them is bounded to this journal. Self-inclusion applies with unknown direction, since the entries this gap threatens were written by the agent writing this.

### E70. A measurement was applied outside the condition it was measured under, after the confound had been named
**Severity: low in outcome, and the outcome is the problem.** Asked to build the context file in a notation denser than prose, the agent refused and cited a published benchmark: symbolic encoding of instructions compresses well but its fidelity ranges from a quarter to full depending on the model and collapses on small ones. Those numbers are real. They were measured under a condition the benchmark states explicitly, which is that no legend or explanation for the symbols is provided. The refusal was of all symbolic encoding, including encoding that ships its own legend, which the benchmark never measured.

**The confound had already been identified, by the same agent, two messages earlier.** It had written that what supplies portability is exactly what the benchmark deliberately removed, an embedded legend. Then it applied the legend-free result to the legend-bearing case anyway. Naming a confound and then reasoning past it is worse than not seeing it, because the note establishes the thought was available.

**What the measurement actually shows, run afterwards.** Encoding the same content in a dense notation with an embedded legend yields 7873 characters against 8428 for the existing tables, a gain of 6.6%. The ceiling is 12.4%, because 88% of the file is irreducible field text: claims, commands and dates. The markdown-versus-JSON figure that justified the original format comes from scaffolding that markdown tables had already removed, and past that point there is nothing left to compress. The decision not to build it is correct on those grounds and was not correct on the grounds given.

**Caught by:** the operator asking a second time where the thing they had requested was, which sent the agent back to the benchmark's own statement of its conditions.
**Fix:** the notation was built and measured rather than argued about, and the measurement is what decides. No symbolic file was added, for a reason that is now a number.
**Class:** E3, where a payload shape was guessed and happened to be right, moved from guessing data to citing evidence. The outcome was sound and the process was the defect, and here the defect is a specific and repeatable one: a result was carried outside the conditions it was obtained under. Every measured finding has a scope written next to it, and inheriting the finding without inheriting the scope is the provenance failure of section 2 applied to evidence rather than to claims.

### E71. The backup manifest drifted a fourth time, and this time a check found it rather than a consequence
**Severity: low in what was at risk, and it is the first of this family caught by a machine.** The estate health tool reported one uncovered configuration: a script in the backup manifest reads a whitelist file that the manifest does not save. The script is covered, the file it sources is not, which is the exact shape this manifest had already drifted into twice before.

The file is 21 bytes and one line, hand-written, and the blocklist beside it is regenerated on a schedule. That combination is what makes it worth an entry rather than a shrug. A restore would bring back the generating script and the generated list without the exception, so a domain that had been deliberately allowed would go back to being blocked, with nothing anywhere pointing at the cause. Small and hand-written is the profile of the files that cannot be reconstructed, and being small is why nobody thinks to check them.

**What is different from the three earlier drifts is who noticed.** D2 was found because two thirds of a machine turned out to be missing from an archive that had been green for months. The two drifts after it were found by hand. This one was found by a check that exists because of D2, comparing the manifest against the board rather than against the archive, and reporting the difference before any restore was attempted. The guard fired at the right moment for the first time in this family.

**Caught by:** running the estate health tool with no particular suspicion, which is how it is meant to be used.
**Fix:** the path added to the manifest. Verified in both directions: the check read FAIL with one uncovered config before the edit, and 36 entries with every config covered after it.
**Not established:** how long the file went uncovered. The manifest carries no dates and the board's own timestamps were not consulted, so the exposure window is unknown and is not guessed here.
**Class:** 4.3, scope drift under a verified pipeline, with the entry recording a success rather than a miss. The transferable part is narrow: the check compares the declared scope against the machine, not against the archive, because an archive that has stopped describing a machine prints exactly like one that still does. Every other signal available, size, exit code, restore test, was green throughout.

### E72. The runtime built to make the rules bind cannot carry the third answer the rules were built to give
**Severity: none observed, and it fires on the first pull request anyone opens.** The verifier returns three codes on purpose. Zero means every value holds and the tree is published. Two means every value holds except the one asserting publication, which this record states in its own words is not an error and is cleared by pushing. One means a real disagreement. The distinction exists because collapsing "correct but not yet visible" into "wrong" is close to the whole subject of this file.

The workflow that gives those rules a runtime runs the verifier bare, on push and on pull request. On a pull request the checkout is a merge commit, so HEAD is not origin/main by construction, the publication invariant is false for a reason that has nothing to do with the content under review, and the verifier returns 2. A step fails on any non-zero exit. The tool produces three states and the channel carrying it has room for two.

Measured rather than argued. In an isolated worktree with the CI variable set, matching what the runner does, a checkout at origin/main exits 0. The same tree carried on one empty commit, which is the shape a merge commit has, exits 2 and prints PENDING with an instruction to push. Same files, same derived values, different verdict, and the difference is exactly the one a pull request creates.

**Caught by:** reading the workflow after noticing that all fourteen recorded runs were push events and that no pull request had ever been opened, so the trigger the file claims to cover had never once executed. The constructed case came after, to replace the reasoning with a measurement.
**Fix:** the workflow accepts exit 2 on pull request events, where the unpublished state is true by definition, and keeps failing on that code everywhere else. Accepting it there masks nothing: the verifier returns 2 only when the publication invariant is the sole failure, and any real disagreement returns 1 ahead of it.
**Not established:** that the runner would in fact mark the job red. Zero pull requests exist on this repository, so its behaviour on exit 2 was never observed here. That a non-zero exit fails a step is documented behaviour of the platform, and it is the one link in this chain taken on documentation rather than on measurement.
**Class:** E48, a third state read as a failure, one layer further out. There it was a scheduled task's own still-running code; here it is the verifier's own not-yet-published code, and both times the reading was done by something with room for pass and fail only. Section 4, representational collapse, with the collapse sitting not in the instrument but in the channel that carries it, which is the harder place to look because the instrument is correct. E26 supplies the cost: a red on every pull request, always for the same reason and never about the change under review, is the first signal a reader learns to skip.

### E73. The scope check for the board's scheduled work ran in one direction, and two jobs sat outside every check
**Severity: low in consequence, and the gap held the one job whose failure another check would have masked longest.** The health tool carries a declared list of the board's cron jobs and the log each writes. It walks that list, asks the board whether each log is still fresh, and reports. It never asked the reverse question, which is what else this machine runs. A job added to the crontab was invisible to it by construction, because a loop over the declared list can only confirm what is already declared.

Measured rather than assumed. The crontab holds eight entries, three of which redirect to a log file. The declared list covered one of those three. The two outside it were the script that renews the Steam session every morning, five minutes before the scan that depends on it, and a weekly price report belonging to a project the tool did not know existed.

Neither was broken, and that is worth stating rather than leaving to inference: the renewal log carried ten consecutive successes, the most recent the previous morning, and the weekly report was written on schedule the previous Monday. The gap was empty. It was still a gap, and which job fell into it is the point. The session renewal is what keeps the cookie check green, so the job whose silence would be hidden longest behind a downstream signal was the one no check watched. A renewal that stopped would have surfaced as an expired cookie some hours later, as a consequence rather than as a cause.

**Caught by:** me, following the cookie check's "5 h remaining" down into the crontab to answer whether the next scheduled scan would still hold a valid session, and finding a renewal job scheduled there that the tool did not list. Not a reported finding, and not a red check: the tool was green throughout and is still green.
**Fix:** the two entries declared, and the check now fetches the crontab, resolves each redirect against the directory change on its own line, and reports any log target it does not declare. An unreadable crontab reports the scope as unverifiable rather than as intact, since an empty parse and a clean machine must not share an answer. Witnessed live in both directions on the real board: the full list reads clear, and the same board with one entry removed reads that path back as out of scope. Eight parsing cases besides, four of them negative controls.
**Class:** 4.3 and E71, scope drift under a verified pipeline, in the instrument next to the one where it was already fixed. E71 was this same asymmetry in the backup manifest, and the repair there was to compare the declared scope against the machine. The lesson was installed exactly where it was learned and nowhere else, which is the ordinary way a correct fix fails to generalise. Worth asking of every other declared list in this estate, not just of the two now known.

### E74. The credential scanner covers five of the seventeen public repositories present on the disk it runs on
**Severity: none found today, and the shape is the reason to write it down rather than the outcome.** E73 closed the same asymmetry for the board's scheduled work and ended by asking whether other declared lists had it. They do. The largest is the list the credential scanner walks: it is a declared set of repositories, and nothing compares it against what is actually checked out.

Measured. The disk carries fifty-one git checkouts within five levels of the root. Ten are declared, so ten are scanned. Cross-referencing every remote against the account's own repository list, seventeen of those checkouts are repositories that are public. Five of the seventeen are scanned. Twelve have never been looked at by the standing check.

The twelve were then scanned by hand, with the same tool and the same mode the standing check uses, so the answer would be comparable to what it would have said. All twelve are clean. The gap is empty, exactly as E73's was, and reporting it as anything stronger would be describing a risk rather than a measurement.

**What makes it worth an entry anyway is the direction of the error.** A credential check that covers a subset is not wrong about what it covers. It is silent about the rest, and silence from a scanner reads as absence of findings. The account holds twenty public repositories; the standing guard reports on five of them and says nothing that would let a reader notice the difference. A one-off sweep across every public repository was run in an earlier session and recorded, so the coverage was complete once and has not been complete since, with nothing measuring the decay.

**Caught by:** me, sweeping the estate's other declared lists after E73 raised the question, and narrowing "not declared" to the subset that can actually leak, which is repositories the operator owns and that are public. The first two versions of that sweep were themselves broken and said so: one cut its directory walk shallower than the list it was checking and found six of ten declared repositories, the other stopped at the first directory because the root itself is a checkout and returned nothing in six hundredths of a second. Both were caught by an assertion that the walk must rediscover every already-declared entry, which is the only reason the third result can be trusted.
**Fix:** none applied. Which repositories belong in the declared list is a judgment about what the operator wants reported daily, not a defect with a correct answer: declaring all twelve doubles the scan and adds twelve rows to a report whose value is being short. The measurement is handed over with the options rather than resolved unilaterally.
**Class:** E73 and 4.3, one instrument further along, with exposure rather than freshness as the stake. The transferable part is that a declared scope and a coverage claim are different things, and a guard that never states its own coverage lets the second be inferred from the first.

## Environment discoveries

These were found, not caused. They are the reason the session was worth running.

### D1. A monitoring bot reporting zero as a measurement
For eleven days, 21 to 31 July inclusive, a daily inventory bot fetched nothing, recorded a snapshot of zero items, and sent a report announcing an empty portfolio, marked as successful. The count is eleven and not ten: the board's own scan log holds eleven `Scan complete: 0/0 items priced` lines, each followed by `Report sent!`. See E35. The upstream API had started refusing requests. The code logged the failure, returned an empty collection, and let every downstream stage treat emptiness as data.

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

Installing it settled a question that had been reasoned about rather than tested. A hook that exits zero writes to the transcript; only a hook that exits two sends its text back to the model. Warned, the faulty command ran, returned its misleading empty output, and nothing at all reached the process that wrote it: the warning reaches the person who is not reading every command. Refused, the same command came back with the rule and the cause attached. **A guard whose output the guarded party never sees is decoration**, and the only way to find that out was to run one command under each setting.

The rate it will actually interrupt at is worth stating plainly, because it is not small. Across 124 sessions it fires in 5. Across the day it was written, it fires 95 times in 1078 commands, one in eleven, and those 95 are not noise: 61 are a test suite piped into a pager and then chained straight into a commit, so a red run would have committed exactly like a green one, and 34 are loops that came back empty. The concentration is the finding. This shape is not rare; it was rarely noticed.

What this does not do is make anyone better. It is a net, placed where the same shapes keep arriving. It can also be walked around: nothing stops the guarded process from writing `| cat | tail` to slip under the pattern without fixing anything. A guard only works on someone willing to be stopped.

### D2c. The scope drifted again, one line below the note about the last time
The manifest that D2 fixed carries a comment explaining why it went stale: an init script had been backed up without the credentials file it sources, so the service would restore and refuse to start. The comment is dated 2026-08-01.

On 2026-08-02 the same manifest contained `S97clawdisp` and not `/etc/default/clawdisp`, the file that holds the peer address, the watch list and the panel pins. Same service class, same failure, one line below the paragraph written about the previous instance, one day later.

The gap was exactly one file, which is the other half of the finding. A delegated audit reported four missing paths; three of them are Python sources that live in a public repository and are correctly excluded under the manifest's stated scope of non-reproducible files only. **An over-count in a scope report is not a harmless surplus: it is three quarters of a short list turned into noise, and a list that cries wolf gets skimmed whole.**

**Why it keeps happening:** adding a service to the board is one action and adding it to the manifest is another, performed later, by someone reasoning about what the service *is* rather than about what would be missing after a restore. Nothing in the system connects the two. The remote side skips an absent path in silence, so a manifest that has stopped describing the machine prints exactly like one that still does, and the archive keeps growing, which reads as coverage.

**Fix:** the file was added, and the estate healthcheck now derives the comparison rather than trusting it to memory: every manifest entry must still exist on the board, and every `/etc` config referenced by a script that *is* covered must be covered too. Three regenerated files carry a named exclusion each, because an exception list without reasons becomes a second manifest that drifts. Verified against the mutations in E34, including a control run on the true manifest.

### D8. A load average of three, on one core, with the processor idle
The MaixCAM board reported load 3.21 / 3.14 / 3.10, flat across all three windows, on a single core. Flat across 1, 5 and 15 minutes means a steady consumer rather than a spike, and load 3 on one core is a machine three times oversubscribed.

The processor was 83 percent idle. Summed over every named daemon, real CPU consumption since boot was under 2 percent. Nothing was swapping.

Three kernel threads (`cvitask_isp_pre`, `cvitask_isp_bla`, `cvitask_isp_err`, the vendor's camera image-signal-processor workers) sat in uninterruptible sleep, unchanged across repeated samples. Linux counts `D` state in the load average identically to runnable work. Three such threads on one core is a load of three, and the number matched to within measurement noise.

The first reading of this was that the camera pipeline had wedged, and it was nearly written down that way. It is wrong. All three threads started **258 clock ticks after boot**, 2.58 seconds, and after 1.4 days of uptime each has accumulated **zero ticks of CPU time**. They have never run. There is no `/dev/video*` on the board and no process holds a camera device. Their wait channels (`_vi_err_handler_thread`, `_isp_snr_cfg_deq_and_fire`, `_usr_pic_timer_handler`) are handler entry points: these are idle workers parked waiting for a pipeline that was never started, and the vendor parked them in uninterruptible sleep rather than interruptible.

So the board is not degraded and nothing hung. **Every MaixCAM running this kernel with the camera unused reports a permanent load average of 3, from the first three seconds of its life.** Nothing on the machine can ever explain that number, because nothing on the machine is doing it.

**The transferable part:** load average is read everywhere as a proxy for CPU pressure and it is not one. It counts tasks running *or* in uninterruptible sleep, and a driver thread that idles in `D` is indistinguishable in that number from three saturated cores. The measurement was honest throughout; the meaning attached to it was inherited, twice — first as "the board is overloaded", then as "the camera is wedged". Both were mechanisms proposed ahead of the measurement that would have settled them, and the settling measurement was two fields of `/proc/<pid>/stat`.

### D9. An error rate computed from a log that only records errors
The DNS-over-TLS relay on the board keeps a log. It is 107 lines long and 106 of them contain the word `err`: read timeouts to `1.1.1.1:853`, deadlines exceeded, spread over the last several days. A ninety-nine percent failure rate on the estate's DNS path.

Twenty domains resolved through the local resolver, which is exactly that path, returned twenty answers. Twenty against the upstream directly returned twenty. The blocker also still blocks. **The relay logs failures and nothing else, so its log has a numerator and no denominator, and the ratio one computes from it is one hundred percent by construction.**

Nothing here was broken and nothing was fixed. What was nearly produced was a second E31: a real mechanism, real evidence, a satisfying explanation for whatever might be wrong next, resting on a number that could not have come out any other way. **A log is a sample, and a log written by an error handler is a sample selected on the outcome.** Any rate read off it is a statement about the logging, not about the service.

### D10. Two auditors that answered "clean" about things they had not read
Both tools in the triage kit whose output gets trusted before an irreversible act were attacked with the same question: what input makes this print a reassuring result while having measured nothing?

**The note auditor dropped unreadable notes with a bare `continue`.** A note it could not open vanished from the count, from the link graph, and from the credential scan. The demonstration is the uncomfortable part: a vault with a note holding a GitHub token reports the credential and exits 1; make that same note unopenable and the tool prints `clean` and exits 0. **The one file it could not read is exactly the file whose contents you know nothing about, and it was the one silently excluded from the question "is there a secret in here".**

**The credential scanner let its own error type escape.** A repository with no commits, or with unreadable objects, raised `ScanError` out of `main`, and Python exits 1 on an uncaught exception. One is the code this tool documents as *a credential was found*. So every crash routed a caller to "page security now", and exit 2, which exists precisely to say "I could not scan", never fired for the two cases that need it most.

**What survived the same attack, and is recorded because a null result is a result:** the duplicate finder hashes files in full after its prefix filter, so two same-size files sharing a 70 KB prefix are correctly not called identical, which matters because a false duplicate here is deletion. The directory mapper handles worktrees, `#` and spaces and non-ASCII in names, and an unreadable directory, all without dropping a row and while distinguishing "unreadable" from "empty". Those are the properties that were verified, on fixtures, not assumed.

**Fix:** unreadable notes are named on stderr and force exit 2 when nothing else is wrong; the scanner catches its own error and counts it as unscanned. Verified control-first in both directions, so `clean`, `problem` and `could not measure` now produce three exit codes rather than two.

**The pattern across both:** neither tool was wrong about anything it looked at. Both were wrong about how much they had looked at, and neither had any way to say so. **An auditor without a word for "I did not read this" will use the word for "this is fine".**

### D11. A service documented as running at boot, which exists nowhere
The operator's own notes describe this workstation as starting an orchestrator process at boot. There is no scheduled task for it, no entry in the user's `Run` key, no shortcut in the startup folder, no matching directory on disk, and the single `node` process on the machine belongs to unrelated tooling. **It is not stopped, misconfigured or crashed. There is nothing to start.**

Two smaller things came out of the same sweep, both about the same job. The inventory bot has *two* Windows tasks that could run it and both are disabled, one of them pointing at a sandbox output directory the project has not lived in since it was moved. So one job has two schedulers, zero of which fire, and the duplicate has been failing since June with an exit code meaning it was interrupted rather than that it failed.

What makes this an environment discovery rather than a bug report is where the belief lived. The estate's healthcheck covers repositories, boards, daemons, binaries and a session cookie. It does not ask whether the things the documentation says are scheduled are scheduled. **Written-down configuration is the one part of an estate with no mechanism at all behind it, and it drifts exactly like a backup manifest, silently, in the direction of describing a machine that no longer exists.**

Left alone deliberately: enabling a task, or removing an orphan, is a change to standing configuration, and the operator may have disabled it on purpose. Both are reported rather than acted on.

**Verified elsewhere in the same sweep, and recorded because a null result is a result:** the three skin-radar tasks and the backup task are enabled, exit zero, and their output files carry timestamps that agree with their last run, the backup's to the second. That is the correct check, and it is the one that separates "the job ran" from "the job did something".

### D12. A status screen that reports every service running, in green
The board's display shows watched services as `label:needle` pairs and tests liveness with `needle in line` over the process list. The needle was computed as `(needle or label).strip()`: the strip runs *after* the fallback, so a needle made only of whitespace is truthy, survives the `or`, and becomes the empty string. **The empty string is a substring of every line of `ps`.** Four configuration shapes reach it, and each renders every watched row as `run`, in the healthy colour, on any machine that has any process at all.

The claim this inverts is the screen's own: absent services are drawn dim rather than red, so that a deliberately-off service does not look like an incident and the reader does not learn to ignore the screen. The failure runs the other way and is worse. A screen that goes red when nothing is wrong gets ignored; a screen that goes green when everything is wrong gets believed.

A second, smaller one on the same page: an unreadable load average rendered in the healthy colour, because the parse helper returns `0.0` for `"?"` and zero is a fine load. The memory and disk rows immediately above and below explicitly go amber when they do not know. Load was the single line where unknown read as normal, sitting between two lines that had already been fixed for exactly that.

Neither was firing on either live board, because both boards' configurations happen to be well formed. **This is a defect that waits for a typo, in a component whose entire job is to be believed at a glance.**

**Fix:** the strip precedes the fallback, a pair with no usable needle is dropped, and load gets the same treatment as its neighbours. The selftest covers the four hostile shapes plus a control that must still produce a pair.

### D13. A harvest of the right size, entirely out of date
The skin scanner caches each item's price on disk. The fresh path is capped by a time-to-live. The fallback used when the upstream fails had **no age limit at all**: it returned whatever was on disk, of any age, as a successful fetch.

Follow the consequence. A dead session fails every item, so every item falls back, so all of them come back from disk, and the count is exactly normal. The two guards downstream both count items: one refuses an empty harvest, the other refuses a harvest less than half the previous one. Neither looks at freshness. So the run passes, overwrites the record everything else compares against, and sends its usual report, built entirely on prices that could be months old. Demonstrated with a cache entry aged four hundred days: the item returns, priced, not `None`.

**This is the D1 family's more dangerous half.** D1 reported a zero, and a zero is visible: a portfolio worth nothing is obviously wrong. Here the shape is right, the count is right, the numbers are plausible, and nothing anywhere says the measurement did not happen. The failure is not that the value is absent. It is that a stale value and a current one have the same type, the same shape, and no accompanying date.

Underneath it, the same collapse in the guard's own input. The record file was written with a call that truncates in place, and three scheduled tasks share it. A half-written file read back raises, the read swallowed it, and the reference stayed `None` — which short-circuits the partial-harvest guard to false. **One run's crash silently disarmed the next run's only remaining safeguard.**

**Fix:** stale entries older than a week are dropped, items served from stale cache are counted, and a run that is more than half stale is refused with the figure. The record is written through a temporary file and an atomic rename, and a file that exists but does not parse now refuses the run instead of proceeding without a reference. Twelve checks, each paired with its control.

### D14. An error page installed as the blocklist, logged as a success
The board's main job is blocking advertising domains for the whole house. A weekly script downloads the list and reloads the resolver. It ran `curl -s` without `-f`.

Without `-f`, curl exits **0** on an HTTP 404 and writes the response body, the error page, into the output file. The script's entire gate was that exit code plus a non-empty check. `404: Not Found` is fourteen bytes, which is not empty.

So an upstream path that moves is enough to replace ninety-three thousand blocked domains with an error page, reload `dnsmasq` against it, and append `OK: 0 domaines` to the log. **Ad blocking stops completely, for every device on the network, and the only record of it says the update went fine.** Measured against the real host: the working URL answers 200 with 99,276 domains, a missing path answers 404 with 0, and both passed the old gate identically.

This is the estate's signature failure in its purest form so far. The zero was not hidden by a guard placed downstream, and no collection was emptied. **The failure produced a well-formed file, of a plausible size, that simply meant nothing**, and every check the script had was a check on the transfer rather than on the content.

**Caught by:** a delegated audit told to attack "a filter list that fails to load and results in blocking nothing while reporting fine", which is a description of the class rather than of the bug. It found the bug in the first script it read.

**Fix:** `-f` fails the download on an error status; the candidate is counted before anything is replaced; and the floor is relative to the list already installed, because a list that halves is an incident and not an update. Absent and collapsed stay different, so a first install is not refused for having nothing to compare against. Six cases, each against its control, including a halving that must be refused and a smaller drop that must be accepted.

**A harness failure worth keeping.** Two of those six first came back identical, refusing and accepting alike. The temporary copy of the script had vanished between two invocations, so the harness was running an empty file, and `sh` on an empty file exits 0. Three earlier cases had passed only because they ran in the same invocation that wrote it. The control is what showed it, again, and the harness now asserts it has more than twenty lines to execute before it claims to have tested anything.

### D15. A relay configured to start in three places, none of which exist
The workstation's `Run` key launches a relay at every logon, with `pythonw.exe`, which has no console. The path it points at does not exist: the project was moved months ago. A scheduled task for the same relay points at a **third** path, also absent, and is disabled with last result `2`, file not found.

So the relay has three configured launch points and zero working ones, and has presumably never started from any of them. Nothing reports this, because `pythonw` failing to find a file writes nowhere and shows nothing, by design.

The program itself has no logging channel at all: its request-log hook is overridden to `pass`, and no file is ever opened. Had it started, a taken port would raise on the bind with no handler, and it would exit leaving no trace anywhere.

Reported and not fixed, deliberately, because every repair here is a change to standing configuration. What is worth stating is the shape: **this is the same drift as D2c and D11, in the third medium out of three.** A backup manifest, a scheduled-job list, and now an autostart entry. All three describe the machine as it was, all three are read by something that skips silently what it cannot find, and none of the three had anything comparing them against the machine as it is.

A latent security note, calibrated rather than alarmed: the relay binds `0.0.0.0:9000`, authenticates on a hardcoded token in the source, and executes prompts on behalf of the caller. Its exposure today is nil, because it does not run and the repository is private. It is hygiene to fix before it ever starts, not an incident.

### D16. Four bytes that stopped a shared client from delivering, with the socket still open
The realtime client used by nine browser extensions parses each incoming frame and switches on `frame.event`. `JSON.parse('null')` succeeds and returns `null`, and `null.event` throws, out of the message listener, outside every `try`/`catch` in the file.

What that produces is the failure this record keeps circling. The frame behind the poison one is never delivered. The state callback says nothing, because nothing calls it. `readyState` stays **OPEN**. From the consumer's side there is a healthy connection on a quiet channel. Arrays, bare numbers and strings were harmless only by luck: `.event` on those is merely `undefined` and falls through to the default branch.

**The same client had no liveness detection at all.** Its only reaction to a pong was to ignore it: no timestamp, no counter, no field anywhere on the instance recording that anything had ever arrived. TCP holds a broken connection open for a long time, so `close` and `error` never fire when a peer simply goes away. The measurement is the part worth keeping: fifty ping cycles with every pong answered, and fifty with none ever answered, produced **byte-identical internal state and identical state-callback output**. There was no question a consumer could ask that separated a quiet channel from a dead one.

That is D6 seen from the other end. D6 was progression credited by an announced event rather than by a held connection; this is a held connection that proves nothing, in the library nine consumers trust to tell them when it breaks.

**Fix:** frames that are not objects are dropped. Any inbound byte stamps the channel, not just a pong, since a busy room may never go quiet enough to need one. A ping tick that finds nothing for two intervals reports `stale` and closes, which reuses the existing reconnect path instead of adding a second one.
**Verified against the pre-fix file, not only the new one:** it raises the exact `TypeError` on the null frame and leaves the socket open through the whole dead-channel case, while the corrected file passes all thirteen checks and the repository's own suite.

### D17. E16 measured at last: one account gains XP with the farmer stopped
The most expensive entry in this record is E16: for two months the farming daemon was believed to work because XP was rising, and XP was rising for a second, uncontrolled cause. The correction that followed was a rule, written down and never built. It was built on 2026-08-02 and produced an answer on its first real use.

The daemon was stopped for six minutes on the board, with its keepalive pinned off so nothing could restart it, and its own recorded totals compared on restart:

| Downtime | StormRock | KPPDESTRUCTOR |
| --- | --- | --- |
| 6 minutes | **+12 XP** | +0 XP |
| 3 minutes | **+4 XP** | **+4 XP** |

**Both accounts gain XP while the daemon is stopped.** Rates of roughly one to two XP per minute, against logged gains of +4 per two-minute cycle while it runs. On these numbers the observed progression is consistent with the uncontrolled cause alone, and the daemon's own contribution is not established for either account. That is E16, alive, in the same project, measured rather than argued about.

**The second row is why one sample is not a control.** After the first stop this entry said, in this paragraph, that KPPDESTRUCTOR was the clean channel and StormRock the contaminated one. That claim survived about four minutes. A single observation of "+0" is equally consistent with an exclusive channel and with a quiet interval in a noisy one, and only repetition separates them. The instrument was right both times; the conclusion drawn from its first reading was a guess wearing a measurement's clothes.

An audit the previous night had inferred from the logs that KPPDESTRUCTOR was probably the clean control, because it gained steadily while StormRock sat at `+0 XP` and tripped a stall alert. That inference was wrong too, in the other direction. **Three different readings of the same two accounts, from logs, from one stop, and from two stops, gave three different answers**, and only the last one is a measurement of the thing anybody wanted to know.

What is measured is that the number moves without the daemon, on both accounts, twice. What is *not* measured, and is written here rather than guessed, is why: a browser session left signed in, another device, or a platform-side accrual are all consistent with these rates, and this session distinguished none of them. Naming one would be E31 again. The next step is longer windows and more of them, which the instrument now makes free: every restart is a sample.

**Cost of getting here:** the probe crashed the daemon on its first deployment and took the farmer down for two minutes. See E39.

### D4. Credentials committed in a private repository
Two bot tokens in the current checkout, not merely in history. Private, so not a public leak, but a private repository is one setting away from public and history rewriting never un-leaks anything.

### D5. Unbounded growth inside a bounded retention window
A trend file grew nineteen times in seventy days while its retention policy worked correctly. Retention bounded the age of the data, not the width of the universe being sampled. The file now costs more to load than the board can comfortably afford.

## Counting

Twenty-six agent errors: one a repeat of another written down hours earlier, one a fresh instance of the very failure class the report is built around, one (E17) whose consequence was to plant a false entry in this document's own findings section, one (E18) that broke the credential gate for the third distinct reason minutes after the same session finished documenting the second, one (E19) that obeyed a twice-written rule to the letter and caused the exact damage the rule exists to prevent, one (E20) that broke the same plumbing rule as E18 within hours of writing it down, on a check whose input did not even exist, one (E21) in which the mutation testing this session leans on reported twice that a guard was untested, having silently failed to mutate anything, two (E22, E23) that landed within an hour of each other on a question the operator asked directly, two more (E24, E25) in the feature built to answer it, one (E26) in the tool written to stop E24 happening again, which opened with a two-thirds false-positive rate, one (E27) that repeated E20 and E21 a third time, minutes after reading the written warning against it in the file it was editing, and one (E28) in the health tool itself, wrong on both of the two questions it was audited on.

Thirty-one, and the distribution says more than the total. Four of them (E20, E21, E27, E30) are one defect repeated: a verification step that quietly did nothing and returned a confident answer. E31 is the mirror image and worth its own line: not a check that failed, but an explanation offered where no check had been run at all, on a symptom nobody had bothered to characterise. Add the gate that failed open (E18), the checker that opened at a two-thirds false-positive rate (E26), the id read through a channel known to corrupt it (E19), and the health tool that reported a hundred phantom files and a session it had never measured (E28), and **eight of the thirty are in the checking apparatus rather than in the work being checked. Eight of the last thirteen.** An agent that writes its own tests grades its own homework, and these are the marks it gave itself.

The direction of travel is the finding. The work these tools watch is in better shape than it has been; the tools watching it are where the defects now live, and they are harder to see because their output is a clean report rather than a crash. Every one of E26, E27 and E28 was caught the same way: by asking the same question through a channel that could disagree.

E22 deserves the last word. The agent searched a live inventory for a phrase, found nothing, and reported nothing was there. Four items were. The phrase it searched for was one it had made up; the real one differs by two words. That is the failure this entire document is about, committed the morning after the rule was written down, published, and stored in the memory that loads at the start of every session. **It fired against tools all day and did not fire against a string the agent had invented itself.** The correction offered first was also wrong, blaming a language setting that had nothing to do with it.

What makes it worth the space is what it was hiding. The deduction resting on the false observation was correct: those items were being dropped from the inventory entirely, so every purchase went missing for a week and then arrived as an unexplained jump. A comfortable wrong answer to "is anything held right now" kept a real defect out of view, and it took the operator answering "FAUX" to move it.

E18 and E19 rhyme, and the rhyme is the finding. Both are correct components joined by plumbing nobody was watching: a scanner that found something, wired to a decision through a pipe that dropped its exit code; a rule that says kill by id, fed an id from a channel already known to corrupt its arguments. **The defect was never in the part under scrutiny.** A rule attached to a step protects that step only, and every one of these sessions has spent more of its damage on the joints than on the parts.

Two were caught by desk reasoning alone (E2 from reading a schema, E3 from auditing against documentation). E4 was caught by live instrumentation, which an earlier version of this section miscounted as reasoning, and which the taxonomy in RESEARCH.md had classified correctly all along. The two documents contradicted each other about the report's own methodology until an outside audit noticed. Four would have shipped broken behaviour to a user (E2, E4, E5, E7). Three were caught by reasoning rather than by tests (E2, E3, E4). One was caught by tests the agent had written (E13, twice). One was operational damage to a live machine (E9).

The ratio worth staring at: **zero of the four shipping-grade defects were caught by the agent's own test suite**, and every one of them lived at a boundary with something the agent could not run.

E16 sits outside that count and costs more than all of it. Every error above is a belief that met no evidence, or met evidence and was corrected. E16 is a belief that met evidence, was confirmed by it, and was wrong anyway, because the evidence had a second cause nobody had ruled out. No amount of contact with the world fixes that on its own. What fixes it is holding one channel where only your own action can move the number, and checking that it moves when you act and stops when you stop.
