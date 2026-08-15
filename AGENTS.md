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

VERIFIER: `python check_agents.py`. Exit 0 = every DERIVED value and every INVARIANT holds. Non-zero = at least one failed, each named by ID. Failures are all reported, not just the first.
CLASSIFICATION-RULE: a claim with no regenerating command belongs in ASSERTED or OPEN, never in DERIVED. An ASSERTED claim disguised as DERIVED is an assertion with no age and no owner; when in doubt, classify as ASSERTED.

## DERIVED

| ID | FACT | VALUE | COMMAND |
| --- | --- | --- | --- |
| DRV-01 | tracked files | 11 | `git ls-tree -r --name-only HEAD \| wc -l` |
| DRV-02 | agent-error entries in ledger | 66 | `git grep -h -c -E '^### E[0-9]+\.' HEAD -- LEDGER.md` |
| DRV-03 | environment-discovery entries in ledger | 17 | `git grep -h -c -E '^### D[0-9]+\.' HEAD -- LEDGER.md` |
| DRV-04 | lettered ledger entries | 2 | `git grep -h -c -E '^### E[0-9]+[a-z]\.' HEAD -- LEDGER.md` |
| DRV-05 | commits on the branch | 71 | `git rev-list --count HEAD` |
| DRV-06 | licence | MIT License | `git show HEAD:LICENSE \| head -1` |
| DRV-07 | machine config tracked | 0 | `git ls-tree -r --name-only HEAD -- estate.json \| wc -l` |
| DRV-08 | taxonomy layer rows in research | 7 | `git grep -h -c -E '^\| L[0-9]' HEAD -- RESEARCH.md` |
| DRV-09 | top-level research sections | 12 | `git grep -h -c -E '^## ' HEAD -- RESEARCH.md` |
| DRV-10 | LEDGER.md size in bytes | 150412 | `git cat-file -s $(git rev-parse HEAD:LEDGER.md)` |
| DRV-11 | RESEARCH.md size in bytes | 47365 | `git cat-file -s $(git rev-parse HEAD:RESEARCH.md)` |
| DRV-12 | CHANGELOG.md size in bytes | 49551 | `git cat-file -s $(git rev-parse HEAD:CHANGELOG.md)` |

## ASSERTED

| ID | CLAIM | DATE | SOURCE |
| --- | --- | --- | --- |
| AST-01 | Repository records errors made by coding agents under widening autonomy on real systems, each with its detection path and cost. It is a record, not a library. | 2026-07-30 | repository owner |
| AST-02 | Never `git push`. Publication is the owner's decision, not an agent's. Commit locally and report the push command. | 2026-08-15 | repository owner |
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
| AST-13 | Ledger entry format: `### E<n>. <declarative title>`, a bolded severity clause, the mechanism, then `Caught by:`, `Fix:`, `Class:`. `Class:` cites other entries by identifier. | 2026-08-15 | LEDGER.md |
| AST-14 | Adding a ledger entry means allocating above the current maximum by counting, then re-verifying after writing. Numbering has collided silently twice in this record. | 2026-08-15 | E46, E54 |

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
