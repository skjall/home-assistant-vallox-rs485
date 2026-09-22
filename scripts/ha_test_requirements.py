#!/usr/bin/env python3
"""Print everything the tests need beyond Home Assistant itself.

Two sources, both read from files that already exist, so nothing here is ever
maintained by hand:

* The integration's own `requirements` - the libraries it imports at runtime.
  Tests import the same modules, so they need the same libraries. One of them
  may live in this repository rather than on PyPI; that one is installed from
  where it lies, see `_local_distributions`.
* The requirements of the Home Assistant components it depends on (bluetooth,
  usb, ...). pytest-homeassistant-custom-component installs Home Assistant but
  not those. Pinning them by hand means the numbers drift from the release
  being tested against, and a dependency bot keeps proposing bumps that must
  never be taken on their own. Reading them out of the installed release
  removes both problems: they are always exactly right, and there is nothing
  left to pin.
"""

from __future__ import annotations

import json
import re
import site
import sys
import tomllib
from pathlib import Path


def _components_directory() -> Path | None:
    for directory in site.getsitepackages():
        components = Path(directory) / "homeassistant" / "components"
        if components.is_dir():
            return components
    return None


def _manifest() -> dict:
    """Return the integration's manifest, or an empty dict.

    Two places, because this also runs during the Docker build, where the
    integration is not in the image yet - only its manifest is, copied next to
    this script so that a code change does not invalidate the build cache.
    """
    here = Path(__file__).resolve().parent
    candidates = [
        *sorted(Path("custom_components").glob("*/manifest.json")),
        *sorted(here.glob("manifest.json")),
        *sorted(here.glob("*/manifest.json")),
    ]
    for manifest in candidates:
        return json.loads(manifest.read_text(encoding="utf-8"))
    return {}


def _canonical(name: str) -> str:
    """Return a distribution name in the one spelling PEP 503 compares by."""
    return re.sub(r"[-_.]+", "-", name).lower()


def _distribution(requirement: str) -> str:
    """Return the distribution a requirement line names, without its version."""
    return _canonical(re.split(r"[<>=!~;\[ ]", requirement, maxsplit=1)[0].strip())


def _local_distributions() -> dict[str, Path]:
    """Return the distributions this repository builds itself, by name.

    An integration that reverse-engineered a protocol keeps that package under
    `lib/` and pins it in the manifest. Installing it from PyPI would be wrong
    twice over. It tests the release before last, so the code under `lib/` -
    the code being changed - is never the code under test. And during a release
    it cannot be installed at all: the tool raises the pin in the manifest and
    the version in `lib/` in one commit, while the version itself only reaches
    PyPI once that commit is merged. Every release would go red on a package
    that is sitting right there in the checkout.

    Looked for beside this script as well, because the image build copies it
    into a directory of its own rather than running it from the project root.
    """
    here = Path(__file__).resolve().parent
    found: dict[str, Path] = {}
    for root in (Path("lib"), here / "lib", here.parent / "lib"):
        if not root.is_dir():
            continue
        for pyproject in sorted(root.glob("*/pyproject.toml")):
            name = tomllib.loads(pyproject.read_text(encoding="utf-8"))
            if project_name := name.get("project", {}).get("name"):
                # Resolved, because pip reads the file from wherever it was
                # started, which is not where this ran.
                found.setdefault(_canonical(project_name), pyproject.parent.resolve())
    return found


def _components(manifest: dict) -> list[str]:
    """Return the Home Assistant components this integration depends on."""
    wanted = list(manifest.get("dependencies", []))
    # An integration that depends on bluetooth_adapters also needs what the
    # bluetooth component itself pulls in.
    if "bluetooth_adapters" in wanted:
        wanted += ["bluetooth", "usb"]
    return sorted(set(wanted))


def main() -> int:
    """Print one requirement per line."""
    manifest = _manifest()

    # What the integration itself imports. Without this the tests fail at
    # import time, and only in CI, because a locally built image usually still
    # carries the library from an earlier install.
    local = _local_distributions()
    for requirement in manifest.get("requirements", []):
        if directory := local.get(_distribution(requirement)):
            print(directory)
            continue
        print(requirement)

    components = _components_directory()
    if components is None:
        print("Home Assistant is not installed", file=sys.stderr)
        return 1

    for name in _components(manifest):
        component = components / name / "manifest.json"
        if not component.exists():
            continue
        for requirement in json.loads(component.read_text()).get("requirements", []):
            print(requirement)
    return 0


if __name__ == "__main__":
    sys.exit(main())
