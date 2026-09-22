# Vendored from ha-integration-standards 0.1.2. Do not edit:
# `ha-standards sync` rewrites this file, and `run.py verify` fails the
# commit when it has been changed by hand.

"""What a project may say about itself, and what it may not.

Everything here has a default that works without configuration. A project
only writes a key down when it genuinely differs - and then it says so in
one place, pyproject.toml, next to the rest of its tooling:

    [tool.ha_standards]
    overall_coverage = 95
    derived_translation_keys = ["binary_sensor:valve_open"]
    unenforceable = ["discovery"]
    brand_color = "#0A7EE8"

    [tool.ha_standards.coverage]
    "config_flow.py" = 100
    "coordinator.py" = 95

    [tool.ha_standards.readme]
    docs-supported-devices = "Supported devices"
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path

# Rules whose verdict needs a human: documentation prose, process questions,
# the quality of a dependency. Claiming them is fine; proving them is not.
# Keeping the list here rather than in each project is the point of this
# package - it grows as checks are written, and every project gets the growth.
NOT_CHECKABLE = frozenset(
    {
        "appropriate-polling",
        "async-dependency",
        "docs-actions",
        "docs-conditions",
        "docs-triggers",
        "entity-category",
        "entity-device-class",
        "entity-event-setup",
        "inject-websession",
        "log-when-unavailable",
        "repair-issues",
        "stale-devices",
        "unique-config-entry",
        # Coverage has a gate of its own.
        "config-flow-test-coverage",
        "test-coverage",
    }
)

# Each documentation rule maps to a heading the README has to carry. The
# wording of a section is nobody's business here; its absence is. Matching is
# case-insensitive and on the heading text, so "## Supported devices" and
# "### Supported Devices" both count.
README_SECTIONS = {
    "docs-high-level-description": None,  # the title; handled separately
    "docs-installation-instructions": "Installation",
    "docs-removal-instructions": "Removal",
    "docs-configuration-parameters": "Configuration",
    "docs-installation-parameters": "Setup",
    "docs-supported-devices": "Supported devices",
    "docs-supported-functions": "What you get",
    "docs-data-update": "How data is fetched",
    "docs-known-limitations": "Notes and limitations",
    "docs-troubleshooting": "Troubleshooting",
    "docs-examples": "Examples",
    "docs-use-cases": "Use cases",
}

DEFAULT_COVERAGE = {"config_flow.py": 100.0}
DEFAULT_OVERALL = 95.0

# The house colour every brand icon is built on. It is what makes a set of
# integrations read as coming from one author, which is the whole reason the
# gate looks at pixels at all. A project that wants a different ground says so
# in pyproject.toml; an empty string turns the colour check off and leaves the
# size and shape checks standing.
DEFAULT_BRAND_COLOR = "#0A7EE8"


@dataclass(frozen=True)
class Settings:
    """The project's own adjustments, defaults already applied."""

    overall_coverage: float = DEFAULT_OVERALL
    coverage: dict[str, float] = field(default_factory=dict)
    readme: dict[str, str] = field(default_factory=dict)
    derived_translation_keys: dict[str, set[str]] = field(default_factory=dict)
    unenforceable: frozenset[str] = frozenset()
    coverage_report: str = ".artefakte/coverage.json"
    brand_color: str = DEFAULT_BRAND_COLOR

    def section_for(self, rule: str) -> str | None:
        """Return the README heading a documentation rule needs."""
        if rule in self.readme:
            return self.readme[rule]
        return README_SECTIONS.get(rule)

    def needs_a_human(self, rule: str) -> bool:
        """Return True when no check can decide this rule for this project."""
        return rule in NOT_CHECKABLE or rule in self.unenforceable


def load(root: Path) -> Settings:
    """Read [tool.ha_standards] from the project, with defaults applied."""
    pyproject = root / "pyproject.toml"
    raw: dict = {}
    if pyproject.exists():
        with pyproject.open("rb") as handle:
            raw = tomllib.load(handle).get("tool", {}).get("ha_standards", {})

    coverage = dict(DEFAULT_COVERAGE)
    coverage.update({k: float(v) for k, v in (raw.get("coverage") or {}).items()})

    derived: dict[str, set[str]] = {}
    for entry in raw.get("derived_translation_keys") or []:
        platform, _, key = str(entry).partition(":")
        if key:
            derived.setdefault(platform, set()).add(key)

    return Settings(
        overall_coverage=float(raw.get("overall_coverage", DEFAULT_OVERALL)),
        coverage=coverage,
        readme={str(k): str(v) for k, v in (raw.get("readme") or {}).items()},
        derived_translation_keys=derived,
        unenforceable=frozenset(raw.get("unenforceable") or ()),
        coverage_report=str(raw.get("coverage_report", ".artefakte/coverage.json")),
        brand_color=str(raw.get("brand_color", DEFAULT_BRAND_COLOR)),
    )
