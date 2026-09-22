# Vendored from ha-integration-standards 0.2.0. Do not edit:
# `ha-standards sync` rewrites this file, and `run.py verify` fails the
# commit when it has been changed by hand.

"""Hold each module to the coverage its tier demands.

pytest already fails below the overall floor. This adds the per-module floors
that a single number hides: a config flow at 88% still passes a 95% average,
and the Bronze rule asks for all of it.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from .. import config
from ..discovery import NoIntegrationError, find_integration


def main(argv: list[str] | None = None) -> int:
    """Check the coverage report against the floors."""
    start = Path(argv[0]) if argv else Path.cwd()
    try:
        it = find_integration(start)
    except NoIntegrationError as err:
        print(f"  coverage: {err}", file=sys.stderr)
        return 1

    settings = config.load(it.root)
    report = it.root / settings.coverage_report
    if not report.exists():
        print(f"{settings.coverage_report} is missing - run the tests first.")
        return 1

    data = json.loads(report.read_text(encoding="utf-8"))
    files = data["files"]
    problems: list[str] = []
    prefix = it.path.relative_to(it.root).as_posix()

    for name, floor in sorted(settings.coverage.items()):
        # A floor is written as the module name; the report uses full paths.
        path = name if "/" in name else f"{prefix}/{name}"
        if not (it.root / path).exists():
            # A floor for a module this integration does not have is a stale
            # setting, not a failure of the code.
            print(f"  note: no {path} in this integration - floor ignored")
            continue
        entry = files.get(path)
        if entry is None:
            problems.append(f"{path}: not in the report at all - was it renamed?")
            continue
        actual = entry["summary"]["percent_covered"]
        if actual + 1e-9 < floor:
            missing = entry["missing_lines"]
            problems.append(
                f"{path}: {actual:.1f}% < {floor:.0f}% "
                f"(uncovered lines: {', '.join(map(str, missing[:12]))})"
            )

    total = data["totals"]["percent_covered"]
    if total + 1e-9 < settings.overall_coverage:
        problems.append(f"overall: {total:.1f}% < {settings.overall_coverage:.0f}%")

    if problems:
        print("Coverage is below what the claimed tier requires\n")
        for line in problems:
            print(f"  FAIL  {line}")
        return 1

    print(f"Coverage: {total:.1f}% overall, every module above its floor.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
