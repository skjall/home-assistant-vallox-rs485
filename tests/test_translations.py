"""Tests for translation completeness."""

from __future__ import annotations

import json
from pathlib import Path


def get_all_keys(obj: dict, prefix: str = "") -> set[str]:
    """Recursively extract all keys from a nested dictionary."""
    keys = set()
    for key, value in obj.items():
        full_key = f"{prefix}.{key}" if prefix else key
        keys.add(full_key)
        if isinstance(value, dict):
            keys.update(get_all_keys(value, full_key))
    return keys


def test_all_translations_have_fallback_keys() -> None:
    """Ensure all translation files contain all keys from strings.json."""
    base_path = Path(__file__).parent.parent / "custom_components" / "vallox_rs485"
    strings_path = base_path / "strings.json"
    translations_path = base_path / "translations"

    with open(strings_path, encoding="utf-8") as f:
        reference = json.load(f)

    reference_keys = get_all_keys(reference)

    translation_files = list(translations_path.glob("*.json"))
    assert len(translation_files) > 0, "No translation files found"

    missing_keys_report: dict[str, set[str]] = {}

    for trans_file in translation_files:
        with open(trans_file, encoding="utf-8") as f:
            translation = json.load(f)

        translation_keys = get_all_keys(translation)
        missing = reference_keys - translation_keys

        if missing:
            missing_keys_report[trans_file.name] = missing

    if missing_keys_report:
        report_lines = ["Missing keys in translations:"]
        for filename, keys in sorted(missing_keys_report.items()):
            report_lines.append(f"\n{filename}:")
            for key in sorted(keys):
                report_lines.append(f"  - {key}")
        raise AssertionError("\n".join(report_lines))


def test_no_extra_keys_in_translations() -> None:
    """Ensure translations don't have keys that don't exist in strings.json."""
    base_path = Path(__file__).parent.parent / "custom_components" / "vallox_rs485"
    strings_path = base_path / "strings.json"
    translations_path = base_path / "translations"

    with open(strings_path, encoding="utf-8") as f:
        reference = json.load(f)

    reference_keys = get_all_keys(reference)

    translation_files = list(translations_path.glob("*.json"))

    extra_keys_report: dict[str, set[str]] = {}

    for trans_file in translation_files:
        with open(trans_file, encoding="utf-8") as f:
            translation = json.load(f)

        translation_keys = get_all_keys(translation)
        extra = translation_keys - reference_keys

        if extra:
            extra_keys_report[trans_file.name] = extra

    if extra_keys_report:
        report_lines = ["Extra keys in translations (not in strings.json):"]
        for filename, keys in sorted(extra_keys_report.items()):
            report_lines.append(f"\n{filename}:")
            for key in sorted(keys):
                report_lines.append(f"  - {key}")
        raise AssertionError("\n".join(report_lines))


def test_translation_files_valid_json() -> None:
    """Ensure all translation files are valid JSON."""
    base_path = Path(__file__).parent.parent / "custom_components" / "vallox_rs485"
    translations_path = base_path / "translations"

    translation_files = list(translations_path.glob("*.json"))
    assert len(translation_files) > 0, "No translation files found"

    for trans_file in translation_files:
        try:
            with open(trans_file, encoding="utf-8") as f:
                json.load(f)
        except json.JSONDecodeError as e:
            raise AssertionError(f"Invalid JSON in {trans_file.name}: {e}") from e


def test_strings_json_valid() -> None:
    """Ensure strings.json is valid JSON."""
    base_path = Path(__file__).parent.parent / "custom_components" / "vallox_rs485"
    strings_path = base_path / "strings.json"

    try:
        with open(strings_path, encoding="utf-8") as f:
            data = json.load(f)
        assert "config" in data, "strings.json must have 'config' section"
        assert "entity" in data, "strings.json must have 'entity' section"
    except json.JSONDecodeError as e:
        raise AssertionError(f"Invalid JSON in strings.json: {e}") from e


# Keys that are allowed to remain in English (technical terms, cognates)
ALLOWED_ENGLISH_KEYS = {
    "entity.sensor.co2_ppm.name",  # CO2 is universal
    "entity.binary_sensor.damper_motor_position.name",  # Bypass is technical
    "entity.fan.ventilation.name",  # Ventilation is same in many languages (da, fr, sv)
}


def get_leaf_values(obj: dict, prefix: str = "") -> dict[str, str]:
    """Recursively extract all leaf string values from a nested dictionary."""
    values = {}
    for key, value in obj.items():
        full_key = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict):
            values.update(get_leaf_values(value, full_key))
        elif isinstance(value, str):
            values[full_key] = value
    return values


def test_entity_names_are_translated() -> None:
    """Ensure entity names are actually translated, not left in English."""
    base_path = Path(__file__).parent.parent / "custom_components" / "vallox_rs485"
    strings_path = base_path / "strings.json"
    translations_path = base_path / "translations"

    with open(strings_path, encoding="utf-8") as f:
        reference = json.load(f)

    # Get English entity names from strings.json (which is English)
    english_values = get_leaf_values(reference.get("entity", {}), "entity")

    translation_files = list(translations_path.glob("*.json"))
    # Exclude en.json since it's supposed to match strings.json
    translation_files = [f for f in translation_files if f.name != "en.json"]

    untranslated_report: dict[str, list[str]] = {}

    for trans_file in translation_files:
        with open(trans_file, encoding="utf-8") as f:
            translation = json.load(f)

        trans_values = get_leaf_values(translation.get("entity", {}), "entity")
        untranslated = []

        for key, eng_value in english_values.items():
            if key in ALLOWED_ENGLISH_KEYS:
                continue
            trans_value = trans_values.get(key)
            if trans_value and trans_value == eng_value:
                untranslated.append(f"{key} = '{eng_value}'")

        if untranslated:
            untranslated_report[trans_file.name] = untranslated

    if untranslated_report:
        report_lines = ["Untranslated entity names (still in English):"]
        for filename, keys in sorted(untranslated_report.items()):
            report_lines.append(f"\n{filename}:")
            for key in sorted(keys):
                report_lines.append(f"  - {key}")
        raise AssertionError("\n".join(report_lines))
