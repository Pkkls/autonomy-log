# AGENTS.md

## SCHEMA

PURPOSE: cold-start context for an agent operating on this repository. Machine-first. Read this file before any other.

SECTIONS: SCHEMA, DERIVED, ASSERTED, INVARIANTS, OPEN. Order is fixed.

ID-PREFIX: `DRV-` re-derivable fact. `AST-` asserted, not derivable. `INV-` machine-checkable condition. `OPN-` unresolved.
ID-RULE: stable, never reused, never renumbered. Allocate above the current maximum in each series.

DERIVED-COLUMNS: `ID | FACT | VALUE | COMMAND`. COMMAND regenerates VALUE exactly. This section is a CACHE, not a source; it can be rebuilt entirely by running its own commands.
ASSERTED-COLUMNS: `ID | CLAIM | DATE | SOURCE`. Not derivable from the repository. Irreducible.
INVARIANTS-COLUMNS: `ID | CONDITION | COMMAND | EXPECT`. EXPECT is the required process exit code.
OPEN-COLUMNS: `ID | UNRESOLVED | WHY`.

ESCAPE: `\|` inside a cell is a literal pipe character.
SHELL: COMMAND cells are POSIX sh, executed as `sh -c`, from the repository root.

SCOPE: DERIVED reads `HEAD`, never the index and never the working tree. `INV-01` asserts `HEAD` equals `origin/main`. Those two together, and only together, mean DERIVED describes what a reader can see. A green DERIVED with a red `INV-01` describes a tree that exists only on one machine.

VERIFIER: `python check_agents.py`. Three outcomes, because two would put one answer where another belongs.
EXIT-0: everything holds and the tree is published.
EXIT-2: everything holds except `INV-01`, meaning the values are correct for this machine and not yet visible to anyone. Not an error. The owner clears it by pushing.
EXIT-1: at least one real disagreement, each named by ID. All failures are reported, never just the first.
LOCAL-ONLY: `INV-08` needs machine configuration that is absent from a clean checkout. It is skipped when the `CI` environment variable is set, and the skip is printed, never silent.
NOT-AN-INVARIANT: external links are checked by `python check_agents.py --extlinks`, on a weekly CI schedule, not in this table. They need the network, and a transient outage failing every local run would be a false positive, which in a monitoring tool costs more than a miss.
RUNTIME: `.github/workflows/verify.yml` runs the verifier on every push and pull request. Without it the rules in this file would have no runtime and would not bind, which is AST-09 applied to AST-09.
ESCAPE-TRAP: a COMMAND cell cannot contain a regex pipe. The table's `\|` escape and a regex `\|` are the same two characters, and unescaping turns `^\|` into `^|`, which matches every line instead of none. Write the pattern without a pipe.
CLASSIFICATION-RULE: a claim with no regenerating command belongs in ASSERTED or OPEN, never in DERIVED. An ASSERTED claim disguised as DERIVED is an assertion with no age and no owner; when in doubt, classify as ASSERTED.

## DERIVED

| ID | FACT | VALUE | COMMAND |
| --- | --- | --- | --- |
| DRV-01 | tracked files | 12 | `git ls-tree -r --name-only HEAD \| wc -l` |
| DRV-02 | agent-error entries in ledger | 68 | `git grep -h -c -E '^### E[0-9]+\.' HEAD -- LEDGER.md` |
| DRV-03 | environment-discovery entries in ledger | 17 | `git grep -h -c -E '^### D[0-9]+\.' HEAD -- LEDGER.md` |
| DRV-04 | lettered ledger entries | 2 | `git grep -h -c -E '^### E[0-9]+[a-z]\.' HEAD -- LEDGER.md` |
| DRV-06 | licence | MIT License | `git show HEAD:LICENSE \| head -1` |
| DRV-07 | machine config tracked | 0 | `git ls-tree -r --name-only HEAD -- estate.json \| wc -l` |
| DRV-08 | taxonomy layer rows in research | 7 | `git grep -h -c -E '^. L[0-9] ' HEAD -- RESEARCH.md` |
| DRV-09 | top-level research sections | 13 | `git grep -h -c -E '^## ' HEAD -- RESEARCH.md` |

DRV-05, DRV-10, DRV-11 and DRV-12 were retired: commit counts and file byte sizes change on every ordinary commit, so they turned the verifier red without ever meaning anything. Their ids are not reused. See AST-15.

## ASSERTED

| ID | CLAIM | DATE | SOURCE |
| --- | --- | --- | --- |
| AST-01 | Repository records errors made by coding agents under widening autonomy on real systems, each with its detection path and cost. It is a record, not a library. | 2026-07-30 | repository owner |
| AST-02 | Committing and pushing to `main` of this repository is authorized standing, no confirmation needed. `push --force`, history rewriting, and any other repository remain forbidden. This supersedes the earlier rule that forbade pushing outright; that rule was written when the repository was private and the campaign's brief required it. | 2026-08-15 | repository owner |
| AST-03 | Never publish anything identifying a machine, a user, a network address, an ssh key filename, an absolute path, or a private repository name. Machine-specific values belong in the gitignored config read by the health tool. | 2026-08-15 | E64, E66 |
| AST-04 | Everything written for this repository is in English, plain prose, no em dashes, no hollow openings, no robotic connectors. | 2026-07-30 | repository owner |
| AST-05 | No claim without a controllable source. Testimony with no artifact behind it is published marked as such, never promoted to fact. | 2026-08-15 | RESEARCH section 8 |
| AST-06 | Two campaigns are recorded. First: one agent, one session, widening autonomy. Second: two machine sessions with no shared context, one writing briefs and one executing, documents passed by hand through the operator. | 2026-08-15 | RESEARCH 3.2 |
| AST-07 | The argument has three questions, added in order because each proved insufficient: is this true, is this true because of me, do I know this or did I inherit it. | 2026-08-15 | README |
| AST-08 | Two claims were withdrawn rather than defended: the second campaign is not a control condition, its confounder being inseparable, and the modality blind spot weakens to an ordinary lesson because a machine node did measure the overflow once pointed at it. | 2026-08-15 | RESEARCH 6e |
| AST-09 | A rule written in a document has no runtime and does not bind. Install it as a program positioned before the action, or expect it to be broken by its own author. | 2026-08-15 | E53, E65 |
| AST-10 | A check never observed failing has proved nothing. Witness every detector red on a constructed broken case and quiet on a clean one before trusting its green. | 2026-07-30 | RESEARCH section 7 |
| AST-11 | Never read an exit code after a pipe. Capture the checked process's own status. | 2026-08-15 | E51, E65 |
| AST-12 | `git add` with named files only. Never `-A`, never `.`. | 2026-08-15 | repository owner |
| AST-13 | Ledger entry format for NEW entries: `### E<n>. <declarative title>`, a bolded severity clause, the mechanism, then `Caught by:`, `Fix:`, `Class:`, with `Class:` citing other entries by identifier. The convention accreted and earlier entries predate it: measured across 83 entries, `Severity:` appears 68 times, `Caught by:` 61, `Class:` 54, `Fix:` 43. Do not retrofit the older ones; the record is what it was. | 2026-08-15 | LEDGER.md, measured |
| AST-14 | Adding a ledger entry means allocating above the current maximum by counting, then re-verifying after writing. Numbering has collided silently twice in this record. | 2026-08-15 | E46, E54 |
| AST-15 | A DERIVED row must be stable under ordinary work. Commit counts, byte sizes and timestamps change on every commit and make the verifier red without meaning anything, which teaches its reader to skip it. Entry counts are kept precisely because changing one should force a re-verification of the numbering. | 2026-08-15 | E26, AST-14 |
| AST-16 | An agent holds standing stewardship of this repository: keep it correct, keep the verifier and its runtime working, repair drift, and record errors as they occur. Stewardship is maintenance and recording. It is not a mandate to produce content. | 2026-08-15 | repository owner |
| AST-17 | This repository records work done elsewhere and has no subject matter of its own. Every entry must trace to something observed: a commit, a command output, a measurement, a dated report. An agent given a standing mandate will be tempted to generate entries to justify it, and a fabricated entry destroys the only property this record has. A quiet period correctly produces nothing, and that must be reported as the result rather than filled. | 2026-08-15 | repository owner, AST-16 |
| AST-18 | An agent also acts as analyst over the estate's other sessions, whose transcripts are readable. Collection and raw analysis stay local: transcripts carry the operator's private work and must never reach this repository. Only sanitized, artifact-backed findings are published. | 2026-08-15 | repository owner |
| AST-19 | An analyst examining a peer node in its own estate is not independent, and its tilts are enumerable with a direction each: shared instruction set, shared modality, asymmetric evidence, self-inclusion, survivorship of the record, outcome knowledge. Every finding names the ones that apply to it and their direction, inside the finding. A blanket admission at the top of a document changes no conclusion, which is why it is the comfortable option. | 2026-08-15 | RESEARCH 6f |

## INVARIANTS

| ID | CONDITION | COMMAND | EXPECT |
| --- | --- | --- | --- |
| INV-01 | HEAD equals origin/main, so DERIVED describes what is published | `test "$(git rev-parse HEAD)" = "$(git rev-parse origin/main)"` | 0 |
| INV-02 | working tree clean | `test -z "$(git status --porcelain)"` | 0 |
| INV-03 | ledger E series has no gap and no duplicate | `python check_agents.py --numbering E` | 0 |
| INV-04 | ledger D series has no gap and no duplicate | `python check_agents.py --numbering D` | 0 |
| INV-05 | committed tree carries no identifying data | `python check_agents.py --secrets` | 0 |
| INV-06 | every relative markdown link resolves inside the committed tree | `python check_agents.py --links` | 0 |
| INV-07 | machine config is ignored and never tracked | `git check-ignore -q estate.json` | 0 |
| INV-08 | health tool selftest passes | `python healthcheck.py --selftest` | 0 |

## OPEN

| ID | UNRESOLVED | WHY |
| --- | --- | --- |
| OPN-01 | Number of rounds in the second campaign | Four definitions are available, journal section, brief, session, commit range, and they return four different numbers. Asserting one would repeat E59. |
| OPN-02 | Completeness of the second campaign's record | The journal and the git history agree on 41.2% of the union of item numbers they mention. Every count taken from the journal is a lower bound. |
| OPN-03 | Errors of the brief-writing node that it did not notice itself | That node's reasoning left no artifact. Only finished briefs exist, never drafts, so nothing can search for what it missed. |
| OPN-04 | Identifying values already present in git history | Removing them from the current tree does not retract them. The remedies were never publishing, or rewriting public history, and the second is irreversible on existing clones. |
| OPN-05 | Whether the conclusions generalise beyond this estate | One owner, one machine, two campaigns, no repetition and no counterfactual. No generalisation is attempted. |
