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


def run(args, cwd=None, timeout=60):
    """Returns (returncode, stdout+stderr) or (None, reason) if it could not run."""
    try:
        p = subprocess.run(args, cwd=cwd, capture_output=True, text=True,
                           timeout=timeout)
    except (OSError, subprocess.SubprocessError) as err:
        return None, str(err)
    return p.returncode, (p.stdout or "") + (p.stderr or "")


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
        code, out = run(["git", "status", "--porcelain"], cwd=path)
        dirty = len([l for l in out.splitlines() if l and not l.startswith("??")]) if code == 0 else None

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

def ssh(board, remote_cmd, timeout=45):
    host, key = BOARDS[board]
    return run(["ssh", "-o", "ConnectTimeout=15", "-o", "BatchMode=yes",
                "-i", os.path.expanduser(f"~/.ssh/{key}"), f"root@{host}",
                remote_cmd], timeout=timeout)


def check_boards(res):
    for board in BOARDS:
        code, out = ssh(board, "hostname && date +%s")
        if code is None or code != 0:
            res.add(UNKNOWN, board, f"injoignable: {out.strip()[:60]}")
            continue
        lines = out.split()
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
    if code is None or code != 0 or rc != 0:
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
    elif "EXPIRED" in out:
        res.add(FAIL, "cookie steam", "expire, aucune mesure possible")
    elif "expires in about" in out:
        res.add(OK, "cookie steam", out.split("expires in about", 1)[1].split("—")[0].strip() + " restantes")
    else:
        res.add(OK, "cookie steam", "valide")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--repos", action="store_true")
    ap.add_argument("--boards", action="store_true")
    ap.add_argument("--json", action="store_true", help="sortie machine")
    args = ap.parse_args()
    everything = not (args.repos or args.boards)

    res = Result()
    if everything or args.repos:
        check_repos(res)
        check_secrets(res)
    if everything or args.boards:
        check_boards(res)

    if args.json:
        print(json.dumps([{"status": s, "name": n, "detail": d} for s, n, d in res.rows],
                         ensure_ascii=False, indent=2))
        return 1 if res.failed else (2 if res.unknown else 0)
    return res.report()


if __name__ == "__main__":
    sys.exit(main())
