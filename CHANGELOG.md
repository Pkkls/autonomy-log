# Changelog

Everything produced or changed during the session documented in this repository, in the order it happened. Dates are the session date, 2026-07-30.

Format follows [Keep a Changelog](https://keepachangelog.com). Entries link to the artifact so each claim can be checked rather than believed.

---

## Repositories created

### [disk-triage](https://github.com/Pkkls/disk-triage) — public, MIT
Read-only tools for a directory tree that got out of hand. Standard library only, nothing is ever deleted.

- **`dirmap.py`** — sortable HTML map of every directory: size, file count, last write, project type, git branch, uncommitted count, and the first README line so a forgotten project is recognisable.
  - Worktrees and submodules now count as repositories. `.git` is a file there, and testing for a directory silently skipped the checkouts most likely to hold forgotten work.
  - Reports commits that exist nowhere else, distinguishing a repository with no remote at all from a branch merely untracked. The first version conflated the two and produced a false alarm on a repository that was in fact behind its remote.
  - Survives unreadable directories instead of aborting the whole report.
- **`dupescan.py`** — byte-identical files ranked by reclaimable space, grouped by size then partial hash before hashing in full.
- **`notecheck.py`** — auditor for a directory of markdown notes: dead wiki links, a `name:` that drifted from its filename, paths to things that moved, credentials pasted into a note. Run against a real vault it found 28 dead links out of 39, caused by three naming conventions coexisting. Its own path detection needed two fixes, both the same class of bug it exists to find: stopping a match at the first space broke every directory named like `02 - Projects`, and prose mentioning a path shape was read as a path.
- **`secretscan.py`** — credential scanner over full git history, not just the checkout. Masks matches, counts placeholders instead of reporting them, anchors patterns so they cannot match inside a base64 blob. Exit 1 on a finding, 2 on an unreadable path.
- CI on six combinations: Linux, Windows, macOS crossed with Python 3.9 and 3.13. The scanner runs against its own repository on every push.

### [kickbus](https://github.com/Pkkls/kickbus) — public, MIT
Receives official platform webhooks, verifies their RSA signature, deduplicates, and fans events out over SSE with filtering by type and channel. Standard library only, sized for a 128 MB single-board computer.

### [kick-core](https://github.com/Pkkls/kick-core) — public, MIT
Dependency-free client for a streaming platform's current realtime gateway, for use in browser extensions. Handles token fetch, subscription, ping, and reconnection with a fresh token.

### [claw-display](https://github.com/Pkkls/claw-display) — public, MIT
Turns a 240x240 SPI panel on a RISC-V board into an always-on status screen. The board has no framebuffer and no DRM, so the display is driven entirely from userspace over spidev with three GPIO lines.

- **`clawdisp.py`** — daemon rotating three pages (system, network, services), with thresholds that turn amber then red so an abnormal screen is recognisable without reading it. Anything written to a message file takes the screen for five minutes, then rotation resumes. That file is the interface: whoever holds SSH holds the display.
- **`show.py`** — one-shot rendering: text with a title bar, an image, colour bars to prove the SPI link, backlight off.
- **`say.sh`** — pushes text from another machine in one command, base64-encoded because quotes and accents do not survive four nested shells.
- **`S97clawdisp`** — init script that refuses to start when another process owns the panel, rather than producing `get gpio line failed` with no explanation.
- The driver and pin map are read from the vendor app already on the board rather than reimplemented, so a pin change stays in one place. A second backend drives the panel with nothing but `spidev` and the legacy GPIO sysfs, for a board with no vendor libraries at all.
- Rendering is testable off-device, which matters because on the board the daemon owns the panel and nothing else can draw.
- **Heartbeat.** A running process is not a working one. This display exists to reveal that kind of silence elsewhere, so it must not hide its own: after every successful frame it writes the time, the page and the outcome to a state file. Two readings apart tell a live screen from a process that is merely alive. Verified on the board, the timestamp advanced 21s across a 20s window. An unwritable state path is swallowed, because observability that can take down what it observes is worse than none.
- **Watched processes are configurable.** The services page hardcoded two names from one particular board; it now reads `label:needle` pairs from the environment. Absent services stay dim rather than red, since a service that is off on purpose must not look like an incident, or the screen teaches you to ignore it.
- **Installable on a board with no panel.** With the enable flag off, the service starts, says why it is not running, and exits: nothing runs, nothing is consumed, and the selftest still passes on the board itself, so the stack is proven ready rather than assumed ready.

### [autonomy-log](https://github.com/Pkkls/autonomy-log) — public, MIT
This repository. Ledger of errors, engineering write-up, denser analysis, and the record of what changed in the agent afterwards.

---

## Releases

### kickbus v0.1.2
- **Fixed:** `broadcaster_user_id` was sent as a string where the API types it as an integer. Every subscription attempt would have been rejected. The test double accepted anything, which is what hid it; tests now assert the JSON wire type rather than the decoded value.
- **Added:** self-repairing subscriptions. Given credentials, the daemon lists its subscriptions every thirty minutes and recreates only what is missing. The platform drops an app's subscriptions after a day of failed deliveries, and reporting that outage does not fix it.
- **Added:** `subscriptions`, `subscriptions_checked_at`, `subscriptions_error` in `/health`.
- Non-numeric broadcasters and empty event lists are refused before a request leaves the process.

### kickbus v0.1.1
- **Changed:** the signing key is no longer pinned. The embedded copy is now only an offline fallback; the published key is fetched at startup and every six hours. Pinning turned a key rotation into a silent outage where every webhook fails verification.
- **Added:** `key_source` in `/health`, reporting `published` or `embedded`. First thing to check when signatures start failing on a remote box.
- **Added:** `-offline` to skip the fetch entirely.

### kickbus v0.1.0
- First release. Six static binaries (riscv64, amd64, arm64, arm, windows, darwin), `SHA256SUMS.txt`, built with `-trimpath` and CGO disabled.

---

## Unreleased changes to kickbus after v0.1.2

- **Added:** `last_event_at` and `seconds_since_last_event` in `/health`, null until the first event ever arrives. A bus nobody feeds looks exactly like a healthy idle one.
- **Added:** `examples/consumer.py`, a working SSE consumer in standard library Python with reconnection and backoff. Verified end to end against a running daemon: a signed webhook reaches the consumer, a replayed message id answers 200 without being delivered twice, and the filters hold.
- **Added:** parsing tests backed by six documented event payloads, plus cases proving an absent broadcaster yields no match rather than a wildcard, and that a channel-filtered subscriber never receives another channel's events. This is the E3 near-miss being closed: the payload shape had been inferred and never checked, and it was correct by luck. The fix was in the git history but missing from this changelog until an audit noticed.
- **Fixed:** concurrent connections are now bounded, not just CPU. See the audit section below.

---

## kick-core

- **Fixed:** the token request sent only `Accept`. The real client sends session cookies plus three headers, one of which is a public client constant. The request shape had been assumed, never observed, because the endpoint is blocked outside a browser and blocked by CORS from a page. Captured by hooking `fetch` on a live session and forcing a reconnect.
- **Added:** selftest coverage of the request shape: method, credentials, every header, request id variation, and the two failures that matter (a rejected request must surface, a 200 with an unexpected body must not yield a bogus token).
- CI on Node 20 and 22, including a manifest validation that catches the three mistakes which make an extension silently inert.

---

## Fixes delivered to the operator, not deployed

These touch production hardware and were left for the operator to apply.

### Inventory monitoring daemon
- **Fixed:** a total failure to read inventories was indistinguishable from an empty account. The fetch logged its failure, returned an empty collection, and every downstream stage treated emptiness as data. Eleven days of daily reports announced an empty portfolio, marked successful.
- **Fixed:** the existing abort flag was only ever set inside the pricing loop, which is never entered when the item list is empty. The safeguard sat downstream of the failure it was meant to catch.
- **Changed:** the daily message distinguishes "inventory could not be read" from "scan aborted early", since the second implies a partial result that does not exist.
- **Added:** the project's first tests. Three cases covering unreadable versus genuinely empty versus one game failing, through a stubbed transport, no network. `InventoryDelay` became a variable so tests can set it to zero; it must never be lowered in production.

### Encrypted backup of the single-board computer
- **Fixed:** the manifest described the machine as it had been months earlier. A non-reproducible price history, a live session file, credentials, the DNS configuration and all six maintenance scripts were absent from every archive. Daily, encrypted, pushed, size stable for seventeen days, restore check green, and covering a third of the machine.
- Archive goes from 15 to 23 entries, 13 KB to 68 KB. Verified restorable before the change was committed.

---

## Data preserved

- Two copies of a project with no remote at all, holding its entire history on one disk, pushed to dedicated branches rather than over an existing default branch whose history was unrelated.
- Scanned for credentials before pushing. One copy contained a bot token in its configuration, which is why it went to a private repository and not a public one.
- Result: **0 of 33 local repositories** hold commits that exist nowhere else, down from 2.

---

## Findings reported, no action taken by the agent

- Two bot tokens committed in the current checkout of a private repository. Private is not public, but a private repository is one setting away, and history rewriting never un-leaks anything.
- A trend file grew nineteen times in seventy days while its retention policy worked correctly: retention bounded the age of the data, not the width of the sampled universe. It now costs more to load than the board can comfortably afford.
- A bot with an init script disabled at boot, occupying 224 MB while not running.

---

## Independent audit

Four agents that had written none of this code were asked to find real defects in it, each with a different remit, and told to prove anything they reported. This is the one mechanism the analysis in this repository argues actually works: a judge that does not share the author's beliefs. It found four things in an hour that months of self-authored tests would not have.

- **kickbus, denial of service.** The RSA semaphore bounded CPU, not connections. The request body is read before a verification slot is requested, and the server set only `ReadHeaderTimeout`, so trickled bodies could hold unlimited goroutines and buffers without ever reaching the cap. Fixed with `ReadTimeout`, `IdleTimeout`, and a limiting listener that sheds excess connections; the slot is freed exactly once even on a double close, which is tested because otherwise the limit erodes silently.
- **secretscan, silently blind.** See E14. The tool that gated every publication here was skipping a whole credential class and reporting clean. Fixed, and every published repository rescanned.
- **kick-core, two proven defects.** Two subscriptions in the same tick opened two sockets, because the re-entrancy guard inspected a field assigned only after an await; the orphan kept delivering messages and `stop()` could never close it. Separately, a `null` inside a badge array threw out of the parser, through the frame handler, into the socket listener. Both regressions were confirmed to fail against the previous code before the fixes were kept.
- **A false claim in a README.** kick-core stated a service worker was the one place it could run, while relying on timers that do not survive a worker being torn down. The limitation is now documented rather than implied away.

One of the four findings was itself wrong, and checking it mattered: see E15.

## Agent memory

- Two behavioural rules added: verification discipline, and operational care on constrained hardware. Both carry the incident that produced them.
- Naming normalised across 29 memory files. Internal links went from **11 alive out of 39** to **39 out of 39**.
- A bot token and an API key removed from memory files. Zero credentials remain.
- Dead filesystem paths went from nine to two, and the two remaining sit in sections explicitly marked historical. One path flagged as dead was a false positive from the audit's own regex, which cut on a hyphen.

---

## Session 2, 2026-07-31

A follow-up session on one project, added here because it invalidated a claim this repository had published.

### Retracted

- **D3 was false.** This log reported that a streaming platform had migrated off its hosted message bus. It had rotated a key. The entry is retracted in place rather than deleted, with the reasoning error recorded as E17.

### Added

- **E16, the most expensive error in the record.** A daemon reported as working for two months, confirmed continuously by a real external signal, which a second uncontrolled cause was producing. Full account in [LEDGER.md](LEDGER.md), and the loop it exposes in [RESEARCH.md](RESEARCH.md) section 3.1.
- **A new taxonomy layer, L5 attribution**, and a third feedback loop alongside the open and closed ones: externally confirmed, by something that is not you.
- **D6**, the mechanism that had been missed: progression credited by an announced event rather than a held connection, found by reading the client's own bundle and by treating a validator's rejections as its specification.
- **A third persistent rule, attribution**, filed separately from verification discipline on purpose. See [WHAT-CHANGED.md](WHAT-CHANGED.md).

### Corrected

- The one-line summary in the README. "Contact with the world catches it" was the lesson of session 1 and is not sufficient.

### Session 2, later the same day

A sweep across the rest of the machine, applying the attribution rule to work that had been reported as fine.

- **D1b: the flagship finding's fix was half a fix.** The inventory bot's guard protected the database and not the report. Two Telegram messages went out announcing a portfolio worth nothing, the day the log was published.
- **A latent copy of the same defect** in the sibling bot, which additionally overwrote its analysis file and swallowed its own exit code. Both fixed, both with a test confirmed to fail against the previous behaviour.
- **E18: the credential gate failed open a third time**, piped through `tail` inside a chain that ignored its exit code. It printed a real finding and was not read.
- **Verified rather than assumed:** the board display is drawing (heartbeat three seconds old), the weekly backup produced 581 real records, the second board's display is disabled by design and not by accident. One suspected defect turned out to be correct behaviour, which is the point of checking before acting.

### Credential sweep, all public repositories

The E14 aftermath note said the published repositories had been rescanned. That covered the five published in that session; the account has fifteen public ones. All fifteen were scanned across full history, since on a public repository the history is the exposure.

- **Fifteen clean.** Two matches, both benign on inspection: the scanner matching its own pattern table, and a unit test whose subject is redacting PEM blocks.
- **A production bot token was found in the checkout of two private repositories**, one of them the token used by the monitoring that runs on both boards. Removed from both working trees; rotation is the operator's, and removal does not revoke.
- **The scanner's sensitivity was left alone.** Two explainable matches out of fifteen cost seconds to read. Trading sensitivity away in a tool that has already failed open three times is the wrong side of that trade.

### Following the pattern instead of the incident

The morning's guard was placed on the two report formatters, so it protected the two reports that use them. Three more paths in the same program did not.

- **The monthly report** builds its message inline and never touches a formatter.
- **The inventory watcher** compares item counts, so a refused fetch read as "-369 item(s) (369 → 0)": a theft alert for a read failure, printed directly above the honest message saying nothing could be read.
- **The scheduled CI job** has been cancelled every day at its timeout, because the retry backoff is longer than the job is allowed to live. It sent nothing and left no readable trace, which ranks below sending something false.

All three fixed, each with a test confirmed to fail against the previous behaviour, and both Python repositories now run those tests on every push instead of when someone remembers.

### Overnight: running the real thing, then enumerating

Two of the day's fixes had only ever been exercised by their own tests. Running the programs for real, against nothing staged, caught the price source returning 500 on both games: 723 items read, none priced, and the guard written hours earlier for a different outage refused the total correctly. The same run showed a skip message naming the wrong branch and a console line printing "€0.00" as a fact; both fixed. A second run ten minutes later hit rate limiting instead and produced the other branch correctly.

Then the method changed: list every query that asks the same question, and every place a status field is written. That found the weekly comparison unfiltered (it would have announced a gain from nothing this Sunday), a dashboard table labelling zeros as "ok", a display daemon reporting every service "off" when its probe failed, a disk showing a reassuring 0% when unreadable, and a connected flag that could only ever go up.

Also measured rather than guessed: the dashboard's amber threshold was lighting on one healthy cycle in ten, because one number served two signals whose real cadences are 30 and 121 seconds.

### Running itself

The operator set the session to re-enter every twenty minutes and manage these projects on its own. The first thing that needed to exist was a procedure rather than a habit.

`healthcheck.py` is that procedure: repositories in sync and free of credentials, both boards reachable, one farming daemon and not two, the display actually drawing a frame, the deployed binary matching the last commit that touched its source, the Steam session still alive. One command, same order, same output shape every time.

Its exit code distinguishes three answers, not two: passed, failed, and **could not be measured**. Everything in this log argues that the third is a distinct state, so a tool written to watch the estate has no business collapsing it.

It found two things about itself on the first honest run. Executed from the environment that holds the ssh keys, it resolved the wrong home directory and saw no repositories at all — reported as unmeasured, which is the distinction doing its job rather than a silent zero. And it compared the deployed binary against HEAD, which a documentation commit is enough to break; it now compares against the last commit that touched the sources, still catching the stale binary the check exists for.

One branch went unverified after four attempts to mutate it, each defeated by a different path-resolution quirk. The commit says so. A gap that is written down is a different thing from a gap that is implied not to exist.

### Asked a direct question, answered it wrong three times

The operator asked whether the inventory bot sees items bought in the last seven days, which Steam holds before they can be traded or sold.

- **The search found nothing because it was looking for the wrong words.** Steam writes "Tradable/Marketable After 5 Aug @ 5:00am"; the query was for "Tradable After". Four items were held. The answer given was that none were, and it took "FAUX !!!" and three pasted item names to move it.
- **The first correction was also wrong**, blaming a French locale that had nothing to do with it. The request had asked for English and received English.
- **The counter then counted the wrong thing.** Held items were only tallied if they also had a price, so three stickers too new to be listed went uncounted and the report announced one hold out of four. Being held is a fact about the item; being priceable is a fact about the market. Those two had been pulled apart in six other places over the previous two days.

Underneath the wrong answers was a real defect, which is why they mattered. Held items carry `marketable = 0` and were dropped from the inventory outright, so a purchase vanished for a week and returned as an unexplained jump. They are now kept, counted, valued, and shown with Steam's own unlock date, while permanently non-marketable items stay excluded.

One more thing surfaced while measuring: the report has been labelling euros as dollars since the switch to bulk pricing that morning. Introduced by the same session that then failed to notice it for six hours.

### A report that says something, and everything that broke on the way

The board's daily message said a total and nothing else. The bot it replaced named the holdings, ranked what was worth selling, and flagged what was wrong with what was held. All of that is back, ported from the Python engines rather than rewritten: per-game split, evolution on four horizons, overnight movers, sell scores, the anti-trap verdicts and their thresholds, supply-decay holds, top 25 per game, every item linked.

Four things broke on the way, and each was a solved problem sitting nearby.

- **Every link was dead.** The marketplace search URL answers 200 with an empty application shell, so the status code confirms the mistake rather than catching it. None had been opened before shipping; the operator found them. Two hundred kilobytes versus two, distinguishable in one request.
- **Three sends refused with a bare 400.** An item named "Dreams & Nightmares Case" put a raw ampersand inside an href, which ends an HTML parse. The escaping helper's own comment had said so an hour earlier, applied to the text and not to the link beside it.
- **The splitter cut mid-tag.** At 17500 characters against a 4096 limit it fires every time, and it cut on byte offsets, landing inside tags and inside multibyte characters. The sibling bot fixed this in June by splitting on lines. The content was ported without the constraint it lives under.
- **The market indicator was measuring nothing**, in the original. It divided the preferred price by the suggested price, and the preferred price *is* the suggested price whenever one exists: a ratio of 1.0 everywhere and a light that was green regardless. Measuring the real undercut turned it permanently red instead, so the verdict was dropped and the figure kept until there is history to calibrate against.

Also corrected: "Hier +915 EUR (+175%)" compared against a measurement from twelve days earlier, because no valid snapshot exists in between. The figure was right, the word was not.

---

## Session of 2026-08-02: turning the audit on the auditors

The estate tool was run first, because it is the procedure. It returned twenty-five controls, zero failures, two unmeasurable. The two unmeasurable lines were the only interesting output, and everything below came out of reading them instead of the twenty-three green ones.

### The board that was never checked

One of the two single-board machines had never been probed by the tool built to probe them. Its ssh key lives only in the WSL filesystem, the tool read `~/.ssh/` from the Windows profile, and it had therefore printed `?` on every run since it was written, under a screen of green. The file's own docstring says the keys live in WSL, four lines above the code that reads them from the other home.

Keys are now located across both filesystems, an absent key reads as *not probed* rather than *unreachable*, and six board controls report a measured value for the first time, including the guard against the farming daemon running as two copies. Recorded as E32.

### A check that could not fail

Ten repositories were reported `sync`. The comparison was `HEAD` against `@{u}`, which is a local ref recording what this machine last heard from the server. Nothing fetched. **The repository was being compared to its own copy of the answer**, and the check had never been capable of returning anything else. Shown by a scratch clone whose remote is pushed to from a second clone: `sync` before a fetch, `DIVERGE` after, same repository, same command. It now asks `ls-remote`, and offline reads as unmeasured. Recorded as E36.

### Backup scope, third instance

The manifest carries a comment dated the previous day explaining why it had gone stale: a service's init script backed up without the config it sources. It had happened again, one line below that comment, for the next service added. The gap was one file, not the four an audit reported: three of those are in a public repository and correctly excluded, and over-counting in a short list is noise rather than surplus.

The comparison is no longer trusted to memory. Every manifest entry must still exist on the board, every `/etc` config referenced by a covered script must itself be covered, and three regenerated files carry a named exclusion each. Recorded as D2c.

### Two auditors that said clean about what they had not read

The note auditor dropped unreadable notes with a bare `continue`: a note holding a token, made unopenable, turned a run that had reported the credential into `clean`, exit 0. The credential scanner let its own error type escape `main`, so a repository with no commits exited 1, the code it documents as *a credential was found*, while exit 2, *could not scan*, never fired. Both now distinguish clean, problem and could-not-measure. The duplicate finder and the directory mapper were attacked the same way and held. Recorded as D10.

### Three findings that were not findings

Recorded because the near-misses are the method. A delegated agent reported a bot dead for twenty-two days; the metric it read counts human messages, and the bot was holding two live connections the first probe missed by reading the IPv4 table on a machine that talks IPv6 (E33). A board reporting a load average of three turned out to have three vendor kernel threads parked in uninterruptible sleep since 2.58 seconds after boot, having never consumed a single tick, on a board with no camera attached (D8). A DNS relay whose log is ninety-nine percent errors resolved twenty domains out of twenty when asked with a denominator; it logs failures and nothing else (D9).

### Corrections to this record

The headline incident ran for **eleven** days, 21 to 31 July inclusive, eleven reports sent. Three files here said ten and two said eleven, and the board's log settles it. The count is now the same in all five places and D1 carries the dates so the next reader can check it in one command (E35).

One defect was introduced and caught within the hour: the new backup-scope control joined manifest paths with spaces, so an entry containing one was never tested under its own name. Found by mocking the transport and reading the message that would have been sent; the board, where every real path is space-free, would have answered green (E37).

### The probe that fed the next probe

An audit ran the inventory bot's regression suite. The suite imports `main`, and `main` attached a file handler to the production journal at import time, so the test wrote rate-limit warnings and an abandoned-scan line into the log a human reads, against a fabricated URL, in production's own format. An hour later a second audit read that journal's timestamp as proof a real scan was running despite a disabled scheduled task, and concluded another trigger existed. There is none. Logging setup moved under `__main__`, verified both ways. Recorded as E38.

### Jobs the estate believes it runs

A sweep of every non-vendor scheduled task against its own output files. The backup and the three skin-radar jobs are enabled, exit zero, and their outputs carry timestamps that agree with their last run, the backup's to the second. The inventory job has two schedulers and both are disabled, one pointing at a directory the project left months ago. And the orchestrator process the notes describe as starting at boot has no task, no registry entry, no startup shortcut and no directory: there is nothing to start. All three are reported and none were changed, because standing configuration is the operator's. Recorded as D11.

### What held

The webhook daemon and the gateway client were attacked on the axes that broke them before: signature verification failing open when the key cannot be fetched, wire types asserted after decoding rather than on the bytes, empty collections standing in for errors, unbounded retry, unbounded dedup. Nothing was found. Its suite runs 30 tests, all passing, checked directly rather than taken from the audit that reported it. The one structural note is that two background goroutines carry no `recover`, so a panic in either takes the process with it; no reachable trigger was demonstrated.

### Two services that fail as a plausible success

The status screen computed its liveness needle as `(needle or label).strip()`, stripping after the fallback, so a needle of pure whitespace survived as truthy and then went empty. Liveness is `needle in line` over the process list, and the empty string is a substring of every line, so every watched service rendered as running, in green, on any machine with any process. Four config shapes reach it. Neither live board triggers it, because both configs happen to be well formed: it is a defect waiting for a typo, in the component whose job is to be believed at a glance. Its unreadable load average also rendered healthy, between two rows already fixed for exactly that. Recorded as D12.

The skin scanner's stale-cache fallback had no age limit, unlike the fresh path it mirrors. A dead session fails every item, so every item comes back off disk, so the count is normal and both guards pass, because both count items and neither looks at dates. Shown with a cache entry aged four hundred days: it returns priced, not absent. Stale entries older than a week are dropped, stale-served items are counted, and a majority-stale run is refused. Its record file was also written truncate-in-place while three scheduled tasks share it, and a half-written file read back as "no previous run", which short-circuits the remaining guard: one run's crash disarmed the next. Atomic rename, and unreadable-but-present now refuses. Recorded as D13.

### The correction that was written down and never built

E16 cost two months: the farmer was believed to work because XP rose, and XP rose for a second uncontrolled cause. The fix that followed was a rule, not code. The obvious implementation sacrifices a control account nobody maintains; the window already exists for free, because every restart and outage is a period where the daemon is not running. The last total is now recorded on each successful poll, and at startup, before the first event is sent, each account's XP is read and compared against it. Four answers kept distinct: exclusive, not exclusive, nothing to compare, incoherent. The fourth exists because the test caught the first two unknowns rendering the same sentence. Cross-compiles for the board, deliberately not deployed.

---

## Session of 2026-08-02, morning

### The DNS blocker would have installed a 404 page and called it an update

`curl -s` without `-f` exits 0 on an HTTP 404 and writes the error body to the output file, and the script's whole gate was that exit code plus a non-empty check. A fourteen-byte error page passes both. A moved upstream path was therefore enough to replace 93,000 blocked domains with `404: Not Found`, reload the resolver against it, and log `OK: 0 domaines`: blocking off for the whole network, with the only record saying it went fine. Measured on the real host, 200 gives 99,276 domains and a missing path gives 0, and both passed identically. Now `-f` on the download, the candidate counted before anything is replaced, and a floor relative to the installed list. Six cases against their controls. Recorded as D14, not deployed.

### Background loops that took the daemon down with them

The webhook daemon's key-refresh and subscription-repair goroutines had no `recover`, so a panic in either killed webhook intake and SSE fan-out along with it. A bare `recover` would have been worse: the loop would die silently while the process stayed up and `/health` kept answering. Both are supervised now, restarting with a capped backoff and counting the panic in `/health` under the name of the loop, with the field absent until it happens. 33 tests, up from 30.

### Cron on the board, and the third region of the radar

Five cron entries ran on the board with nothing verifying any of them: cron reports no failure, it reports nothing. Six outputs are now compared against the cadence in the crontab, 36 hours of slack for a daily job and eight days for a weekly one. busybox has no `stat -c`, so age is tested rather than computed, with `find -mmin +N`, verified against a control on the board first. Fresh, stale, and no output at all are three answers, and the third used to be unaskable. The three skin-radar tasks are also listed separately: they share one output file, so with one enabled the file stays fresh while two thirds of the coverage is gone.

### Configuration that describes a machine which no longer exists

A relay is launched at every logon from a path that does not exist, by `pythonw`, which shows nothing when it fails. A scheduled task for the same relay points at a third absent path. Three configured launch points, none working, nothing reporting it. With the stale backup manifest and the disabled job list, that is the same drift in three different media, none of which had anything comparing them against the machine. Reported, not changed. Recorded as D15.

### A shared client that stayed open and stopped speaking

The realtime client behind nine extensions switched on `frame.event` after parsing. `JSON.parse('null')` returns null, `null.event` threw out of the message listener with no catch anywhere above it, and the frame behind it was never delivered while the socket stayed OPEN and the state callback said nothing. It also had no liveness detection: fifty ping cycles with every pong answered and fifty with none produced byte-identical state, so a dead channel and a quiet one were the same object. Non-object frames are dropped, any inbound byte stamps the channel, and two silent ping intervals now report `stale` and close, reusing the existing reconnect. Proven against the pre-fix file, which raises the exact TypeError and holds the socket open. Recorded as D16.

---

## Session of 2026-08-02, afternoon: everything deployed

Three days of writing fixes and not shipping them ended here. Every pending change went to the hardware it was written for, and each one was verified on the machine rather than in the repository.

### The blocklist fix, live

Deployed to the board and run for real: 93,156 domains became 99,276, dnsmasq stayed up, twenty resolutions through the local resolver answered, and an advertising domain still resolves to nothing. The previous script and the previous list are kept beside them.

### The attribution channel, live, and what it found

E16 was measured for the first time. The daemon was stopped with its keepalive pinned off and its own recorded totals compared on restart. Both accounts gain XP while it is stopped: one by twelve over six minutes, then both by four over three. The daemon's own contribution is not established for either. The first stop alone said one account was clean, and that claim survived four minutes before the second stop contradicted it, which is the entry's real lesson. Recorded as D17.

### What the deployment cost, and what it exposed

The probe crashed the daemon on its first start and the farmer was down for two minutes: it called the HTTP path before the TLS client was built. Three tests shipped with it, all covering the pure helpers, none calling the one function that runs on the board. Recorded as E39.

Then the deployment appeared to succeed while changing nothing. The board's init script has a `start` and no `stop`, so `stop` matched no case and exited 0; the binary was replaced under a live process and the keepalive declined to start a second. Only `/proc/<pid>/exe` reading `(deleted)` gave it away. The script now stops by pid, holds the kill switch across a keepalive tick, reports what is rather than what was asked, and answers `status`. Recorded as E40.

### The rest of the estate

The daily inventory task is enabled again and next runs tomorrow at 08:00; all six scheduled jobs and the six cron outputs now report green. The relay's token left the source for a file outside the tree, with the old published value denied by name, constant-time comparison, and a log so that a `pythonw` process can no longer die without a word. Its autostart entry was repointed from a path deleted months ago to the real one, where it now refuses to start until a token exists, so the configuration describes the machine for the first time.

---

## Session of 2026-08-03: the work was findable to nobody

Six public repositories, five of them the Kick estate, audited for the one thing none of the previous sessions had measured: whether anything published could be found by someone not given the link.

### Four repositories with no topics at all

`kick-drops-miner`, `kick-core`, `kickbus` and `autonomy-log` carried zero GitHub topics between them, which means zero surface in topic search and no signal to the recommendation graph. Each now carries fifteen to eighteen, derived from the source rather than the description: the miner's actual stack (Selenium, undetected-chromedriver, customtkinter, seven locales), the gateway client's real constraint (service worker only, Cloudflare closes every other host), the relay's transport (signed webhooks in, SSE out, Go, riscv64).

`kick-ad-blocker` had five, all correct and all generic. Fourteen were added covering the browsers it actually ships on, the blocking mechanism, and the category a person would search.

### The one repository that could not be improved by addition

`kick-chat-translator` was already at twenty topics, which is the ceiling GitHub enforces. Four were spending a slot without earning it: `javascript` on a TypeScript project, `translator` next to `translation`, `mv3` next to `manifest-v3`, and `kick-tv`, which is not what the site is called. They were traded for `kick`, `kick-com`, `vod` and `i18n`. The first two were missing on the most visible repository of the set, which is the sort of gap that only shows up when the metadata is read as data rather than admired as prose.

### A compiled artifact in the repository about rigour

`__pycache__/healthcheck.cpython-310.pyc` had been tracked since the health tool landed. Removed, with a `.gitignore` so it does not come back. Nothing was verified by its presence and nothing is lost by its absence, but a repository whose subject is the gap between what a tool reports and what is true should not ship the byte-compiled output of the tool that failed both audits.

Nothing broke in this session, which is worth stating rather than leaving to inference: the pass was metadata only, no code path was touched, and there is no ledger entry to add.
