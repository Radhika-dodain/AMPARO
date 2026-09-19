"""
Checks that every version pinned in requirements.txt is a version that really
exists, by comparing each one against what is actually installed here.

    python scripts/check_requirements.py

WHY THIS EXISTS:
A pin was once written as httpx==0.28.2. There is no such release - the real
one is 0.28.1. Nothing local complained, because httpx was already installed
and nobody reinstalled it. The mistake surfaced five minutes into a deploy, as
a wall of red text listing every httpx version ever published, which reads like
a catastrophe and means "you asked for one that is not on that list".

Run this before you push. It takes a second and it needs no network: if a
version is installed on this machine, that version exists.

Run it after a `pip install -U` too. If something was upgraded and the pin was
not, this is what tells you - and that is the honest moment to decide whether
to pin the new version or hold the old one.
"""

from __future__ import annotations

import re
import sys
from importlib import metadata
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent

# name, optional [extras], ==, version
PIN = re.compile(r"^([A-Za-z0-9_.-]+)(?:\[[^\]]+\])?==([A-Za-z0-9.]+)")


def check(path: Path) -> tuple[int, int, int]:
    """Returns (matched, mismatched, unverifiable) for one requirements file."""
    if not path.exists():
        return (0, 0, 0)

    print(f"\n{path.name}")
    ok = bad = unknown = 0

    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue

        found = PIN.match(line)
        if not found:
            print(f"  ?  not a pinned line, skipped: {line}")
            continue

        name, pinned = found.groups()
        try:
            installed = metadata.version(name)
        except metadata.PackageNotFoundError:
            # Not installed here, so this check cannot say anything either way.
            print(f"  ?  {name}=={pinned} - not installed locally, unverified")
            unknown += 1
            continue

        if installed == pinned:
            print(f"  ok {name}=={pinned}")
            ok += 1
        else:
            print(f"  NO {name}=={pinned}  <-- installed here is {installed}")
            bad += 1

    return (ok, bad, unknown)


def main() -> int:
    totals = [0, 0, 0]
    for name in ("requirements.txt", "requirements-dev.txt"):
        for i, value in enumerate(check(BACKEND / name)):
            totals[i] += value

    ok, bad, unknown = totals
    print(f"\n{ok} pins match, {bad} do not, {unknown} could not be checked.")

    if bad:
        print(
            "\nFix the mismatched pins before pushing. A pin that names a"
            "\nversion nobody published fails the deploy, not the build here."
        )
        return 1

    if unknown:
        print(
            "\nThe unchecked ones are not installed on this machine, so this"
            "\nscript cannot vouch for them. Install them, or check by hand."
        )

    print("\nGood to push.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
