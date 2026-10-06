# Vendored from ha-integration-standards 0.4.1. Do not edit:
# `ha-standards sync` rewrites this file, and `run.py verify` fails the
# commit when it has been changed by hand.

"""Run the tests and the type check where they mean something.

Home Assistant needs Python 3.14.2 from 2026.3 onwards, which most systems do
not have. Running the suite on whatever interpreter happens to be installed
means testing an API that is not the one users have. So both run in a
container built from the version the integration targets.

Isolation is part of the point: the source is mounted read-only, the container
runs as the calling user and without a network, so a run cannot change the
working tree or reach out. Everything a run produces lands in the artefacts
directory.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

from . import config
from .discovery import Integration, NoIntegrationError, find_integration

DOCKERFILE = "Dockerfile.test"

# Nothing in the image is pinned by hand: pytest-homeassistant-custom-component
# decides which Home Assistant comes in, and it follows the releases, betas
# included. So an image that is still there is not an image that still tests
# what users run - a fortnight-old one type checked correct code as wrong,
# because 2026.9 annotated data_schema as voluptuous and 2026.10 annotates it
# as probatio. A rebuild costs minutes; testing yesterday's Home Assistant and
# believing it costs more.
MAX_IMAGE_AGE_DAYS = 7


def _image_name(it: Integration) -> str:
    return f"{it.domain.replace('_', '-')}-test"


def _ensure_image(it: Integration) -> str:
    """Build the test image when it is missing or has gone stale."""
    if not shutil.which("docker"):
        raise RuntimeError(
            "docker is required: the suite runs against the Home Assistant "
            "release this integration targets, not against the local Python."
        )
    image = _image_name(it)
    age = _image_age(image)
    if age is not None and age.days < MAX_IMAGE_AGE_DAYS:
        return image

    dockerfile = it.root / DOCKERFILE
    if not dockerfile.exists():
        raise RuntimeError(
            f"{DOCKERFILE} is missing - run 'ha-standards sync' to write the "
            "managed one."
        )
    if age is None:
        print(f"Building {image} ...", flush=True)
    else:
        print(
            f"Rebuilding {image}: it is {age.days} days old, and the Home "
            "Assistant release inside it is whatever was current then.",
            flush=True,
        )
    subprocess.run(
        ["docker", "build", "-q", "-f", str(dockerfile), "-t", image, str(it.root)],
        check=True,
        stdout=subprocess.DEVNULL,
    )
    return image


def _image_age(image: str) -> timedelta | None:
    """How long ago the image was built, or None when there is no image.

    An unreadable timestamp counts as no image: rebuilding costs minutes,
    while trusting an image of unknown age costs a wrong verdict.
    """
    created = subprocess.run(
        ["docker", "image", "inspect", "-f", "{{.Created}}", image],
        capture_output=True,
        text=True,
        check=False,
    )
    if created.returncode != 0:
        return None
    stamp = created.stdout.strip()
    # Docker reports more precision than fromisoformat accepts before 3.11 and
    # a trailing Z that it never accepted; both are easier to cut than to parse.
    stamp = re.sub(r"(\.\d{6})\d+", r"\1", stamp).replace("Z", "+00:00")
    try:
        built = datetime.fromisoformat(stamp)
    except ValueError:
        return None
    return datetime.now(tz=built.tzinfo) - built


def _run(
    it: Integration,
    image: str,
    command: list[str],
    *,
    network: bool,
    as_user: bool = True,
) -> int:
    artefacts = it.root / ".artefakte"
    artefacts.mkdir(exist_ok=True)
    docker = [
        "docker",
        "run",
        "--rm",
        # Run as the caller so nothing a test writes is owned by root. The
        # type check is the exception: it installs into the image's own
        # site-packages and the container is thrown away either way.
        *(["--user", f"{os.getuid()}:{os.getgid()}"] if as_user else []),
        "-e",
        "HOME=/tmp",
        "-e",
        "PYTHONDONTWRITEBYTECODE=1",
        "-e",
        "COVERAGE_FILE=/ausgabe/.coverage",
        "-v",
        f"{it.root}:/app:ro",
        "-v",
        f"{artefacts}:/ausgabe",
        "-w",
        "/app",
    ]
    if not network:
        docker += ["--network", "none"]
    docker += [image, *command]
    return subprocess.run(docker, check=False).returncode


def _integration() -> Integration:
    try:
        return find_integration(Path.cwd())
    except NoIntegrationError as err:
        print(f"  {err}", file=sys.stderr)
        raise SystemExit(1) from err


def tests(argv: list[str] | None = None) -> int:
    """Run pytest inside the container, coverage report into .artefakte/."""
    it = _integration()
    settings = config.load(it.root)
    image = _ensure_image(it)
    report = Path(settings.coverage_report).name
    return _run(
        it,
        image,
        [
            "pytest",
            "-p",
            "no:cacheprovider",
            f"--cov=custom_components.{it.domain}",
            f"--cov-report=json:/ausgabe/{report}",
            *(argv or sys.argv[1:]),
        ],
        network=False,
    )


def types(argv: list[str] | None = None) -> int:
    """Type check in the same environment. Platinum asks for strict."""
    it = _integration()
    image = _ensure_image(it)
    target = it.path.relative_to(it.root).as_posix()
    # mypy is installed here rather than baked into the image so that a bumped
    # mypy takes effect without rebuilding. A failed install has to fail the
    # run: swallowing it turns a broken environment into "mypy: not found".
    return _run(
        it,
        image,
        [
            "sh",
            "-ec",
            "pip install -q --root-user-action=ignore mypy; "
            "mypy --config-file mypy.ini "
            f"--cache-dir=/tmp/mypy {target}",
        ],
        network=True,
        as_user=False,
    )


if __name__ == "__main__":
    raise SystemExit(tests())
