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
    audit_write_failure,
    confirmation_already_used,
    confirmation_entity_mismatch,
    confirmation_expired,
    confirmation_not_found,
    confirmation_operation_mismatch,
    confirmation_rejected_or_cancelled,
    confirmation_user_mismatch,
    draft_version_mismatch,
    expected_version_mismatch,
    idempotency_key_missing,
    idempotency_payload_mismatch,
    idempotency_replay,
    invalid_contract_shape,
    invalid_enum_value,
    invalid_field_type,
    invalid_range,
    invalid_schema_version,
    missing_required_field,
    ownership_required,
    preview_summary_hash_mismatch,
    retry_limit_reached,
    transaction_conflict,
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

REQUIRED_M3_CODES = {
    ErrorCode.CONFIRMATION_NOT_FOUND,
    ErrorCode.CONFIRMATION_EXPIRED,
    ErrorCode.CONFIRMATION_ALREADY_USED,
    ErrorCode.CONFIRMATION_REJECTED_OR_CANCELLED,
    ErrorCode.CONFIRMATION_USER_MISMATCH,
    ErrorCode.CONFIRMATION_OPERATION_MISMATCH,
    ErrorCode.CONFIRMATION_ENTITY_MISMATCH,
    ErrorCode.PREVIEW_SUMMARY_HASH_MISMATCH,
    ErrorCode.EXPECTED_VERSION_MISMATCH,
    ErrorCode.DRAFT_VERSION_MISMATCH,
    ErrorCode.IDEMPOTENCY_KEY_MISSING,
    ErrorCode.IDEMPOTENCY_REPLAY,
    ErrorCode.IDEMPOTENCY_PAYLOAD_MISMATCH,
    ErrorCode.TRANSACTION_CONFLICT,
    ErrorCode.AUDIT_WRITE_FAILURE,
}


class ErrorCatalogTests(unittest.TestCase):
    def test_catalog_covers_required_m2_error_classes(self) -> None:
        self.assertLessEqual(REQUIRED_M2_CODES, set(ERROR_CATALOG))

    def test_catalog_covers_required_m3_commit_error_classes(self) -> None:
        self.assertLessEqual(REQUIRED_M3_CODES, set(ERROR_CATALOG))

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
            confirmation_not_found("confirm_001", "user_001"),
            confirmation_expired(
                "confirm_001",
                "2026-07-10T10:00:00Z",
                "2026-07-10T10:05:00Z",
            ),
            confirmation_already_used("confirm_001", "committed"),
            confirmation_rejected_or_cancelled("confirm_001", "rejected"),
            confirmation_user_mismatch("confirm_001", "user_001", "user_002"),
            confirmation_operation_mismatch(
                "confirm_001",
                "commit_profile",
                "commit_menu",
            ),
            confirmation_entity_mismatch("confirm_001", "entity_001", "entity_002"),
            preview_summary_hash_mismatch("confirm_001", "hash_001", "hash_002"),
            expected_version_mismatch("entity_001", 1, 2),
            draft_version_mismatch("entity_001", 3, 4),
            idempotency_key_missing("commit_profile", "user_001"),
            idempotency_replay("idem_001", "commit_profile", "version_002"),
            idempotency_payload_mismatch(
                "idem_001",
                "commit_profile",
                "payload_hash_001",
                "payload_hash_002",
            ),
            transaction_conflict("commit_profile", "entity_001"),
            audit_write_failure("commit_profile", "entity_001", "db_error"),
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

    def test_m4_profile_validation_errors_are_catalog_backed(self) -> None:
        payload = {
            "schema_version": "m2.v1",
            "user_id": "user_001",
            "draft_id": "profile_draft_001",
            "status": "created",
            "fields": {
                "user_facts": {
                    "people_count": 0,
                    "locale": "en-US",
                    "timezone": "UTC",
                    "available_equipment": ["stovetop"],
                    "default_max_active_time_minutes": 30,
                },
                "strict_restrictions": [],
                "soft_preferences": [],
            },
        }

        result = validate_contract("profile_draft", payload)

        self.assertFalse(result.is_valid)
        self.assertEqual(result.errors[0].code, ErrorCode.INVALID_RANGE)
        self.assertIn(result.errors[0].code, ERROR_CATALOG)
        self.assertEqual(
            result.errors[0].path,
            ("fields.user_facts.people_count",),
        )

    def test_error_json_uses_string_code_for_adapters(self) -> None:
        payload = missing_required_field("schema_version").to_json()

        self.assertEqual(payload["code"], "contract.missing_required_field")
        self.assertEqual(payload["path"], ["schema_version"])


if __name__ == "__main__":
    unittest.main()
