from __future__ import annotations

import unittest

from menu_planner.application.profile_persistence import (
    PROFILE_COMMIT_OPERATION,
    PROFILE_ENTITY_TYPE,
    ProfileVersionedRecordRepository,
    profile_entity_id,
)
from menu_planner.application.safe_commit import VersionedRecord
from menu_planner.domain.contracts.models import (
    SCHEMA_VERSION,
    DraftStatus,
    JsonObject,
    ProfileDraft,
    ProfileVersion,
)


def _profile_fields() -> JsonObject:
    return {
        "user_facts": {
            "people_count": 1,
            "locale": "en-US",
            "timezone": "UTC",
            "available_equipment": ["stovetop"],
            "default_max_active_time_minutes": 30,
        },
        "strict_restrictions": [
            {
                "kind": "ingredient_exclusion",
                "value": "peanut",
            }
        ],
        "soft_preferences": [
            {
                "direction": "prefer",
                "value": "vegetables",
            }
        ],
    }


class InMemoryVersionedRecordRepository:
    def __init__(self) -> None:
        self.records: list[VersionedRecord] = []

    def add(self, record: VersionedRecord) -> None:
        self.records.append(record)

    def get(
        self,
        user_id: str,
        entity_type: str,
        entity_id: str,
        version: int,
        lifecycle_status: str,
    ) -> VersionedRecord | None:
        return next(
            (
                record
                for record in self.records
                if record.user_id == user_id
                and record.entity_type == entity_type
                and record.entity_id == entity_id
                and record.version == version
                and record.lifecycle_status == lifecycle_status
            ),
            None,
        )

    def get_current_committed(
        self,
        user_id: str,
        entity_type: str,
        entity_id: str,
    ) -> VersionedRecord | None:
        committed = [
            record
            for record in self.records
            if record.user_id == user_id
            and record.entity_type == entity_type
            and record.entity_id == entity_id
            and record.lifecycle_status == "committed"
        ]
        if not committed:
            return None
        return max(committed, key=lambda record: record.version)


class ProfilePersistenceTests(unittest.TestCase):
    def test_profile_identity_and_operation_are_m4_safe_commit_values(self) -> None:
        self.assertEqual(PROFILE_ENTITY_TYPE, "profile")
        self.assertEqual(PROFILE_COMMIT_OPERATION, "commit_profile")
        self.assertEqual(profile_entity_id("user_001"), "profile:user_001")

    def test_profile_draft_and_committed_versions_map_to_m3_records(self) -> None:
        records = InMemoryVersionedRecordRepository()
        profiles = ProfileVersionedRecordRepository(records)

        draft = ProfileDraft(
            schema_version=SCHEMA_VERSION,
            user_id="user_001",
            draft_id="profile_draft_001",
            status=DraftStatus.CREATED,
            fields=_profile_fields(),
        )
        profile = ProfileVersion(
            schema_version=SCHEMA_VERSION,
            user_id="user_001",
            profile_id=profile_entity_id("user_001"),
            version=1,
            fields=_profile_fields(),
        )

        profiles.add_draft("profile_draft_record_001", draft, draft_version=1)
        profiles.add_committed(
            "profile_committed_record_001",
            profile,
            confirmation_id="confirm_001",
            idempotency_key="idem_001",
            audit_event_id="audit_001",
        )

        self.assertEqual(len(records.records), 2)
        self.assertEqual(records.records[0].entity_type, "profile")
        self.assertEqual(records.records[0].entity_id, "profile:user_001")
        self.assertEqual(records.records[0].lifecycle_status, "draft")
        self.assertEqual(records.records[1].lifecycle_status, "committed")
        self.assertEqual(
            profiles.get_draft("user_001", 1),
            draft,
        )
        self.assertEqual(
            profiles.get_current_committed("user_001"),
            profile,
        )

    def test_committed_profile_requires_m4_entity_identity(self) -> None:
        records = InMemoryVersionedRecordRepository()
        profiles = ProfileVersionedRecordRepository(records)
        profile = ProfileVersion(
            schema_version=SCHEMA_VERSION,
            user_id="user_001",
            profile_id="profile_001",
            version=1,
            fields=_profile_fields(),
        )

        with self.assertRaisesRegex(ValueError, "profile_id"):
            profiles.add_committed("profile_committed_record_001", profile)


if __name__ == "__main__":
    unittest.main()
