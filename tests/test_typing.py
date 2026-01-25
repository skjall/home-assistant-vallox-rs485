"""Tests for strict type checking compliance."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def test_mypy_strict_compliance() -> None:
    """Ensure codebase passes mypy strict mode."""
    project_root = Path(__file__).parent.parent
    source_path = project_root / "custom_components" / "vallox_rs485"

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "mypy",
            "--strict",
            "--ignore-missing-imports",
            str(source_path),
        ],
        capture_output=True,
        text=True,
        cwd=project_root,
    )

    if result.returncode != 0:
        error_lines = result.stdout.strip().split("\n") if result.stdout else []
        error_count = len([line for line in error_lines if ": error:" in line])

        error_msg = (
            f"mypy strict mode found {error_count} errors:\n\n"
            f"{result.stdout}\n"
            f"Run 'mypy --strict custom_components/vallox_rs485/' to see details."
        )
        raise AssertionError(error_msg)
