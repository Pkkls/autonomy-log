#!/usr/bin/env python3
"""Verify AGENTS.md against the committed tree.

AGENTS.md is the spec and this file is its runtime. Every DERIVED row carries
the command that regenerates its value; every INVARIANT carries a command and
the exit code it must return. This runs them and disagrees loudly.

The document is the single source of truth. Nothing already written there is
reimplemented here, so the two cannot drift apart.

Scope: DERIVED reads HEAD. INV-01 asserts HEAD equals origin/main. Only both
together mean the values describe what a reader can see, which is the
distinction E66 was written about.

Modes:
  (none)          every DERIVED row and every INVARIANT
  --numbering E   ledger E series continuity, used by INV-03
  --numbering D   ledger D series continuity, used by INV-04
  --secrets       identifying data in the committed tree, used by INV-05
  --links         relative markdown links resolve, used by INV-06
  --sections      the SECTIONS line matches the file, used by INV-09
  --extlinks      external links serve real content. Not an INVARIANT: it
                  needs the network, and a transient outage turning the local
                  verifier red would be a false positive, which costs more
                  than a miss (E26). CI runs it on a schedule.

Exit 0 when everything holds and the tree is published. Exit 2 when everything
holds except INV-01, meaning the values are right for this machine and not yet
visible to anyone; that is not an error and the owner clears it by pushing.
Exit 1 on any real disagreement. Three outcomes rather than two, because a
checker with room for two eventually reports one as the other.

Every failure is printed with its id and the run does not stop at the first,
because reading all findings before believing any is this repository's own
lesson (E26).

Commands are POSIX sh. Run from the repository root.

Cost, measured 2026-08-15, median of five runs after a discarded warm-up, on
twelve tracked files. Method matters here: a single first invocation read
5149 ms and would have sent this in the wrong direction entirely.

    full run                2057 ms
      12 sh -c spawns       1044 ms   DERIVED rows and the non-python invariants
      5 python respawns     1013 ms   of which healthcheck --selftest is 165
    CI, INV-08 skipped      1892 ms

Not optimised, deliberately. Roughly half the cost is respawning this file
through the commands written in the INVARIANTS table, and that indirection is
the design's central guarantee: the table holds the command and the verifier
runs what the table says. Calling the functions directly would save about a
second and make the table decorative, free to drift from what actually
executes, which is the failure this whole apparatus exists to prevent. Two
seconds on a push is a fair price for that, so PRC-5 yields to PRC-4 here.

The one real inefficiency is check_secrets reading each tracked file with its
own `git show`, which is O(files) in subprocess spawns. At twelve files it
costs 434 ms. Batching would win maybe 350 ms at the price of parsing a batch
protocol, which is not worth it yet. Revisit if the tree passes roughly fifty
files, where the same pattern would cost several seconds.
"""

import os
import re
import subprocess
import sys

DOC = "AGENTS.md"
REF = "HEAD"

# Invariants that depend on this machine's own configuration and cannot hold on
# a clean checkout. Skipped when CI is set, and the skip is always printed.
LOCAL_ONLY = {"INV-08"}

# Explicit utf-8. The default is the host locale codepage, which silently
# mangles any non-ascii byte before this file's logic ever sees it (E47).
ENC = {"encoding": "utf-8", "errors": "replace"}


def _lit(*parts):
    """Assemble a sensitive literal at runtime.

    Specimens below, and one pattern, would otherwise sit in this file as
    disclosure-shaped strings, and this file is scanned like every other one.
    A scanner that has to exempt itself from its own rules is not a scanner.
    """
    return "".join(parts)


def sh(cmd):
    """Run a shell command, return (exit code, stripped stdout)."""
    p = subprocess.run(["sh", "-c", cmd], capture_output=True, **ENC)
    return p.returncode, (p.stdout or "").strip()


def git(args):
    p = subprocess.run(["git"] + args, capture_output=True, **ENC)
    return p.returncode, (p.stdout or "").strip()


def cells(line):
    """Split a markdown table row on unescaped pipes."""
    parts = re.split(r"(?<!\\)\|", line.strip())
    if parts and parts[0] == "":
        parts = parts[1:]
    if parts and parts[-1] == "":
        parts = parts[:-1]
    out = []
    for c in parts:
        c = c.replace("\\|", "|").strip()
        if len(c) > 1 and c.startswith("`") and c.endswith("`"):
            c = c[1:-1]
        out.append(c)
    return out


def table(section):
    """Rows of the markdown table under a '## <section>' heading."""
    with open(DOC, encoding="utf-8") as fh:
        lines = fh.read().splitlines()
    rows, inside = [], False
    for line in lines:
        if line.startswith("## "):
            inside = line[3:].strip() == section
            continue
        if not inside or not line.startswith("|"):
            continue
        c = cells(line)
        if not c or c[0] == "ID" or set(c[0]) <= set("- "):
            continue
        rows.append(c)
    return rows


def committed_files():
    code, out = git(["ls-tree", "-r", "--name-only", REF])
    return out.splitlines() if code == 0 else []


def committed(path):
    code, out = git(["show", REF + ":" + path])
    return out if code == 0 else ""


# --- sub-checks, each invoked by an INVARIANT row ---------------------------

def check_numbering(series):
    text = committed("LEDGER.md")
    seen = {}
    for m in re.finditer(r"^###[ \t]+" + series + r"(\d+)([a-z]?)\.", text, re.M):
        seen.setdefault(int(m.group(1)), []).append(m.group(2))
    if not seen:
        print("FAIL numbering %s: no entries found, probe failure" % series)
        return 1
    nums = sorted(seen)
    dups = [n for n in nums if len([x for x in seen[n] if x == ""]) > 1]
    gaps = [i for i in range(1, nums[-1] + 1) if i not in seen]
    if dups or gaps:
        print("FAIL numbering %s: gaps=%s duplicates=%s" % (series, gaps, dups))
        return 1
    print("ok   numbering %s: %s1..%s%d continuous" % (series, series, series, nums[-1]))
    return 0


# Each rule ships a positive specimen. A detector that does not fire on its own
# specimen is a broken probe, and its silence on the real tree means nothing
# (AST-10). Specimens are assembled at runtime, never written out whole.
SECRET_RULES = [
    (r"\b" + _lit("k", "il") + r"\b", "owner name",
     _lit("k", "il") + " ran the probe"),
    (r"(?i)[A-Z]:\\+" + _lit("Us", "ers") + r"\\+[A-Za-z]", "absolute user path",
     _lit("C:\\\\Us", "ers\\\\someone")),
    (r"\b(?:10|192\.168|172\.(?:1[6-9]|2\d|3[01]))\.\d+\.\d+\b", "private address",
     _lit("192.", "168.1.50")),
    (r"/home/[a-z][a-z0-9_-]*/", "home directory path",
     _lit("/ho", "me/someone/")),
    (_lit("/mnt", "/c/Us", "ers"), "mounted user path",
     _lit("/mnt", "/c/Us", "ers")),
    (r"\b\w+_key\b", "key filename", _lit("nano", "_key")),
    (r"(?i)(api[_-]?key|secret|password)\s*[=:]\s*\S{8,}", "credential",
     _lit("api", "_key: ") + "ABCDEFGH12"),
    (r"\b(?:sk|ghp|gho|xox[baprs])[-_][A-Za-z0-9]{16,}", "provider token",
     _lit("gh", "p_") + "ABCDEFGHIJKLMNOPQ"),
    (r"-----BEGIN [A-Z ]*PRIVATE KEY-----", "private key block",
     _lit("-----BEGIN RSA ", "PRIVATE KEY-----")),
]

# Phrases that legitimately match a pattern because they discuss a disclosure
# rather than commit one.
ALLOWED = ("killed", "one long session", "single-session")

CLEAN = "a plain sentence about ledger entries and commits"


def check_secrets():
    unproven = 0
    for pattern, label, specimen in SECRET_RULES:
        if not re.search(pattern, specimen):
            print("FAIL detector '%s' did not fire on its own specimen" % label)
            unproven += 1
        if re.search(pattern, CLEAN):
            print("FAIL detector '%s' fires on clean text" % label)
            unproven += 1
    if unproven:
        print("FAIL secrets: %d unproven detector(s), a clean result would mean nothing"
              % unproven)
        return 1
    hits = 0
    for path in committed_files():
        for n, line in enumerate(committed(path).splitlines(), 1):
            if any(a in line for a in ALLOWED):
                continue
            for pattern, label, _ in SECRET_RULES:
                if re.search(pattern, line):
                    print("FAIL %s:%d [%s] %s" % (path, n, label, line.strip()[:80]))
                    hits += 1
    if hits:
        print("FAIL secrets: %d disclosure(s) in the committed tree" % hits)
        return 1
    print("ok   secrets: %d detectors witnessed, 0 disclosures committed"
          % len(SECRET_RULES))
    return 0


def check_extlinks():
    """External links must serve real content, not merely answer 200 (E24).

    Deliberately not an INVARIANT. It needs the network, so a transient outage
    would turn the local verifier red for a reason that is not a defect, and in
    a monitoring tool a false positive costs more than a miss (E26). It runs on
    a schedule in CI instead.
    """
    import urllib.error
    import urllib.request

    def body(url):
        req = urllib.request.Request(url, headers={"User-Agent": "check-agents"})
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return r.status, r.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            return e.code, ""
        except Exception as e:  # network, DNS, TLS
            return 0, str(e)

    def serves_content(url):
        status, text = body(url)
        return status == 200 and len(text) > 1000 and "Page not found" not in text

    # The detector must be able to fail, or its silence proves nothing (AST-10).
    control = "https://github.com/Pkkls/deliberately-absent-witness-repository"
    if serves_content(control):
        print("FAIL extlinks: the negative control passed, detector is unproven")
        return 1

    urls = set()
    for path in committed_files():
        if path.endswith(".md"):
            for _t, href in re.findall(r"\[([^\]]+)\]\((https?:[^)]+)\)",
                                       committed(path)):
                urls.add(href)
    bad = 0
    for url in sorted(urls):
        if not serves_content(url):
            print("FAIL extlinks: %s does not serve real content" % url)
            bad += 1
    if bad:
        print("FAIL extlinks: %d of %d dead" % (bad, len(urls)))
        return 1
    print("ok   extlinks: control refused, %d external links serve real content"
          % len(urls))
    return 0


def check_sections():
    """The SECTIONS line must list exactly the sections the file has, in order.

    Adding a section and forgetting to declare it leaves a document whose own
    schema understates it, which a reader has no way to notice. Written because
    the precedence section was added by hand and the declaration was updated
    from memory, which works once.
    """
    with open(DOC, encoding="utf-8") as fh:
        src = fh.read()
    m = re.search(r"^SECTIONS:\s*([^.]+)\.", src, re.M)
    if not m:
        print("FAIL sections: no SECTIONS line found, probe failure")
        return 1
    declared = [s.strip() for s in m.group(1).split(",")]
    actual = re.findall(r"^## (.+?)\s*$", src, re.M)
    if declared != actual:
        print("FAIL sections: declared %s, found %s" % (declared, actual))
        return 1
    print("ok   sections: %d declared and present in order" % len(actual))
    return 0


def check_links():
    files = set(committed_files())
    bad = total = 0
    for path in sorted(f for f in files if f.endswith(".md")):
        for _text, href in re.findall(r"\[([^\]]+)\]\(([^)]+)\)", committed(path)):
            if href.startswith("http"):
                continue
            total += 1
            target = href.split("#")[0]
            if target and target not in files:
                print("FAIL %s: relative link '%s' resolves to nothing" % (path, href))
                bad += 1
    if bad:
        return 1
    print("ok   links: %d relative links resolve inside the committed tree" % total)
    return 0


# --- full run ---------------------------------------------------------------

def run_all():
    failures = []

    derived = table("DERIVED")
    for row in derived:
        rid, fact, want, cmd = row[0], row[1], row[2], row[3]
        code, got = sh(cmd)
        if code != 0:
            failures.append("%s command failed (exit %d): %s" % (rid, code, fact))
        elif got != want:
            failures.append("%s expected '%s', derived '%s': %s" % (rid, want, got, fact))

    invariants = table("INVARIANTS")
    for row in invariants:
        rid, cond, cmd, expect = row[0], row[1], row[2], row[3]
        if rid in LOCAL_ONLY and os.environ.get("CI"):
            # Printed, never silent: a check that vanishes without saying so is
            # indistinguishable from one that passed.
            print("skip %s: needs machine-specific configuration, absent in CI" % rid)
            continue
        code, _ = sh(cmd)
        if str(code) != expect.strip():
            failures.append("%s exit %d, expected %s: %s" % (rid, code, expect, cond))

    print("%d DERIVED rows, %d INVARIANTS" % (len(derived), len(invariants)))
    if not derived or not invariants:
        print("FAIL parsed nothing from %s, probe failure" % DOC)
        return 1

    # Three outcomes, not two. "Correct but not published yet" and "wrong" are
    # different answers, and a checker with room for two eventually reports one
    # as the other. This estate's oldest lesson, applied to itself.
    pending = [f for f in failures if f.startswith("INV-01")]
    real = [f for f in failures if not f.startswith("INV-01")]
    for f in real:
        print("FAIL " + f)
    if real:
        print("%d failure(s)" % len(real))
        return 1
    if pending:
        print("PENDING " + pending[0])
        print("ok   every value holds; this tree is not published yet, push to clear")
        return 2
    print("ok   AGENTS.md agrees with the published tree")
    return 0


def main(argv):
    if "--numbering" in argv:
        return check_numbering(argv[argv.index("--numbering") + 1])
    if "--secrets" in argv:
        return check_secrets()
    if "--sections" in argv:
        return check_sections()
    if "--links" in argv:
        return check_links()
    if "--extlinks" in argv:
        return check_extlinks()
    return run_all()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
