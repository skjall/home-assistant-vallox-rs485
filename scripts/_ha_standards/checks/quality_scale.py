# Vendored from ha-integration-standards 0.2.0. Do not edit:
# `ha-standards sync` rewrites this file, and `run.py verify` fails the
# commit when it has been changed by hand.

"""Hold an integration to the tier it claims.

quality_scale.yaml is a promise. This checks the part of that promise a
machine can check, and fails when the code has drifted below it. Rules that
only a human can judge are named in config.NOT_CHECKABLE, so the gap between
"checked" and "claimed" stays visible instead of implied.

Nothing here knows which integration it is looking at.
"""

from __future__ import annotations

import re
import sys
from collections.abc import Callable
from pathlib import Path

from .. import config
from ..discovery import Integration, NoIntegrationError, find_integration
from . import brand_image


class Report:
    """Collected failures, in the order they were found."""

    def __init__(self) -> None:
        """Start empty."""
        self.failures: list[tuple[str, str]] = []

    def fail(self, rule: str, message: str) -> None:
        """Record one rule that does not hold."""
        self.failures.append((rule, message))


Check = Callable[[Integration, config.Settings, Report], None]


# --- Bronze -----------------------------------------------------------------


def common_modules(it: Integration, _: config.Settings, report: Report) -> None:
    """Shared logic belongs in coordinator.py and entity.py."""
    for name in ("coordinator", "entity"):
        if not (it.path / f"{name}.py").exists():
            report.fail("common-modules", f"{name}.py is missing")


def runtime_data(it: Integration, _: config.Settings, report: Report) -> None:
    """State hangs off the entry, typed, not off hass.data."""
    init = it.source("__init__")
    if "runtime_data" not in init:
        report.fail("runtime-data", "__init__.py never assigns entry.runtime_data")
    if re.search(r"hass\.data\[\s*DOMAIN", init):
        report.fail("runtime-data", "__init__.py still uses hass.data[DOMAIN]")
    if not re.search(r"^type \w+ConfigEntry = ConfigEntry\[", init, re.M):
        report.fail("runtime-data", "no typed ConfigEntry alias in __init__.py")


def config_flow(it: Integration, _: config.Settings, report: Report) -> None:
    """Require a UI setup flow, declared in the manifest."""
    if not it.manifest.get("config_flow"):
        report.fail("config-flow", 'manifest.json does not set "config_flow": true')
    if not it.source("config_flow"):
        report.fail("config-flow", "config_flow.py is missing")


def test_before_configure(it: Integration, _: config.Settings, report: Report) -> None:
    """The flow talks to the device before it writes an entry."""
    flow = it.source("config_flow")
    if "errors" not in flow:
        report.fail("test-before-configure", "the flow reports no errors to the user")


def test_before_setup(it: Integration, _: config.Settings, report: Report) -> None:
    """An unreachable device fails setup properly."""
    if "ConfigEntryNotReady" not in it.source("__init__"):
        report.fail("test-before-setup", "__init__.py never raises ConfigEntryNotReady")


def entity_basics(it: Integration, _: config.Settings, report: Report) -> None:
    """Names and ids come from the base entity."""
    entity = it.source("entity")
    if "_attr_has_entity_name = True" not in entity:
        report.fail(
            "has-entity-name", "the base entity does not set _attr_has_entity_name"
        )
    if "_attr_unique_id" not in entity:
        report.fail("entity-unique-id", "the base entity does not set _attr_unique_id")


# What a brand folder carries, and how big each one has to be. The names are
# the ones the frontend looks for; the sizes are the ones home-assistant/brands
# specifies, and there is no reason for a locally shipped icon to differ.
BRAND_REQUIRED = {"icon.png": 256, "icon@2x.png": 512}
BRAND_OPTIONAL = {"dark_icon.png": 256, "dark_icon@2x.png": 512}


def _brand_ground(
    name: str, image: brand_image.Png, wanted: tuple[int, int, int], report: Report
) -> None:
    """Hold one image to the flat house-coloured ground."""
    if not image.readable:
        # Adam7 and 16-bit samples are deliberately not decoded here. Failing
        # is the honest outcome: the alternative is a rule that silently stops
        # being checked for exactly the files that differ from the build.
        report.fail(
            "brands",
            f"brand/{name} is interlaced or 16-bit, so its ground colour "
            "cannot be read - write it as an 8-bit, non-interlaced PNG",
        )
        return
    corners = image.corners()
    if len(corners) > 1:
        found = ", ".join(sorted(brand_image.to_hex(c) for c in corners))
        report.fail(
            "brands",
            f"brand/{name} has corners in {found} - the ground is meant to be "
            "one flat colour, edge to edge",
        )
        return
    if corners != {wanted}:
        found = brand_image.to_hex(next(iter(corners)))
        report.fail(
            "brands",
            f"brand/{name} sits on {found}, not the house colour "
            f"{brand_image.to_hex(wanted)}",
        )


def brands(it: Integration, settings: config.Settings, report: Report) -> None:
    """Require brand images in the house style, and a hacs.json that serves them."""
    folder = it.path / "brand"
    for name in BRAND_REQUIRED:
        if not (folder / name).exists():
            report.fail("brands", f"brand/{name} is missing")

    wanted = brand_image.parse_hex(settings.brand_color)
    if settings.brand_color and wanted is None:
        report.fail("brands", f"brand_color {settings.brand_color!r} is not '#RRGGBB'")

    for name, size in (BRAND_REQUIRED | BRAND_OPTIONAL).items():
        path = folder / name
        if not path.exists():
            continue
        try:
            image = brand_image.read(path)
        except brand_image.NotAPng as err:
            report.fail("brands", f"brand/{name}: {err}")
            continue
        if (image.width, image.height) != (size, size):
            report.fail(
                "brands",
                f"brand/{name} is {image.width}x{image.height}, not {size}x{size}",
            )
        if wanted is not None:
            _brand_ground(name, image, wanted, report)

    hacs = it.root / "hacs.json"
    if not hacs.exists():
        return
    import json

    minimum = json.loads(hacs.read_text(encoding="utf-8")).get("homeassistant", "0")
    try:
        parts = tuple(int(part) for part in minimum.split(".")[:2])
    except ValueError:
        parts = (0,)
    if parts < (2026, 3):
        report.fail(
            "brands",
            f"hacs.json requires {minimum}, but local brand images need 2026.3",
        )


def integration_owner(it: Integration, _: config.Settings, report: Report) -> None:
    """Require a complete manifest that is honest about the tier."""
    for key in (
        "domain",
        "name",
        "version",
        "codeowners",
        "documentation",
        "issue_tracker",
        "integration_type",
        "iot_class",
    ):
        if not it.manifest.get(key):
            report.fail("integration-owner", f"manifest.json lacks {key}")
    # Home Assistant reports "custom" for every integration outside core
    # (loader.py, Integration.quality_scale), whatever the manifest claims.
    # Any core tier here would be a claim the runtime never repeats.
    scale = it.manifest.get("quality_scale")
    if scale != "custom":
        report.fail(
            "integration-owner",
            f'manifest.json must declare quality_scale "custom", not {scale!r}; '
            "the tier actually met is recorded in quality_scale.yaml",
        )


# --- Silver -----------------------------------------------------------------


def config_entry_unloading(it: Integration, _: config.Settings, report: Report) -> None:
    """Require the entry to be removable without a restart."""
    if "async def async_unload_entry" not in it.source("__init__"):
        report.fail("config-entry-unloading", "async_unload_entry is missing")


def entity_unavailable(it: Integration, _: config.Settings, report: Report) -> None:
    """Something narrows availability beyond the coordinator's verdict."""
    text = it.source("entity") + "".join(it.source(p) for p in it.platforms)
    if "def available" not in text:
        report.fail("entity-unavailable", "no entity narrows availability")


def action_exceptions(it: Integration, _: config.Settings, report: Report) -> None:
    """Require a failed action to reach the user as a HomeAssistantError."""
    if "HomeAssistantError" not in it.source("coordinator"):
        report.fail("action-exceptions", "the coordinator raises no HomeAssistantError")


def parallel_updates(it: Integration, _: config.Settings, report: Report) -> None:
    """Every platform states its own limit."""
    for platform in it.platforms:
        if not re.search(r"^PARALLEL_UPDATES\s*=", it.source(platform), re.M):
            report.fail(
                "parallel-updates", f"{platform}.py does not set PARALLEL_UPDATES"
            )


def _flow_steps(it: Integration, rule: str, report: Report, *steps: str) -> None:
    flow = it.source("config_flow")
    for step in steps:
        if f"async def {step}" not in flow:
            report.fail(rule, f"{step} is missing")


def reauthentication_flow(it: Integration, _: config.Settings, report: Report) -> None:
    """Credentials can be renewed without deleting the entry."""
    _flow_steps(
        it,
        "reauthentication-flow",
        report,
        "async_step_reauth",
        "async_step_reauth_confirm",
    )


def reconfiguration_flow(it: Integration, _: config.Settings, report: Report) -> None:
    """Require a reconfigure step, so the device can be moved."""
    _flow_steps(it, "reconfiguration-flow", report, "async_step_reconfigure")


# --- Gold -------------------------------------------------------------------


def devices(it: Integration, _: config.Settings, report: Report) -> None:
    """Entities belong to a device, not to nothing."""
    if "DeviceInfo" not in it.source("entity"):
        report.fail("devices", "the base entity registers no device")


def diagnostics(it: Integration, _: config.Settings, report: Report) -> None:
    """There is something to attach to a bug report."""
    if not (it.path / "diagnostics.py").exists():
        report.fail("diagnostics", "diagnostics.py is missing")


def discovery(it: Integration, _: config.Settings, report: Report) -> None:
    """Whatever finds the device is declared and handled."""
    if not it.discovery_keys:
        report.fail(
            "discovery",
            "manifest.json declares no discovery matcher "
            "(bluetooth, dhcp, ssdp, zeroconf, usb, homekit, mqtt)",
        )
        return
    flow = it.source("config_flow")
    if not any(f"async_step_{key}" in flow for key in it.discovery_keys):
        declared = ", ".join(it.discovery_keys)
        report.fail("discovery", f"the flow has no step for the declared {declared}")


def entity_disabled_by_default(
    it: Integration, _: config.Settings, report: Report
) -> None:
    """Noisy entities start switched off."""
    if "entity_registry_enabled_default" not in "".join(
        it.source(platform) for platform in it.platforms
    ):
        report.fail(
            "entity-disabled-by-default",
            "no entity is noisy enough to be disabled by default - is that right?",
        )


def entity_translations(
    it: Integration, settings: config.Settings, report: Report
) -> None:
    """Every key an entity asks for exists, in every language."""
    strings = it.json("strings.json")
    for platform, keys in it.translation_keys.items():
        wanted = keys | settings.derived_translation_keys.get(platform, set())
        have = set(strings.get("entity", {}).get(platform, {}))
        for missing in sorted(wanted - have):
            report.fail(
                "entity-translations", f"strings.json lacks entity.{platform}.{missing}"
            )
    for language in _languages(it):
        translation = it.json(f"translations/{language}.json")
        if not translation:
            report.fail(
                "entity-translations", f"translations/{language}.json is missing"
            )
            continue
        for entry in _missing_keys(strings, translation)[:10]:
            report.fail(
                "entity-translations", f"translations/{language}.json lacks {entry}"
            )


def _languages(it: Integration) -> list[str]:
    """Return the languages shipped, with English always included."""
    folder = it.path / "translations"
    if not folder.is_dir():
        return ["en"]
    return sorted(path.stem for path in folder.glob("*.json")) or ["en"]


def _missing_keys(reference: dict, actual: dict, path: str = "") -> list[str]:
    """List the keys of the reference that the translation does not have."""
    missing: list[str] = []
    for key, value in reference.items():
        if key not in actual:
            missing.append(path + key)
        elif isinstance(value, dict) and isinstance(actual[key], dict):
            missing.extend(_missing_keys(value, actual[key], f"{path}{key}."))
    return missing


def icon_translations(
    it: Integration, settings: config.Settings, report: Report
) -> None:
    """Icons come from icons.json, and belong to an entity that exists."""
    icons = it.json("icons.json")
    if not icons:
        report.fail("icon-translations", "icons.json is missing")
    for platform, entries in icons.get("entity", {}).items():
        derived = settings.derived_translation_keys.get(platform, set())
        known = it.translation_keys.get(platform, set()) | derived
        for stray in sorted(set(entries) - known):
            report.fail(
                "icon-translations", f"icons.json: {platform}.{stray} has no entity"
            )
    # An icon= on an EntityDescription bypasses the translations entirely.
    for platform in it.platforms:
        if re.search(r"\bicon\s*=\s*[\"']mdi:", it.source(platform)):
            report.fail("icon-translations", f"{platform}.py hardcodes an mdi: icon")


def exception_translations(it: Integration, _: config.Settings, report: Report) -> None:
    """Every raised translation_key has a message to go with it."""
    strings = it.json("strings.json")
    known = set(strings.get("exceptions", {}))
    for name in ("coordinator", "__init__", "config_flow"):
        text = it.source(name)
        for match in re.finditer(r"translation_key=\"([^\"]+)\"", text):
            key = match.group(1)
            # Flow steps take their keys from config.*, not from exceptions.
            if name == "config_flow" and key in str(strings.get("config", {})):
                continue
            if key not in known and _raises_nearby(text, match.start()):
                report.fail(
                    "exception-translations",
                    f"{name}.py raises '{key}', absent from strings.json exceptions",
                )


def _raises_nearby(text: str, index: int) -> bool:
    """Return True when this translation_key belongs to a raise."""
    start = max(0, text.rfind("\n", 0, max(0, index - 400)))
    return "raise " in text[start:index]


# --- Platinum ---------------------------------------------------------------


def strict_typing(it: Integration, _: config.Settings, report: Report) -> None:
    """Require the package to be typed, and something to enforce it."""
    if not (it.path / "py.typed").exists():
        report.fail("strict-typing", "py.typed is missing")
    # Claiming strict typing without something that enforces it makes the
    # claim unverifiable. Either the shared ha-types hook, or mypy by hand.
    hooks = it.root / ".pre-commit-config.yaml"
    text = hooks.read_text(encoding="utf-8") if hooks.exists() else ""
    if "ha-types" not in text and "mypy" not in text:
        report.fail(
            "strict-typing",
            "nothing enforces it: no ha-types and no mypy hook in "
            ".pre-commit-config.yaml",
        )


def dependency_transparency(
    it: Integration, _: config.Settings, report: Report
) -> None:
    """Require a library from lib/ to be pinned, published and in step."""
    requirements = it.manifest.get("requirements", [])
    if not it.local_packages:
        if not requirements:
            report.fail(
                "dependency-transparency",
                "manifest.json requires nothing - is the device protocol inside "
                "the integration? It belongs in a package of its own.",
            )
        return
    for name, (pyproject, packaged) in it.local_packages.items():
        pinned = next(
            (r.split("==", 1)[1] for r in requirements if r.startswith(f"{name}==")),
            None,
        )
        if pinned is None:
            report.fail(
                "dependency-transparency",
                f"lib/ builds {name}, but manifest.json does not pin it with ==",
            )
            continue
        # A release tool should raise both in one commit; they can only drift
        # apart if someone edits one by hand - and then the integration would
        # install a version of the library that nobody built.
        if packaged and pinned != packaged:
            report.fail(
                "dependency-transparency",
                f"manifest.json pins {name}=={pinned}, but "
                f"{pyproject.relative_to(it.root)} is at {packaged}",
            )


# --- documentation ----------------------------------------------------------


def readme_section(rule: str) -> Check:
    """Build the check for one documentation rule."""

    def check(it: Integration, settings: config.Settings, report: Report) -> None:
        readme = it.root / "README.md"
        if not readme.exists():
            report.fail(rule, "README.md is missing")
            return
        text = readme.read_text(encoding="utf-8")
        wanted = settings.section_for(rule)
        if wanted is None:
            # The high level description is the title and the text under it.
            if not re.search(r"^#\s+\S", text, re.M):
                report.fail(rule, "README.md has no title")
            return
        pattern = re.compile(
            rf"^#{{1,4}}\s*{re.escape(wanted)}\s*$", re.M | re.IGNORECASE
        )
        if not pattern.search(text):
            report.fail(rule, f"README.md has no section '{wanted}'")

    return check


CHECKS: dict[str, Check] = {
    "common-modules": common_modules,
    "runtime-data": runtime_data,
    "config-flow": config_flow,
    "test-before-configure": test_before_configure,
    "test-before-setup": test_before_setup,
    "has-entity-name": entity_basics,
    "entity-unique-id": entity_basics,
    "brands": brands,
    "integration-owner": integration_owner,
    "config-entry-unloading": config_entry_unloading,
    "entity-unavailable": entity_unavailable,
    "action-exceptions": action_exceptions,
    "parallel-updates": parallel_updates,
    "reauthentication-flow": reauthentication_flow,
    "reconfiguration-flow": reconfiguration_flow,
    "devices": devices,
    "diagnostics": diagnostics,
    "discovery": discovery,
    "entity-disabled-by-default": entity_disabled_by_default,
    "entity-translations": entity_translations,
    "icon-translations": icon_translations,
    "exception-translations": exception_translations,
    "strict-typing": strict_typing,
    "dependency-transparency": dependency_transparency,
    **{rule: readme_section(rule) for rule in config.README_SECTIONS},
}


def main(argv: list[str] | None = None) -> int:
    """Run every check the integration claims."""
    start = Path(argv[0]) if argv else Path.cwd()
    try:
        it = find_integration(start)
    except NoIntegrationError as err:
        print(f"  quality scale: {err}", file=sys.stderr)
        return 1

    settings = config.load(it.root)
    report = Report()

    if not it.quality_scale:
        print(
            f"  quality scale: {it.domain} has no quality_scale.yaml - "
            "nothing is claimed, so nothing is checked."
        )
        return 0

    claimed = it.claimed_rules
    for rule, status in sorted(it.rule_status.items()):
        if status not in ("done", "todo", "exempt"):
            report.fail(rule, f"unknown status '{status}'")

    for rule in sorted(claimed):
        if check := CHECKS.get(rule):
            check(it, settings, report)
        elif not settings.needs_a_human(rule):
            report.fail(
                rule,
                "claimed as done, but no check in ha-integration-standards knows "
                "this rule - add one, or list it under unenforceable",
            )

    # A rule that is checkable and passes but is not claimed is worth knowing
    # about; that is a note, not a failure.
    notes = sorted(
        rule for rule in CHECKS if rule not in claimed and rule not in it.rule_status
    )

    if report.failures:
        print(f"Quality scale: {it.domain} is below what quality_scale.yaml claims\n")
        for rule, message in report.failures:
            print(f"  FAIL  {rule}: {message}")
        print(f"\n{len(report.failures)} problem(s). Fix them, or downgrade the claim.")
        return 1

    checked = len(claimed & set(CHECKS))
    print(
        f"Quality scale: {it.domain}, {len(claimed)} rules claimed, "
        f"{checked} machine-checked, all hold."
    )
    if notes:
        print("  note: not claimed yet: " + ", ".join(notes))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
