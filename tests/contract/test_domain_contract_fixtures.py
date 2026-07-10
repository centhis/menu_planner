from __future__ import annotations

import json
import pathlib
import unittest
from dataclasses import fields, is_dataclass
from typing import Any, cast

from menu_planner.domain.contracts.models import SCHEMA_VERSION
from menu_planner.domain.contracts.validation import CONTRACT_VALIDATORS
from menu_planner.domain.errors import ErrorCode

ROOT = pathlib.Path(__file__).resolve().parents[2]
FIXTURES_ROOT = ROOT / "fixtures" / "domain" / "contracts"

EXPECTED_INVALID_ERROR_CODES = {
    "missing_schema_version.json": ErrorCode.MISSING_REQUIRED_FIELD,
    "missing_profile_fields.json": ErrorCode.MISSING_REQUIRED_FIELD,
    "strict_restriction_missing_value.json": ErrorCode.MISSING_REQUIRED_FIELD,
    "equipment_item_not_string.json": ErrorCode.INVALID_FIELD_TYPE,
    "people_count_zero.json": ErrorCode.INVALID_RANGE,
    "version_zero.json": ErrorCode.INVALID_RANGE,
}

EXPECTED_INVALID_ERROR_PATHS = {
    "missing_schema_version.json": ("schema_version",),
    "missing_profile_fields.json": ("fields.user_facts",),
    "strict_restriction_missing_value.json": (
        "fields.strict_restrictions.0.value",
    ),
    "equipment_item_not_string.json": (
        "fields.user_facts.available_equipment.1",
    ),
    "people_count_zero.json": ("fields.user_facts.people_count",),
    "version_zero.json": ("version",),
}


def _load_json(path: pathlib.Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


class DomainContractFixtureTests(unittest.TestCase):
    def test_all_m2_contracts_have_fixture_directories(self) -> None:
        fixture_names = {path.name for path in FIXTURES_ROOT.iterdir() if path.is_dir()}

        self.assertEqual(fixture_names, set(CONTRACT_VALIDATORS))

        for contract_name in CONTRACT_VALIDATORS:
            self.assertTrue((FIXTURES_ROOT / contract_name / "valid").is_dir())
            self.assertTrue((FIXTURES_ROOT / contract_name / "invalid").is_dir())

    def test_all_contract_models_have_schema_version_field(self) -> None:
        for contract_name, validator in CONTRACT_VALIDATORS.items():
            with self.subTest(contract=contract_name):
                self.assertTrue(is_dataclass(validator.model))
                model = cast(Any, validator.model)
                field_names = {field.name for field in fields(model)}
                self.assertIn("schema_version", field_names)

    def test_valid_fixtures_validate(self) -> None:
        for contract_name, validator in CONTRACT_VALIDATORS.items():
            valid_dir = FIXTURES_ROOT / contract_name / "valid"
            fixture_paths = sorted(valid_dir.glob("*.json"))
            self.assertGreater(len(fixture_paths), 0, contract_name)

            for fixture_path in fixture_paths:
                with self.subTest(contract=contract_name, fixture=fixture_path.name):
                    payload = _load_json(fixture_path)
                    if not isinstance(payload, dict):
                        self.fail(f"{fixture_path} must contain a JSON object")
                    self.assertEqual(payload.get("schema_version"), SCHEMA_VERSION)

                    result = validator.validate(payload)

                    self.assertTrue(result.is_valid, result.errors)
                    self.assertIsNotNone(result.value)

    def test_invalid_fixtures_return_stable_machine_error(self) -> None:
        for contract_name, validator in CONTRACT_VALIDATORS.items():
            invalid_dir = FIXTURES_ROOT / contract_name / "invalid"
            fixture_paths = sorted(invalid_dir.glob("*.json"))
            self.assertGreater(len(fixture_paths), 0, contract_name)

            for fixture_path in fixture_paths:
                with self.subTest(contract=contract_name, fixture=fixture_path.name):
                    result = validator.validate(_load_json(fixture_path))

                    self.assertFalse(result.is_valid)
                    self.assertEqual(result.value, None)
                    expected_code = EXPECTED_INVALID_ERROR_CODES[fixture_path.name]
                    expected_path = EXPECTED_INVALID_ERROR_PATHS[fixture_path.name]
                    self.assertEqual(result.errors[0].code, expected_code)
                    self.assertEqual(
                        result.errors[0].to_json()["code"],
                        expected_code.value,
                    )
                    self.assertEqual(result.errors[0].path, expected_path)


if __name__ == "__main__":
    unittest.main()
