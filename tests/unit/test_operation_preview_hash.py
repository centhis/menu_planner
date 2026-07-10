from __future__ import annotations

import re
import unittest

from menu_planner.application.safe_commit import (
    OperationPreviewInput,
    build_operation_preview,
    canonical_preview_payload,
    operation_preview_summary_hash,
)

HEX_SHA256 = re.compile(r"^[0-9a-f]{64}$")


class OperationPreviewHashTests(unittest.TestCase):
    def test_summary_hash_is_stable_for_different_object_key_order(self) -> None:
        left = OperationPreviewInput(
            preview_id="preview_001",
            operation="commit_m3_record",
            user_id="user_001",
            entity_type="m3_test_entity",
            entity_id="entity_001",
            expected_version=1,
            draft_version=2,
            committed_relevant_payload={
                "constraints": {"max_minutes": 20, "equipment": ["pan", "pot"]},
                "title": "Weeknight dinner",
            },
        )
        right = OperationPreviewInput(
            preview_id="preview_002",
            operation="commit_m3_record",
            user_id="user_001",
            entity_type="m3_test_entity",
            entity_id="entity_001",
            expected_version=1,
            draft_version=2,
            committed_relevant_payload={
                "title": "Weeknight dinner",
                "constraints": {"equipment": ["pan", "pot"], "max_minutes": 20},
            },
        )

        summary_hash = operation_preview_summary_hash(left)

        self.assertRegex(summary_hash, HEX_SHA256)
        self.assertEqual(summary_hash, operation_preview_summary_hash(right))

    def test_summary_hash_changes_when_committed_relevant_payload_changes(
        self,
    ) -> None:
        base = OperationPreviewInput(
            preview_id="preview_001",
            operation="commit_m3_record",
            user_id="user_001",
            entity_type="m3_test_entity",
            entity_id="entity_001",
            expected_version=1,
            draft_version=2,
            committed_relevant_payload={"items": ["eggs", "rice"]},
        )
        changed = OperationPreviewInput(
            preview_id="preview_001",
            operation="commit_m3_record",
            user_id="user_001",
            entity_type="m3_test_entity",
            entity_id="entity_001",
            expected_version=1,
            draft_version=2,
            committed_relevant_payload={"items": ["rice", "eggs"]},
        )

        self.assertNotEqual(
            operation_preview_summary_hash(base),
            operation_preview_summary_hash(changed),
        )

    def test_summary_hash_changes_when_version_or_user_changes(self) -> None:
        base = OperationPreviewInput(
            preview_id="preview_001",
            operation="commit_m3_record",
            user_id="user_001",
            entity_type="m3_test_entity",
            entity_id="entity_001",
            expected_version=1,
            draft_version=2,
            committed_relevant_payload={"value": "draft"},
        )
        changed_user = OperationPreviewInput(
            preview_id="preview_001",
            operation="commit_m3_record",
            user_id="user_002",
            entity_type="m3_test_entity",
            entity_id="entity_001",
            expected_version=1,
            draft_version=2,
            committed_relevant_payload={"value": "draft"},
        )
        changed_version = OperationPreviewInput(
            preview_id="preview_001",
            operation="commit_m3_record",
            user_id="user_001",
            entity_type="m3_test_entity",
            entity_id="entity_001",
            expected_version=2,
            draft_version=3,
            committed_relevant_payload={"value": "draft"},
        )

        base_hash = operation_preview_summary_hash(base)

        self.assertNotEqual(base_hash, operation_preview_summary_hash(changed_user))
        self.assertNotEqual(base_hash, operation_preview_summary_hash(changed_version))

    def test_display_only_changes_do_not_drive_summary_hash(self) -> None:
        base = OperationPreviewInput(
            preview_id="preview_001",
            operation="commit_m3_record",
            user_id="user_001",
            entity_type="m3_test_entity",
            entity_id="entity_001",
            expected_version=1,
            draft_version=2,
            committed_relevant_payload={"value": "draft"},
            changes=[{"text": "Save the draft"}],
        )
        wording_changed = OperationPreviewInput(
            preview_id="preview_001",
            operation="commit_m3_record",
            user_id="user_001",
            entity_type="m3_test_entity",
            entity_id="entity_001",
            expected_version=1,
            draft_version=2,
            committed_relevant_payload={"value": "draft"},
            changes=[{"text": "Persist this version"}],
        )

        self.assertEqual(
            operation_preview_summary_hash(base),
            operation_preview_summary_hash(wording_changed),
        )

    def test_build_operation_preview_uses_computed_summary_hash(self) -> None:
        preview_input = OperationPreviewInput(
            preview_id="preview_001",
            operation="commit_m3_record",
            user_id="user_001",
            entity_type="m3_test_entity",
            entity_id="entity_001",
            expected_version=1,
            draft_version=2,
            committed_relevant_payload={"value": "draft"},
            changes=[{"field": "value"}],
        )

        preview = build_operation_preview(preview_input)

        self.assertEqual(preview.entity_ref, "m3_test_entity:entity_001")
        self.assertEqual(
            preview.summary_hash,
            operation_preview_summary_hash(preview_input),
        )
        self.assertEqual(preview.changes, [{"field": "value"}])
        self.assertTrue(preview.requires_confirmation)

    def test_canonical_payload_contains_only_committed_relevant_fields(self) -> None:
        preview_input = OperationPreviewInput(
            preview_id="preview_001",
            operation="commit_m3_record",
            user_id="user_001",
            entity_type="m3_test_entity",
            entity_id="entity_001",
            expected_version=1,
            draft_version=2,
            committed_relevant_payload={"value": "draft"},
            changes=[{"text": "Display only"}],
        )

        payload = canonical_preview_payload(preview_input)

        self.assertEqual(
            set(payload),
            {
                "schema_version",
                "operation",
                "user_id",
                "entity_type",
                "entity_id",
                "expected_version",
                "draft_version",
                "committed_relevant_payload",
            },
        )


if __name__ == "__main__":
    unittest.main()
