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
- **Fixed:** a total failure to read inventories was indistinguishable from an empty account. The fetch logged its failure, returned an empty collection, and every downstream stage treated emptiness as data. Ten days of daily reports announced an empty portfolio, marked successful.
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
