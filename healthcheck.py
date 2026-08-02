#!/usr/bin/env python3
"""One command that answers "is the estate sound", the same way every time.

Every check in here was run by hand at least once during the session that
produced this repository, improvised each time and therefore not comparable
between runs. A procedure that varies cannot tell you whether something got
worse.

    python healthcheck.py              # everything
    python healthcheck.py --repos      # only the repository checks
    python healthcheck.py --boards     # only the two single-board machines

Exit code is 0 when every check passed, 1 when any failed, 2 when a check
could not be run at all. That last one is the point: "could not measure" and
"measured, fine" are different answers, and collapsing them is the mistake this
whole repository is about.
"""
import argparse
import json
import os
import subprocess
import sys

# --- what is expected to exist -----------------------------------------------

def _downloads():
    """Where the checkouts live, from Windows or from WSL.

    The board half of this script needs the ssh keys, which live in WSL; the
    repository half needs the Windows checkouts. Run from WSL, `~/Downloads`
    resolves to the Linux home and every repository silently became "pas de
    checkout ici" — a wrong answer that at least announced itself as unmeasured
    rather than as fine.
    """
    for candidate in (os.environ.get("ESTATE_ROOT"),
                      os.path.expanduser("~/Downloads"),
                      "/mnt/c/Users/kil/Downloads"):
        if candidate and os.path.isdir(candidate):
            return candidate
    return os.path.expanduser("~/Downloads")


DOWNLOADS = _downloads()

REPOS = [
    "kick-xp-farmer",
    "autonomy-log",
    "claw-display",
    "disk-triage",
    "kickbus",
    "kick-core",
    "02 - Projects/inventory-monitor",
    "02 - Projects/cs2-skin-radar",
    "02 - Projects/bloque_pub",
    "filefs/mnt/user-data/outputs/csrust-monitor-go",
]

# name -> (host, ssh key, unit checks)
BOARDS = {
    "claw": ("192.168.1.59", "claw_key"),
    "nano": ("192.168.1.46", "nano_key"),
}

SECRETSCAN = os.path.join(DOWNLOADS, "disk-triage", "secretscan.py")

OK, FAIL, UNKNOWN = "ok", "FAIL", "?"


class Result:
    def __init__(self):
        self.rows = []
        self.failed = 0
        self.unknown = 0

    def add(self, status, name, detail=""):
        self.rows.append((status, name, detail))
        if status == FAIL:
            self.failed += 1
        elif status == UNKNOWN:
            self.unknown += 1

    def report(self):
        width = max((len(n) for _, n, _ in self.rows), default=10)
        for status, name, detail in self.rows:
            mark = {OK: "  ok  ", FAIL: " FAIL ", UNKNOWN: "  ??  "}[status]
            print(f"{mark} {name:<{width}}  {detail}")
        print(f"\n{len(self.rows)} controles, {self.failed} en echec, "
              f"{self.unknown} non mesurables")
        return 1 if self.failed else (2 if self.unknown else 0)


def run(args, cwd=None, timeout=60, merge_stderr=True):
    """Returns (returncode, output) or (None, reason) if it could not run.

    Merging stderr into stdout is convenient when the output is read by a human
    and poison when it is counted. `git diff --name-only` under a forced
    line-ending setting prints one conversion warning per file, on stderr, and
    the merged stream turned twenty-three warnings into twenty-three filenames.
    Anything that counts lines passes merge_stderr=False.
    """
    try:
        p = subprocess.run(args, cwd=cwd, capture_output=True, text=True,
                           timeout=timeout)
    except (OSError, subprocess.SubprocessError) as err:
        return None, str(err)
    out = p.stdout or ""
    if merge_stderr:
        out += p.stderr or ""
    return p.returncode, out


# --- repository checks -------------------------------------------------------

def check_repos(res):
    for rel in REPOS:
        path = os.path.join(DOWNLOADS, rel)
        name = os.path.basename(rel)
        if not os.path.isdir(os.path.join(path, ".git")):
            res.add(UNKNOWN, name, "pas de checkout ici")
            continue

        code, out = run(["git", "rev-parse", "--short", "HEAD"], cwd=path)
        if code is None or code != 0:
            res.add(UNKNOWN, name, f"git illisible: {out.strip()[:60]}")
            continue
        head = out.strip()

        # Non commite (hors fichiers non suivis, qui sont souvent du bruit).
        #
        # Compare le contenu a HEAD, pas l'etat que `status` deduit du cache :
        # et surtout, force le reglage de fin de ligne avec lequel le depot a
        # ete checkoute. Les checkouts vivent sur un disque Windows avec
        # core.autocrlf=true, donc CRLF sur disque et LF dans les blobs. Un git
        # lance depuis WSL n'herite pas de ce reglage, hache les octets bruts,
        # et declare modifie chaque fichier de chaque depot : 102 fichiers
        # annonces comme "du travail qui disparait si le disque disparait",
        # pour un seul reel. Un chiffre qui depend du shell qui pose la
        # question ne mesure pas le depot, et noie la vraie modification parmi
        # cent fausses. Avec le reglage force, les deux git donnent le meme
        # compte, y compris le 1 authentique.
        code, out = run(["git", "-c", "core.autocrlf=true", "diff",
                         "--name-only", "HEAD"], cwd=path, merge_stderr=False)
        dirty = len([l for l in out.splitlines() if l.strip()]) if code == 0 else None

        # Ecart avec le distant, seulement si une branche amont existe.
        code, upstream = run(["git", "rev-parse", "--short", "@{u}"], cwd=path)
        sync = "sans amont"
        if code == 0:
            sync = "sync" if upstream.strip() == head else f"DIVERGE({head}/{upstream.strip()})"

        detail = f"{head} {sync}"
        if dirty is None:
            res.add(UNKNOWN, name, detail + " non-commite=?")
        elif dirty:
            # Du travail non commite n'est pas une panne, mais c'est ce qui
            # disparait si le disque disparait : on le dit sans crier.
            res.add(OK, name, detail + f" {dirty} fichier(s) non commite(s)")
        elif "DIVERGE" in sync:
            res.add(FAIL, name, detail)
        else:
            res.add(OK, name, detail)


def check_secrets(res):
    if not os.path.exists(SECRETSCAN):
        res.add(UNKNOWN, "secrets", "secretscan.py introuvable")
        return
    for rel in REPOS:
        path = os.path.join(DOWNLOADS, rel)
        if not os.path.isdir(os.path.join(path, ".git")):
            continue
        code, out = run([sys.executable, SECRETSCAN, path, "--head-only"], timeout=180)
        name = "secrets/" + os.path.basename(rel)
        if code is None:
            res.add(UNKNOWN, name, out[:60])
        elif code == 0:
            res.add(OK, name, "aucun")
        elif code == 1:
            res.add(FAIL, name, "identifiant dans le HEAD")
        else:
            # Exit 2 = n'a pas pu scanner. Surtout ne pas lire ca comme propre.
            res.add(UNKNOWN, name, f"scan impossible (code {code})")


# --- board checks ------------------------------------------------------------

def classify_cookie(out):
    """(status, detail) for the Steam session, from the scanner's dry run.

    Written as its own function so it can be interrogated directly. The first
    version of this lived inline and ended with `else: OK, "valide"`, meaning
    any output it did not recognise was reported as a healthy session: a binary
    that crashed, a flag that disappeared, a wording change, an empty pipe. The
    failure it exists to catch is a session that expired quietly and let eleven
    days of reports go out wrong. A check for a silent failure must not have a
    silent success.

    Recognised is fine, unrecognised is unmeasured, and the two never share a
    return value.
    """
    if "EXPIRED" in out:
        return FAIL, "expire, aucune mesure possible"
    if "expires in about" in out:
        left = out.split("expires in about", 1)[1].split("—")[0].strip()
        return OK, f"{left} restantes"
    return UNKNOWN, f"sortie non reconnue: {out.strip()[:50] or '(vide)'}"


def selftest():
    """Prove the classifier separates the cases. Run with --selftest."""
    cases = [
        ("cookie expire",      "steamLoginSecure EXPIRED — re-export needed", FAIL),
        ("cookie valide",      "session expires in about 19 h — 723 items",   OK),
        ("sortie vide",        "",                                            UNKNOWN),
        ("binaire plante",     "panic: runtime error: index out of range",    UNKNOWN),
        ("flag disparu",       "Usage: csrust-monitor [--scan] [--weekly]",   UNKNOWN),
        ("libelle change",     "session valid for 19 more hours",             UNKNOWN),
    ]
    bad = 0
    for label, out, want in cases:
        got, detail = classify_cookie(out)
        mark = "  ok  " if got == want else " FAIL "
        if got != want:
            bad += 1
        print(f"{mark} {label:<16} attendu {want:<4} obtenu {got:<4} {detail[:40]}")

    # E32: chaque cle declaree doit etre localisable quelque part. Une cle
    # introuvable a fait passer une carte pour injoignable pendant des mois.
    for board, (_host, key) in BOARDS.items():
        kind, path = _key_path(key)
        ok = kind is not None
        bad += 0 if ok else 1
        print(f"{'  ok  ' if ok else ' FAIL '} cle {board:<12} "
              f"{kind or 'INTROUVABLE'} {path}")

    # Et une cle qui n'existe nulle part doit se dire introuvable, pas se taire.
    kind, why = _key_path("cle_qui_n_existe_pas")
    ok = kind is None and "introuvable" in why
    bad += 0 if ok else 1
    print(f"{'  ok  ' if ok else ' FAIL '} cle absente     {kind} {why}")

    print(f"\n{len(cases) + len(BOARDS) + 1} cas, {bad} en echec")
    return 1 if bad else 0

SSH_OPTS = ["-o", "ConnectTimeout=15", "-o", "BatchMode=yes"]


def _key_path(key):
    """Where this key actually is, or (None, why).

    The two boards were never symmetric and the script assumed they were.
    `nano_key` exists in the Windows profile, `claw_key` only in the WSL one,
    so `~/.ssh/<key>` found the first and missed the second. The docstring at
    the top of this file already said the keys "live in WSL"; the code read
    them from the Windows home anyway, and the claw reported `?` on every run
    since the tool was written. Nobody read the `?`.

    Returns ("native", path) when a plain ssh can use it, ("wsl", path) when
    only the WSL filesystem has it, or (None, reason).
    """
    local = os.path.expanduser(f"~/.ssh/{key}")
    if os.path.exists(local):
        return "native", local
    wsl_path = f"/home/kil/.ssh/{key}"
    if os.path.exists(wsl_path):          # already running inside WSL
        return "native", wsl_path
    code, _ = run(["wsl", "test", "-f", wsl_path], timeout=20)
    if code == 0:
        return "wsl", wsl_path
    return None, f"cle {key} introuvable (ni Windows ni WSL)"


def ssh(board, remote_cmd, timeout=45):
    host, key = BOARDS[board]
    kind, path = _key_path(key)
    if kind is None:
        # Une cle absente n'est pas une carte injoignable. Les confondre, c'est
        # rapporter une panne materielle pour un probleme de poste de travail,
        # et c'est exactement la collapse que ce depot documente.
        return None, path
    argv = ["ssh"] if kind == "native" else ["wsl", "ssh"]
    return run(argv + SSH_OPTS + ["-i", path, f"root@{host}", remote_cmd],
               timeout=timeout)


def check_boards(res):
    for board in BOARDS:
        code, out = ssh(board, "hostname && date +%s")
        if code is None:
            # La sonde n'a pas eu lieu (cle absente, ssh absent). Ce n'est pas
            # un diagnostic sur la carte.
            res.add(UNKNOWN, board, f"non sonde: {out.strip()[:60]}")
            continue
        if code != 0:
            res.add(UNKNOWN, board, f"injoignable: {out.strip()[:60]}")
            continue
        # Un ssh qui rend 0 sans rien ecrire n'a pas prouve que la carte
        # repond : indexer a l'aveugle levait une exception et emportait tout
        # le rapport, y compris les controles deja passes.
        lines = out.split()
        if not lines:
            res.add(UNKNOWN, board, "code 0 mais sortie vide")
        else:
            res.add(OK, board, f"{lines[0]} joignable")

    # clawd doit tourner en UN exemplaire et avoir gagne de l'XP recemment.
    code, out = ssh("claw", "ps | grep -c '[c]lawd-riscv64'; "
                            "cat /tmp/clawdisp.state 2>/dev/null; date +%s")
    if code is None or code != 0:
        res.add(UNKNOWN, "clawd", "non mesurable")
    else:
        parts = out.split()
        n = int(parts[0]) if parts and parts[0].isdigit() else -1
        if n == 1:
            res.add(OK, "clawd", "1 instance")
        elif n == 0:
            res.add(FAIL, "clawd", "arrete")
        else:
            res.add(FAIL, "clawd", f"{n} instances (doublon)")

        # Battement de l'ecran : derniere frame reellement dessinee.
        if len(parts) >= 4 and parts[1].isdigit() and parts[-1].isdigit():
            age = int(parts[-1]) - int(parts[1])
            status = OK if age < 120 else FAIL
            res.add(status, "ecran", f"derniere frame il y a {age}s")
        else:
            res.add(UNKNOWN, "ecran", "pas de battement lisible")

    # csrust : le binaire deploye doit correspondre au depot.
    code, out = ssh("nano", "/root/csrust-monitor/csrust-monitor-riscv64 --version 2>&1")
    repo = os.path.join(DOWNLOADS, "filefs/mnt/user-data/outputs/csrust-monitor-go")
    # Le dernier commit qui a touche du Go, pas le HEAD : un commit de doc ou de
    # script deplace le HEAD sans changer le binaire, et comparer au HEAD
    # signalerait un ecart a chaque fois. Assez precis pour attraper un binaire
    # perime, ce qui est le defaut reel a couvrir : un correctif a dormi onze
    # jours pendant qu'une version d'avant tournait.
    rc, head = run(["git", "log", "-1", "--format=%h", "--",
                    "*.go", "go.mod", "go.sum"], cwd=repo)
    if code is None or code != 0 or rc != 0 or not out.strip():
        res.add(UNKNOWN, "csrust", "version non mesurable")
    else:
        deployed = out.strip().split()[-1]
        if deployed == head.strip():
            res.add(OK, "csrust", f"{deployed} = depot")
        else:
            res.add(FAIL, "csrust", f"deploye {deployed}, depot {head.strip()}")

    # Le cookie Steam est la panne recurrente : la duree de vie est d'un jour.
    code, out = ssh("nano", "cd /root/csrust-monitor && "
                            "./csrust-monitor-riscv64 --scan --dry-run 2>&1 | head -4")
    if code is None or code != 0:
        res.add(UNKNOWN, "cookie steam", "non mesurable")
    else:
        status, detail = classify_cookie(out)
        res.add(status, "cookie steam", detail)


# Surchargeable pour pouvoir muter le manifeste et verifier que le controle
# passe au rouge. E21 etait un test de mutation qui ne mutait rien.
BACKUP_SCRIPT = os.environ.get(
    "NANO_BACKUP_SCRIPT",
    os.path.join(os.path.expanduser("~"), "nano-backups", "bin",
                 "nano-backup.sh"))

# Rebati par un script deja sauve, donc hors perimetre. Chaque exclusion porte
# la raison qui la justifie : une liste d'exceptions sans motif redevient un
# manifeste qui derive.
REGENERATED = {
    "/etc/hosts.blocklist":  "regenere par update-blocklist.sh",
    "/etc/hosts.utiq":       "regenere par update-utiq.sh",
    "/etc/resolv.conf":      "ecrit par le DHCP au boot",
}


def check_backup_scope(res):
    """Does the backup manifest still describe the machine?

    D2 was a backup that ran daily, encrypted, pushed, size-stable and passing
    its restore test, over two thirds of a machine, because the manifest had
    been written months earlier. It was fixed by hand. It then drifted twice
    more in three days, both times the same shape: an init script is added to
    the manifest and the config it sources is not, so the service restores and
    cannot start.

    The remote side skips a missing path in silence, so a manifest that has
    stopped describing the machine prints exactly like one that still does.
    Nothing downstream can see this, which is why the comparison is made here
    against the board rather than against the archive.

    Only `/etc` paths referenced by covered scripts are reported. Binaries and
    generated blocklists live in their own repositories and are reproducible;
    flagging them would put four permanent false alarms in a short list, and a
    list that cries wolf gets skimmed whole.
    """
    if not os.path.exists(BACKUP_SCRIPT):
        res.add(UNKNOWN, "backup scope", "nano-backup.sh introuvable")
        return
    with open(BACKUP_SCRIPT, encoding="utf-8", errors="replace") as fh:
        text = fh.read()
    _, _, rest = text.partition("MANIFEST='")
    body, sep, _ = rest.partition("'")
    if not sep:
        res.add(UNKNOWN, "backup scope", "MANIFEST illisible dans le script")
        return
    manifest = [l.strip() for l in body.splitlines() if l.strip()]
    if not manifest:
        # Un manifeste vide n'est pas un manifeste sain. C'est la meme collapse
        # que partout ailleurs dans ce depot : vide et illisible se ressemblent.
        res.add(UNKNOWN, "backup scope", "MANIFEST vide")
        return

    scripts = [p for p in manifest
               if p.startswith(("/etc/init.d/", "/usr/local/bin/"))]
    # Une seule session ssh : la sonde fait partie du systeme, et la carte a
    # 128 Mo. On rapatrie deux listes courtes et on decide ici.
    remote = ("for p in " + " ".join(manifest) + "; do [ -e \"$p\" ] || "
              "echo \"DEAD $p\"; done; "
              "for f in " + " ".join(scripts) + "; do [ -f \"$f\" ] && "
              "grep -oE '/etc/[A-Za-z0-9._/-]+' \"$f\"; done | sort -u | "
              # Un chemin cite mais absent n'est pas un oubli de sauvegarde.
              "while read p; do [ -f \"$p\" ] && echo \"REF $p\"; done")
    code, out = ssh("nano", remote)
    if code is None or code != 0:
        res.add(UNKNOWN, "backup scope", f"non sonde: {out.strip()[:50]}")
        return

    covered = set(manifest)
    dead, uncovered = [], []
    for line in out.splitlines():
        line = line.strip()
        if line.startswith("DEAD "):
            dead.append(line[5:])
        elif line.startswith("REF "):
            line = line[4:]
            if line in covered or line in REGENERATED:
                continue
            # Un repertoire cite (/etc/crontabs) n'est pas un fichier oublie.
            if not any(c.startswith(line + "/") for c in covered):
                uncovered.append(line)

    if dead:
        res.add(FAIL, "backup scope", f"{len(dead)} entrees mortes: "
                                      f"{', '.join(dead[:3])}")
    elif uncovered:
        res.add(FAIL, "backup scope", f"{len(uncovered)} config(s) citee(s) "
                                      f"non sauvee(s): {', '.join(uncovered[:3])}")
    else:
        res.add(OK, "backup scope", f"{len(manifest)} entrees, toutes vivantes "
                                    f"et leurs configs couvertes")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--repos", action="store_true")
    ap.add_argument("--boards", action="store_true")
    ap.add_argument("--json", action="store_true", help="sortie machine")
    ap.add_argument("--selftest", action="store_true",
                    help="verifie que les controles distinguent leurs cas")
    args = ap.parse_args()
    if args.selftest:
        return selftest()
    everything = not (args.repos or args.boards)

    res = Result()
    if everything or args.repos:
        check_repos(res)
        check_secrets(res)
    if everything or args.boards:
        check_boards(res)
        check_backup_scope(res)

    if args.json:
        print(json.dumps([{"status": s, "name": n, "detail": d} for s, n, d in res.rows],
                         ensure_ascii=False, indent=2))
        return 1 if res.failed else (2 if res.unknown else 0)
    return res.report()


if __name__ == "__main__":
    sys.exit(main())
