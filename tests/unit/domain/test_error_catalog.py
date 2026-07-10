from __future__ import annotations

import re
import unittest

from menu_planner.domain.contracts.validation import validate_contract
from menu_planner.domain.errors import (
    ERROR_CATALOG,
    ErrorCode,
    UserExposure,
    action_not_allowed,
    administrative_action_denied,
    ambiguous_or_incomplete_intent,
    invalid_contract_shape,
    invalid_enum_value,
    invalid_field_type,
    invalid_range,
    invalid_schema_version,
    missing_required_field,
    ownership_required,
    retry_limit_reached,
    unsupported_intent,
)

CODE_PATTERN = re.compile(r"^[a-z]+(\.[a-z0-9_]+)+$")

REQUIRED_M2_CODES = {
    ErrorCode.INVALID_SCHEMA_VERSION,
    ErrorCode.MISSING_REQUIRED_FIELD,
    ErrorCode.INVALID_ENUM_VALUE,
    ErrorCode.INVALID_RANGE,
    ErrorCode.ACTION_NOT_ALLOWED,
    ErrorCode.ADMINISTRATIVE_ACTION_DENIED,
    ErrorCode.AMBIGUOUS_OR_INCOMPLETE_INTENT,
    ErrorCode.UNSUPPORTED_INTENT,
    ErrorCode.OWNERSHIP_REQUIRED,
    ErrorCode.RETRY_LIMIT_REACHED,
}


class ErrorCatalogTests(unittest.TestCase):
    def test_catalog_covers_required_m2_error_classes(self) -> None:
        self.assertLessEqual(REQUIRED_M2_CODES, set(ERROR_CATALOG))

    def test_error_codes_are_stable_machine_values(self) -> None:
        codes = [entry.code.value for entry in ERROR_CATALOG.values()]

        self.assertEqual(len(codes), len(set(codes)))
        for code in codes:
            self.assertRegex(code, CODE_PATTERN)

    def test_catalog_entries_include_repair_loop_metadata(self) -> None:
        for code, entry in ERROR_CATALOG.items():
            with self.subTest(code=code.value):
                self.assertEqual(entry.code, code)
                self.assertTrue(entry.developer_message)
                self.assertGreater(len(entry.sources), 0)
                self.assertIn(
                    entry.user_exposure,
                    {UserExposure.DIRECT, UserExposure.ADAPTER_REQUIRED},
                )

    def test_error_factories_use_catalog_codes_and_messages(self) -> None:
        examples = [
            missing_required_field("schema_version"),
            invalid_schema_version("m1.v1"),
            invalid_field_type("confidence", "number"),
            invalid_enum_value("operation_class", ["read_only"]),
            invalid_range("confidence", 0.0, 1.0, 2.0),
            invalid_contract_shape(),
            action_not_allowed("ready", "commit", ["show_status"]),
            administrative_action_denied("install_skill", "telegram_user"),
            ambiguous_or_incomplete_intent("replace_meal", ["date"], ["meal_type"]),
            unsupported_intent("order_delivery"),
            ownership_required("menu_001", "user_001"),
            retry_limit_reached("workflow_001", "menu_generating", 3, 3),
        ]

        for error in examples:
            with self.subTest(code=error.code.value):
                self.assertIn(error.code, ERROR_CATALOG)
                self.assertEqual(
                    error.message, ERROR_CATALOG[error.code].developer_message
                )
                self.assertLessEqual(
                    set(error.details),
                    set(ERROR_CATALOG[error.code].machine_fields),
                )

    def test_validation_errors_are_catalog_backed(self) -> None:
        result = validate_contract("parsed_intent", {"schema_version": "m1.v1"})

        self.assertFalse(result.is_valid)
        self.assertEqual(result.errors[0].code, ErrorCode.INVALID_SCHEMA_VERSION)
        self.assertIn(result.errors[0].code, ERROR_CATALOG)
        self.assertEqual(
            result.errors[0].message,
            ERROR_CATALOG[ErrorCode.INVALID_SCHEMA_VERSION].developer_message,
        )

    def test_error_json_uses_string_code_for_adapters(self) -> None:
        payload = missing_required_field("schema_version").to_json()

        self.assertEqual(payload["code"], "contract.missing_required_field")
        self.assertEqual(payload["path"], ["schema_version"])


if __name__ == "__main__":
    unittest.main()
