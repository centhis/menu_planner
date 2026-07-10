from __future__ import annotations

from typing import cast

from menu_planner.application.safe_commit import (
    VersionedRecord,
    VersionedRecordRepository,
)
from menu_planner.domain.contracts.models import (
    JsonObject,
    ProfileDraft,
    ProfileVersion,
)
from menu_planner.domain.contracts.validation import validate_contract

PROFILE_ENTITY_TYPE = "profile"
PROFILE_COMMIT_OPERATION = "commit_profile"


def profile_entity_id(user_id: str) -> str:
    return f"profile:{user_id}"


class ProfileVersionedRecordRepository:
    def __init__(self, records: VersionedRecordRepository) -> None:
        self._records = records

    def add_draft(
        self,
        record_id: str,
        draft: ProfileDraft,
        draft_version: int,
    ) -> None:
        self._records.add(
            VersionedRecord(
                record_id=record_id,
                user_id=draft.user_id,
                entity_type=PROFILE_ENTITY_TYPE,
                entity_id=profile_entity_id(draft.user_id),
                version=draft_version,
                lifecycle_status="draft",
                payload=_profile_draft_payload(draft),
            )
        )

    def get_draft(self, user_id: str, draft_version: int) -> ProfileDraft | None:
        record = self._records.get(
            user_id,
            PROFILE_ENTITY_TYPE,
            profile_entity_id(user_id),
            draft_version,
            "draft",
        )
        if record is None:
            return None
        return _profile_draft_from_record(record)

    def add_committed(
        self,
        record_id: str,
        profile: ProfileVersion,
        *,
        confirmation_id: str | None = None,
        idempotency_key: str | None = None,
        audit_event_id: str | None = None,
    ) -> None:
        if profile.profile_id != profile_entity_id(profile.user_id):
            raise ValueError("profile_id must match M4 profile entity identity")

        self._records.add(
            VersionedRecord(
                record_id=record_id,
                user_id=profile.user_id,
                entity_type=PROFILE_ENTITY_TYPE,
                entity_id=profile.profile_id,
                version=profile.version,
                lifecycle_status="committed",
                payload=_profile_version_payload(profile),
                confirmation_id=confirmation_id,
                idempotency_key=idempotency_key,
                audit_event_id=audit_event_id,
            )
        )

    def get_committed(
        self,
        user_id: str,
        version: int,
    ) -> ProfileVersion | None:
        record = self._records.get(
            user_id,
            PROFILE_ENTITY_TYPE,
            profile_entity_id(user_id),
            version,
            "committed",
        )
        if record is None:
            return None
        return _profile_version_from_record(record)

    def get_current_committed(self, user_id: str) -> ProfileVersion | None:
        record = self._records.get_current_committed(
            user_id,
            PROFILE_ENTITY_TYPE,
            profile_entity_id(user_id),
        )
        if record is None:
            return None
        return _profile_version_from_record(record)


def _profile_draft_payload(draft: ProfileDraft) -> JsonObject:
    return {
        "schema_version": draft.schema_version,
        "user_id": draft.user_id,
        "draft_id": draft.draft_id,
        "status": draft.status.value,
        "fields": draft.fields,
    }


def _profile_version_payload(profile: ProfileVersion) -> JsonObject:
    return {
        "schema_version": profile.schema_version,
        "user_id": profile.user_id,
        "profile_id": profile.profile_id,
        "version": profile.version,
        "fields": profile.fields,
    }


def _profile_draft_from_record(record: VersionedRecord) -> ProfileDraft:
    _ensure_profile_record(record, "draft")
    result = validate_contract("profile_draft", record.payload)
    if not result.is_valid or result.value is None:
        raise ValueError("stored profile draft failed domain validation")
    return cast(ProfileDraft, result.value)


def _profile_version_from_record(record: VersionedRecord) -> ProfileVersion:
    _ensure_profile_record(record, "committed")
    payload = _committed_profile_payload(record)
    result = validate_contract("profile_version", payload)
    if not result.is_valid or result.value is None:
        raise ValueError("stored profile version failed domain validation")
    return cast(ProfileVersion, result.value)


def _committed_profile_payload(record: VersionedRecord) -> JsonObject:
    if "profile_id" in record.payload and "version" in record.payload:
        return record.payload
    return {
        "schema_version": record.payload.get("schema_version"),
        "user_id": record.user_id,
        "profile_id": record.entity_id,
        "version": record.version,
        "fields": record.payload.get("fields"),
    }


def _ensure_profile_record(record: VersionedRecord, lifecycle_status: str) -> None:
    if record.entity_type != PROFILE_ENTITY_TYPE:
        raise ValueError("record is not a profile record")
    if record.lifecycle_status != lifecycle_status:
        raise ValueError("record lifecycle status does not match profile mapping")
