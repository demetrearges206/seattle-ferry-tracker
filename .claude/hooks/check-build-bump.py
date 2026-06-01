#!/usr/bin/env python3
"""
PreToolUse(Bash) guard: block a `git commit` that stages ferry.html without
bumping `const BUILD`. Project rule (CLAUDE.md): bump BUILD on every ferry.html
change. Exit 2 = block + feed the message back to the agent so it can fix & retry.

No-ops fast for any Bash command that isn't a git commit, and for commits that
don't touch ferry.html.
"""
import json
import subprocess
import sys


def sh(args):
    return subprocess.run(args, capture_output=True, text=True).stdout


def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        return 0  # can't parse → don't block

    cmd = (data.get("tool_input") or {}).get("command", "")
    if "git commit" not in cmd:
        return 0

    staged = sh(["git", "diff", "--cached", "--name-only"]).split()
    if "ferry.html" not in staged:
        return 0

    diff = sh(["git", "diff", "--cached", "--", "ferry.html"])
    bumped = any(
        line.startswith("+") and "const BUILD" in line
        for line in diff.splitlines()
    )
    if bumped:
        return 0

    print(
        "BUILD-bump guard: ferry.html is staged but `const BUILD` was not changed "
        "in this commit.\nProject rule: bump BUILD (e.g. r73 → r74) on every "
        "ferry.html change.\nBump it and re-stage, or unstage ferry.html if this "
        "change is deliberately un-bumped.",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    sys.exit(main())
