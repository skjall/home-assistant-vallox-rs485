# Vendored from ha-integration-standards 0.3.0. Do not edit:
# `ha-standards sync` rewrites this file, and `run.py verify` fails the
# commit when it has been changed by hand.

"""Find the integration in whatever repository we were pointed at.

Nothing here may be configured if it can be read instead. A domain, the
platforms in use, the packages in lib/ - the repository already states all of
it, and a second statement in a config file is one that can go stale.
"""

from __future__ import annotations

import ast
import json
import re
from dataclasses import dataclass, field
from functools import cached_property
from pathlib import Path

# Everything Home Assistant currently offers as a platform. Used to tell a
# platform module apart from a helper module of the same shape.
PLATFORM_NAMES = frozenset(
    {
        "air_quality",
        "alarm_control_panel",
        "binary_sensor",
        "button",
        "calendar",
        "camera",
        "climate",
        "conversation",
        "cover",
        "date",
        "datetime",
        "device_tracker",
        "event",
        "fan",
        "humidifier",
        "image",
        "image_processing",
        "lawn_mower",
        "light",
        "lock",
        "media_player",
        "notify",
        "number",
        "remote",
        "scene",
        "select",
        "sensor",
        "siren",
        "stt",
        "switch",
        "text",
        "time",
        "todo",
        "tts",
        "update",
        "vacuum",
        "valve",
        "wake_word",
        "water_heater",
        "weather",
    }
)

DISCOVERY_KEYS = ("bluetooth", "dhcp", "ssdp", "zeroconf", "usb", "homekit", "mqtt")


class NoIntegrationError(RuntimeError):
    """Raised when a repository holds no custom integration."""


@dataclass(frozen=True)
class Integration:
    """One integration inside one repository."""

    root: Path
    """Repository root - the directory that holds custom_components/."""

    path: Path
    """The integration package, custom_components/<domain>/."""

    _cache: dict[str, object] = field(default_factory=dict, compare=False, repr=False)

    # --- basics ---------------------------------------------------------

    @property
    def domain(self) -> str:
        """The domain, taken from the directory name."""
        return self.path.name

    @cached_property
    def manifest(self) -> dict:
        """manifest.json, or an empty dict when it is missing."""
        return self.json("manifest.json")

    @cached_property
    def quality_scale(self) -> dict:
        """quality_scale.yaml as it stands, or an empty dict."""
        import yaml

        path = self.path / "quality_scale.yaml"
        if not path.exists():
            return {}
        return yaml.safe_load(path.read_text(encoding="utf-8")) or {}

    @cached_property
    def claimed_rules(self) -> set[str]:
        """The rules quality_scale.yaml marks as done, in slug form."""
        claimed = set()
        for name, value in (self.quality_scale.get("rules") or {}).items():
            status = value if isinstance(value, str) else (value or {}).get("status")
            if status == "done":
                claimed.add(name.replace("_", "-"))
        return claimed

    @cached_property
    def rule_status(self) -> dict[str, str]:
        """Every rule with its status, in slug form."""
        statuses = {}
        for name, value in (self.quality_scale.get("rules") or {}).items():
            status = value if isinstance(value, str) else (value or {}).get("status")
            statuses[name.replace("_", "-")] = status or "unknown"
        return statuses

    # --- source ---------------------------------------------------------

    def source(self, module: str) -> str:
        """Return the text of one module, or "" when it does not exist."""
        path = self.path / f"{module}.py"
        return path.read_text(encoding="utf-8") if path.exists() else ""

    def json(self, relative: str) -> dict:
        """One JSON file inside the integration, or an empty dict."""
        path = self.path / relative
        if not path.exists():
            return {}
        return json.loads(path.read_text(encoding="utf-8"))

    @cached_property
    def platforms(self) -> tuple[str, ...]:
        """The platforms this integration ships.

        Read from the PLATFORMS list in __init__.py, because that is what
        Home Assistant acts on. Falls back to the platform modules present,
        so an integration that builds the list some other way still works.
        """
        from_init = self._platforms_from_init()
        if from_init:
            return from_init
        return tuple(
            sorted(
                path.stem
                for path in self.path.glob("*.py")
                if path.stem in PLATFORM_NAMES
            )
        )

    def _platforms_from_init(self) -> tuple[str, ...]:
        text = self.source("__init__")
        if not text:
            return ()
        try:
            tree = ast.parse(text)
        except SyntaxError:
            return ()
        found: list[str] = []
        for node in ast.walk(tree):
            if not isinstance(node, ast.AnnAssign | ast.Assign):
                continue
            targets = [node.target] if isinstance(node, ast.AnnAssign) else node.targets
            if not any(
                isinstance(t, ast.Name) and t.id == "PLATFORMS" for t in targets
            ):
                continue
            for element in ast.walk(node.value) if node.value else []:
                # Platform.SENSOR
                if (
                    isinstance(element, ast.Attribute)
                    and isinstance(element.value, ast.Name)
                    and element.value.id == "Platform"
                ):
                    found.append(element.attr.lower())
                # "sensor"
                elif isinstance(element, ast.Constant) and isinstance(
                    element.value, str
                ):
                    found.append(element.value)
        return tuple(sorted({name for name in found if name in PLATFORM_NAMES}))

    @cached_property
    def discovery_keys(self) -> tuple[str, ...]:
        """The discovery mechanisms the manifest declares."""
        return tuple(key for key in DISCOVERY_KEYS if self.manifest.get(key))

    @cached_property
    def translation_keys(self) -> dict[str, set[str]]:
        """Per platform, the translation keys its entities ask for."""
        keys: dict[str, set[str]] = {platform: set() for platform in self.platforms}
        for platform in self.platforms:
            path = self.path / f"{platform}.py"
            if not path.exists():
                continue
            try:
                tree = ast.parse(path.read_text(encoding="utf-8"))
            except SyntaxError:
                continue
            for node in ast.walk(tree):
                if (
                    isinstance(node, ast.keyword)
                    and node.arg == "translation_key"
                    and isinstance(node.value, ast.Constant)
                    and isinstance(node.value.value, str)
                ):
                    keys[platform].add(node.value.value)
        return keys

    # --- packages shipped alongside -------------------------------------

    @cached_property
    def local_packages(self) -> dict[str, tuple[Path, str | None]]:
        """Python packages under lib/, by distribution name.

        These are the protocol libraries an integration publishes separately
        and then pins. The value is the pyproject path and the version in it.
        """
        packages: dict[str, tuple[Path, str | None]] = {}
        for pyproject in (self.root / "lib").glob("*/pyproject.toml"):
            text = pyproject.read_text(encoding="utf-8")
            name = re.search(r'^name\s*=\s*"([^"]+)"', text, re.M)
            version = re.search(r'^version\s*=\s*"([^"]+)"', text, re.M)
            if name:
                packages[name.group(1)] = (
                    pyproject,
                    version.group(1) if version else None,
                )
        return packages


def find_integration(start: Path | None = None) -> Integration:
    """Locate the integration at or above the given directory."""
    here = (start or Path.cwd()).resolve()
    for candidate in (here, *here.parents):
        components = candidate / "custom_components"
        if not components.is_dir():
            continue
        packages = [
            path
            for path in sorted(components.iterdir())
            if path.is_dir() and (path / "manifest.json").exists()
        ]
        if len(packages) == 1:
            return Integration(root=candidate, path=packages[0])
        if len(packages) > 1:
            names = ", ".join(path.name for path in packages)
            raise NoIntegrationError(
                f"{components} holds more than one integration ({names}); "
                "these checks expect one per repository"
            )
    raise NoIntegrationError(
        f"no custom_components/<domain>/manifest.json at or above {here}"
    )
