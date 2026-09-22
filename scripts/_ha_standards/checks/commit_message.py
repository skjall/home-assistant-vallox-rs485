# Vendored from ha-integration-standards 0.1.2. Do not edit:
# `ha-standards sync` rewrites this file, and `run.py verify` fails the
# commit when it has been changed by hand.

"""Reject a commit message that a release tool or a reader would choke on.

Two things go wrong repeatedly and both end up published: the subject misses
its Conventional Commits type, so the change cannot be placed in the
changelog, and the message is written in German, while everything else in the
repository - code, comments, docs, the changelog on GitHub and PyPI - is
English.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

TYPES = (
    "build",
    "chore",
    "ci",
    "deps",
    "docs",
    "feat",
    "fix",
    "perf",
    "refactor",
    "revert",
    "style",
    "test",
)
SUBJECT = re.compile(rf"^(?:{'|'.join(TYPES)})(?:\([\w .,/-]+\))?!?: .+")

# Words that are German and are not also English. Short enough to stay a
# tripwire rather than a language detector.
GERMAN = re.compile(
    r"\b(?:der|die|das|und|nicht|nur|wird|wurde|werden|sind|kann|beim|vom|"
    r"eine|einen|einem|einer|dass|weil|damit|statt|ohne|noch|schon|mehr|"
    r"sich|auch|aber|wenn|dann|jetzt|immer|nie|hier|dort|jede|jeden|jedes|"
    r"macht|machen|setzt|setzen|liegt|liegen|steht|stehen|gibt|geben)\b",
    re.IGNORECASE,
)

# Lines a tool appends below the message. They are not the author's prose and
# are not judged - but only below the subject: "fix: ..." has the shape of a
# trailer too, and dropping it would leave nothing to check.
TRAILER = re.compile(
    r"^(?:Co-authored-by|Signed-off-by|Reviewed-by|Acked-by|Tested-by|"
    r"Reported-by|Suggested-by|Cc|Refs|Closes|Fixes|Claude-Session|"
    r"BREAKING[- ]CHANGE):",
    re.IGNORECASE,
)


def main(argv: list[str] | None = None) -> int:
    """Check the message in the file named on the command line."""
    if not argv:
        print("  commit message: no message file given", file=sys.stderr)
        return 1

    text = Path(argv[0]).read_text(encoding="utf-8")
    lines = [line for line in text.splitlines() if not line.lstrip().startswith("#")]
    while lines and not lines[0].strip():
        lines.pop(0)
    if not lines:
        return 0
    subject = lines[0]
    # The subject is always judged; below it, trailers are left out.
    body = "\n".join(
        [subject] + [line for line in lines[1:] if not TRAILER.match(line.strip())]
    ).strip()

    problems = []
    if not SUBJECT.match(subject):
        problems.append(
            f"the subject needs a Conventional Commits type "
            f"({', '.join(TYPES)}), e.g. 'fix: {subject[:40]}'"
        )
    if found := sorted({m.group(0).lower() for m in GERMAN.finditer(body)}):
        problems.append(
            "the message looks German ("
            + ", ".join(found[:6])
            + "); commits, like everything else here, are written in English"
        )

    for problem in problems:
        print(f"  commit message: {problem}", file=sys.stderr)
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
