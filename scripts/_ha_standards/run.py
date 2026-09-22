# Vendored from ha-integration-standards 0.3.0. Do not edit:
# `ha-standards sync` rewrites this file, and `run.py verify` fails the
# commit when it has been changed by hand.

#!/usr/bin/env python3
"""Run the vendored gates.

This is the only entry point a project needs. It works from a checkout with
nothing installed beyond PyYAML, which is what lets the same command run in a
pre-commit hook, in CI, and by hand.
"""

from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from _ha_standards import __version__  # noqa: E402
from _ha_standards.checks import commit_message, coverage, quality_scale  # noqa: E402

USAGE = """usage: run.py <gate> [arguments]

  quality-scale    the code holds what quality_scale.yaml claims
  coverage         the per-module coverage floors the claimed tier requires
  commit-message   Conventional Commits, in English
  tests            the suite, in Docker, against the targeted Home Assistant
  types            mypy --strict, in the same container
  verify           the vendored files are the ones that were synced
  version          which release these checks came from
"""


def _verify() -> int:
    """Check the vendored files against their recorded hashes."""
    import hashlib

    manifest = HERE / "MANIFEST.sha256"
    if not manifest.exists():
        print("  MANIFEST.sha256 is missing - run 'ha-standards sync'.")
        return 1
    problems = []
    for line in manifest.read_text(encoding="utf-8").splitlines():
        if line.startswith("#") or not line.strip():
            continue
        expected, _, name = line.partition("  ")
        path = HERE / name
        if not path.exists():
            problems.append(f"{name}: missing")
        elif hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            problems.append(f"{name}: edited by hand")
    if problems:
        print(f"The vendored gates ({__version__}) have been changed\n")
        for problem in problems:
            print(f"  FAIL  {problem}")
        print(
            "\nThese files are written by ha-integration-standards. Change the\n"
            "rule there and run 'ha-standards sync', or restore them with it."
        )
        return 1
    print(f"Vendored gates: ha-integration-standards {__version__}, unmodified.")
    return 0


def main(argv: list[str]) -> int:
    """Dispatch one gate."""
    if not argv or argv[0] in ("-h", "--help"):
        print(USAGE)
        return 0 if argv else 1

    gate, rest = argv[0], argv[1:]
    if gate == "quality-scale":
        return quality_scale.main(rest)
    if gate == "coverage":
        return coverage.main(rest)
    if gate == "commit-message":
        return commit_message.main(rest)
    if gate == "verify":
        return _verify()
    if gate == "version":
        print(__version__)
        return 0
    if gate in ("tests", "types"):
        from _ha_standards import runner

        return runner.tests(rest) if gate == "tests" else runner.types(rest)

    print(f"unknown gate '{gate}'\n\n{USAGE}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
