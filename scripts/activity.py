#!/usr/bin/env python3
"""activity.py — Git commit activity monitor across cloned AVM module repos.

Reads .config/modules.yaml, iterates cloned repos, and reports recent commit
activity ranked by commit count. Modules with zero commits in the window are
flagged as [stagnant].

Usage:
    python3 scripts/activity.py [options]
    ./avm.sh activity [options]    # operator alias

Options:
    --since PERIOD   Look-back window (default: 30d). Examples: 7d, 30d, 90d, 1y.
                     Passed verbatim to git --since, so any git date expression works.
    --top N          Show only the top N most active modules (0 = all, default: 0).
    --domains LIST   Comma-separated domain slugs (or 'all').
    --types LIST     Comma-separated module types: res, ptn, utl (or 'all').
    --modules LIST   Comma-separated module names (short form: avm-res-*).
    --stagnant-only  Only show modules with 0 commits in the window.
    --no-stagnant    Exclude modules with 0 commits.
    --output FILE    Write output to FILE instead of stdout.
"""

import os
import re
import subprocess
import sys
from datetime import datetime, timezone

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
SCRIPT_DIR  = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT   = os.path.dirname(SCRIPT_DIR)
MODULES_FILE = os.path.join(REPO_ROOT, ".config", "modules.yaml")

# ---------------------------------------------------------------------------
# ANSI helpers
# ---------------------------------------------------------------------------
_NO_COLOR = not sys.stdout.isatty()


def _ansi(code: str, text: str) -> str:
    return text if _NO_COLOR else f"\033[{code}m{text}\033[0m"


def _ok(s: str)   -> str: return _ansi("32", s)   # green
def _warn(s: str) -> str: return _ansi("33", s)   # yellow
def _err(s: str)  -> str: return _ansi("31", s)   # red
def _dim(s: str)  -> str: return _ansi("2",  s)   # dim/grey
def _bold(s: str) -> str: return _ansi("1",  s)   # bold


SEP = "─" * 70


# ---------------------------------------------------------------------------
# .config/modules.yaml loader (mirrors manage_repos.py pattern)
# ---------------------------------------------------------------------------

def _field(line: str, key: str) -> str:
    idx = line.find(f"{key}:")
    if idx == -1:
        return ""
    val = line[idx + len(key) + 1:].strip().strip('"')
    return val


def load_modules(
    filter_domains: list[str] | None = None,
    filter_types:   list[str] | None = None,
    filter_modules: list[str] | None = None,
) -> list[dict]:
    """Parse .config/modules.yaml and return matching module dicts."""
    if not os.path.isfile(MODULES_FILE):
        print("Error: .config/modules.yaml not found.\nRun './avm.sh setup --domains all' first.", file=sys.stderr)
        sys.exit(1)

    modules: list[dict] = []
    cur: dict = {}

    def _flush(c: dict) -> None:
        if not c.get("name") or not c.get("url"):
            return
        if filter_domains and c.get("domain") not in filter_domains:
            return
        if filter_types and c.get("type") not in filter_types:
            return
        short = c["name"].removeprefix("terraform-azurerm-").removeprefix("terraform-azure-").removeprefix("terraform-azapi-")
        if filter_modules and short not in filter_modules and c["name"] not in filter_modules:
            return
        modules.append(dict(c))

    with open(MODULES_FILE, encoding="utf-8") as f:
        for raw in f:
            line = raw.rstrip("\r\n")
            stripped = line.lstrip()
            if not stripped or stripped.startswith("#"):
                continue
            if "- name:" in line:
                _flush(cur)
                cur = {"name": _field(line, "name"), "branch": "main",
                       "domain": "", "type": "", "url": ""}
            elif cur and "domain:" in line and "name:" not in line:
                cur["domain"] = _field(line, "domain")
            elif cur and "type:" in line:
                cur["type"] = _field(line, "type")
            elif cur and "url:" in line:
                cur["url"] = _field(line, "url")
            elif cur and "branch:" in line:
                cur["branch"] = _field(line, "branch")

    _flush(cur)
    return modules


# ---------------------------------------------------------------------------
# Git helpers
# ---------------------------------------------------------------------------

def repo_dir(mod: dict) -> str:
    return os.path.join(REPO_ROOT, mod["name"])


def is_cloned(mod: dict) -> bool:
    return os.path.isdir(os.path.join(repo_dir(mod), ".git"))


def _since_git_arg(since: str) -> str:
    """Convert shorthand like '30d' / '1y' to git --since-compatible string.

    Passes through anything that doesn't match the shorthand patterns so users
    can pass git-native expressions like '2 weeks ago' or '2026-01-01'.
    """
    m = re.fullmatch(r"(\d+)(d|w|m|y)", since)
    if not m:
        return since  # pass through as-is
    n, unit = int(m.group(1)), m.group(2)
    mapping = {"d": "days", "w": "weeks", "m": "months", "y": "years"}
    return f"{n} {mapping[unit]} ago"


def _count_commits(mod: dict, since_git: str) -> tuple[int, str]:
    """Return (commit_count, last_commit_date_iso) for a repo in the window.

    Returns (0, '') for uncloned repos or git errors.
    """
    rdir = repo_dir(mod)
    try:
        result = subprocess.run(
            ["git", "-C", rdir, "log", f"--since={since_git}", "--oneline", "--no-walk=unsorted"],
            capture_output=True, text=True, check=False,
        )
        if result.returncode != 0:
            # Fallback: git log without --no-walk which may fail on some versions
            result = subprocess.run(
                ["git", "-C", rdir, "log", f"--since={since_git}", "--oneline"],
                capture_output=True, text=True, check=False,
            )
        count = len([l for l in result.stdout.splitlines() if l.strip()])
    except OSError:
        return 0, ""

    last = ""
    try:
        r2 = subprocess.run(
            ["git", "-C", rdir, "log", "-1", "--format=%ci"],
            capture_output=True, text=True, check=False,
        )
        last = r2.stdout.strip()[:10]  # YYYY-MM-DD
    except OSError:
        pass

    return count, last


# ---------------------------------------------------------------------------
# Main command
# ---------------------------------------------------------------------------

def cmd_activity(
    modules:        list[dict],
    since:          str  = "30d",
    top:            int  = 0,
    stagnant_only:  bool = False,
    no_stagnant:    bool = False,
    output:         str  | None = None,
) -> None:
    since_git = _since_git_arg(since)
    print(f"\nAVM activity  [since: {since_git}, {len(modules)} modules]")
    print(SEP)

    rows: list[tuple[int, str, str, dict]] = []  # (count, last, label, mod)

    not_cloned = 0
    for mod in modules:
        if not is_cloned(mod):
            not_cloned += 1
            continue
        count, last = _count_commits(mod, since_git)
        label = f"{mod['domain']}/{mod['name']}"
        rows.append((count, last, label, mod))

    # Apply stagnant filters
    if stagnant_only:
        rows = [r for r in rows if r[0] == 0]
    elif no_stagnant:
        rows = [r for r in rows if r[0] > 0]

    # Sort by count descending, then alphabetically
    rows.sort(key=lambda r: (-r[0], r[2]))

    if top > 0:
        rows = rows[:top]

    # --- Render ---
    col_name  = max((len(r[2]) for r in rows), default=40) + 2
    col_count = 8
    col_date  = 12

    header = f"  {'Module':<{col_name}} {'Commits':>{col_count}}  {'Last commit':<{col_date}}"
    lines: list[str] = [header, "  " + "─" * (col_name + col_count + col_date + 4)]

    for count, last, label, _mod in rows:
        count_str = str(count)
        stagnant  = count == 0
        if stagnant:
            label_render = _dim(f"{label:<{col_name}}")
            count_render = _err(f"{count_str:>{col_count}}")
            tag          = _dim("  [stagnant]")
        elif count >= 10:
            label_render = _ok(f"{label:<{col_name}}")
            count_render = _ok(f"{count_str:>{col_count}}")
            tag          = ""
        else:
            label_render = f"{label:<{col_name}}"
            count_render = _warn(f"{count_str:>{col_count}}")
            tag          = ""

        date_render = last or "—"
        lines.append(f"  {label_render} {count_render}  {date_render:<{col_date}}{tag}")

    lines.append("")
    total_commits = sum(r[0] for r in rows)
    stagnant_n    = sum(1 for r in rows if r[0] == 0)
    active_n      = len(rows) - stagnant_n
    lines.append(
        f"  {_bold('Summary:')} {len(rows)} modules checked  |  "
        f"{_ok(str(active_n))} active  |  {_err(str(stagnant_n))} stagnant  |  "
        f"{_bold(str(total_commits))} total commits"
    )
    if not_cloned:
        lines.append(f"  {_dim(f'({not_cloned} modules not cloned — skipped)')}")
    lines.append("")

    output_str = "\n".join(lines)

    if output:
        os.makedirs(os.path.dirname(os.path.abspath(output)), exist_ok=True)
        with open(output, "w", encoding="utf-8") as f:
            # Strip ANSI for file output
            clean = re.sub(r"\033\[[0-9;]+m", "", output_str)
            f.write(clean)
        print(f"  Written to: {output}")
    else:
        print(output_str)


# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------

def _parse_args(argv: list[str]) -> dict:
    args: dict = {
        "domains":       None,
        "types":         None,
        "modules":       None,
        "since":         "30d",
        "top":           0,
        "stagnant_only": False,
        "no_stagnant":   False,
        "output":        None,
    }
    i = 0
    while i < len(argv):
        tok = argv[i]
        if tok in ("--help", "-h"):
            print(__doc__)
            sys.exit(0)
        elif tok in ("--domains", "--domain") and i + 1 < len(argv):
            i += 1
            args["domains"] = [d.strip() for d in argv[i].split(",") if d.strip() and d.strip() != "all"]
        elif tok in ("--types", "--type") and i + 1 < len(argv):
            i += 1
            args["types"] = [t.strip() for t in argv[i].split(",") if t.strip() and t.strip() != "all"]
        elif tok in ("--modules", "--module") and i + 1 < len(argv):
            i += 1
            args["modules"] = [m.strip() for m in argv[i].split(",") if m.strip()]
        elif tok == "--since" and i + 1 < len(argv):
            i += 1
            args["since"] = argv[i]
        elif tok == "--top" and i + 1 < len(argv):
            i += 1
            args["top"] = int(argv[i])
        elif tok == "--stagnant-only":
            args["stagnant_only"] = True
        elif tok == "--no-stagnant":
            args["no_stagnant"] = True
        elif tok == "--output" and i + 1 < len(argv):
            i += 1
            args["output"] = argv[i]
        i += 1
    return args


def main(argv: list[str] | None = None) -> None:
    if argv is None:
        argv = sys.argv[1:]
    a = _parse_args(argv)
    modules = load_modules(
        filter_domains = a["domains"] or None,
        filter_types   = a["types"]   or None,
        filter_modules = a["modules"] or None,
    )
    if not modules:
        print("No modules matched the given filters.", file=sys.stderr)
        sys.exit(1)
    cmd_activity(
        modules       = modules,
        since         = a["since"],
        top           = a["top"],
        stagnant_only = a["stagnant_only"],
        no_stagnant   = a["no_stagnant"],
        output        = a["output"],
    )


if __name__ == "__main__":
    main()
