from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from menu_planner.application.profile_persistence import (
    PROFILE_COMMIT_OPERATION,
    PROFILE_ENTITY_TYPE,
    ProfileVersionedRecordRepository,
    profile_entity_id,
)
from menu_planner.application.safe_commit import (
    ConfirmationLifecycle,
    ConfirmationRecord,
    ConfirmationRequest,
    OperationPreviewInput,
    SafeCommitCommand,
    SafeCommitOrchestrator,
    SafeCommitResult,
    SafeCommitUnitOfWork,
    VersionedRecord,
    build_operation_preview,
)
from menu_planner.domain.contracts.models import (
    SCHEMA_VERSION,
    DraftStatus,
    JsonObject,
    OperationClass,
    OperationPreview,
    ParsedIntent,
    PolicyDecision,
    ProfileDraft,
    ProfileVersion,
    WorkflowRun,
)
from menu_planner.domain.contracts.validation import (
    ContractValidationResult,
    validate_contract,
)
from menu_planner.domain.errors import DomainError
from menu_planner.domain.policy import decide_policy
from menu_planner.domain.workflow import WorkflowAction


@dataclass(frozen=True)
class SaveProfileDraftCommand:
    record_id: str
    user_id: str
    draft_id: str
    draft_version: int
    fields: JsonObject
    workflow: WorkflowRun
    status: DraftStatus = DraftStatus.CREATED


@dataclass(frozen=True)
class CreateProfilePreviewCommand:
    preview_id: str
    user_id: str
    draft_version: int
    workflow: WorkflowRun


@dataclass(frozen=True)
class CreateProfileConfirmationCommand:
    confirmation_id: str
    user_id: str
    draft_version: int
    expected_version: int
    expires_at: datetime
    summary_hash: str
    workflow: WorkflowRun


@dataclass(frozen=True)
class ConfirmProfileCommitCommand:
    confirmation_id: str
    user_id: str
    summary_hash: str
    now: datetime
    workflow: WorkflowRun


@dataclass(frozen=True)
class CommitProfileCommand:
    confirmation_id: str
    idempotency_record_id: str
    committed_record_id: str
    audit_event_id: str
    user_id: str
    expected_version: int
    draft_version: int
    summary_hash: str
    idempotency_key: str
    now: datetime
    workflow: WorkflowRun


@dataclass(frozen=True)
class ProfileCommandResult:
    profile_draft: ProfileDraft | None = None
    profile_version: ProfileVersion | None = None
    preview: OperationPreview | None = None
    confirmation: ConfirmationRecord | None = None
    safe_commit: SafeCommitResult | None = None
    policy: PolicyDecision | None = None
    validation: ContractValidationResult | None = None
    error: DomainError | None = None

    @property
    def ok(self) -> bool:
        if self.policy is not None and not self.policy.allowed:
            return False
        if self.validation is not None and not self.validation.is_valid:
            return False
        if self.safe_commit is not None and not self.safe_commit.ok:
            return False
        if self.error is not None:
            return False
        return True


class ProfileApplicationService:
    def __init__(
        self,
        unit_of_work_factory: Callable[[], SafeCommitUnitOfWork],
    ) -> None:
        self._unit_of_work_factory = unit_of_work_factory
        self._safe_commit = SafeCommitOrchestrator(unit_of_work_factory)

    def save_draft(self, command: SaveProfileDraftCommand) -> ProfileCommandResult:
        policy = _policy_for(command.workflow, WorkflowAction.SUBMIT_PROFILE_DRAFT)
        if not policy.allowed:
            return ProfileCommandResult(policy=policy)

        draft = ProfileDraft(
            schema_version=SCHEMA_VERSION,
            user_id=command.user_id,
            draft_id=command.draft_id,
            status=command.status,
            fields=command.fields,
        )
        validation = validate_contract("profile_draft", _profile_draft_payload(draft))
        if not validation.is_valid:
            return ProfileCommandResult(profile_draft=draft, validation=validation)

        with self._unit_of_work_factory() as unit_of_work:
            profiles = ProfileVersionedRecordRepository(unit_of_work.versioned_records)
            profiles.add_draft(command.record_id, draft, command.draft_version)
            unit_of_work.commit()

        return ProfileCommandResult(profile_draft=draft, policy=policy)

    def validate_draft(self, draft: ProfileDraft) -> ContractValidationResult:
        return validate_contract("profile_draft", _profile_draft_payload(draft))

    def create_preview(
        self,
        command: CreateProfilePreviewCommand,
    ) -> ProfileCommandResult:
        policy = _policy_for(command.workflow, WorkflowAction.SUBMIT_PROFILE_DRAFT)
        if not policy.allowed:
            return ProfileCommandResult(policy=policy)

        with self._unit_of_work_factory() as unit_of_work:
            profiles = ProfileVersionedRecordRepository(unit_of_work.versioned_records)
            draft = profiles.get_draft(command.user_id, command.draft_version)
            current = profiles.get_current_committed(command.user_id)
            unit_of_work.rollback()

        if draft is None:
            missing = validate_contract("profile_draft", {})
            return ProfileCommandResult(policy=policy, validation=missing)

        expected_version = current.version if current is not None else 0
        preview_input = OperationPreviewInput(
            preview_id=command.preview_id,
            operation=PROFILE_COMMIT_OPERATION,
            user_id=command.user_id,
            entity_type=PROFILE_ENTITY_TYPE,
            entity_id=profile_entity_id(command.user_id),
            expected_version=expected_version,
            draft_version=command.draft_version,
            committed_relevant_payload=_profile_version_payload(
                ProfileVersion(
                    schema_version=SCHEMA_VERSION,
                    user_id=command.user_id,
                    profile_id=profile_entity_id(command.user_id),
                    version=command.draft_version,
                    fields=draft.fields,
                )
            ),
            changes=[
                {
                    "kind": "profile_commit",
                    "summary": "Commit M4 profile draft",
                    "draft_id": draft.draft_id,
                    "draft_version": command.draft_version,
                    "expected_version": expected_version,
                }
            ],
        )
        return ProfileCommandResult(
            profile_draft=draft,
            preview=build_operation_preview(preview_input),
            policy=policy,
        )

    def create_confirmation(
        self,
        command: CreateProfileConfirmationCommand,
    ) -> ProfileCommandResult:
        policy = _policy_for(command.workflow, WorkflowAction.CONFIRM_PROFILE_DRAFT)
        if not policy.allowed:
            return ProfileCommandResult(policy=policy)

        confirmation = ConfirmationRecord(
            confirmation_id=command.confirmation_id,
            user_id=command.user_id,
            operation=PROFILE_COMMIT_OPERATION,
            entity_type=PROFILE_ENTITY_TYPE,
            entity_id=profile_entity_id(command.user_id),
            expected_version=command.expected_version,
            draft_version=command.draft_version,
            expires_at=command.expires_at,
            summary_hash=command.summary_hash,
            status="pending",
        )
        with self._unit_of_work_factory() as unit_of_work:
            lifecycle = ConfirmationLifecycle(unit_of_work.confirmations)
            created = lifecycle.create_pending(confirmation)
            unit_of_work.commit()

        return ProfileCommandResult(confirmation=created, policy=policy)

    def confirm_profile_commit(
        self,
        command: ConfirmProfileCommitCommand,
    ) -> ProfileCommandResult:
        policy = _policy_for(command.workflow, WorkflowAction.CONFIRM_PROFILE_DRAFT)
        if not policy.allowed:
            return ProfileCommandResult(policy=policy)

        with self._unit_of_work_factory() as unit_of_work:
            lifecycle = ConfirmationLifecycle(unit_of_work.confirmations)
            result = lifecycle.confirm(
                ConfirmationRequest(
                    confirmation_id=command.confirmation_id,
                    user_id=command.user_id,
                    operation=PROFILE_COMMIT_OPERATION,
                    entity_type=PROFILE_ENTITY_TYPE,
                    entity_id=profile_entity_id(command.user_id),
                    summary_hash=command.summary_hash,
                    now=command.now,
                )
            )
            unit_of_work.commit()

        return ProfileCommandResult(
            confirmation=result.confirmation,
            policy=policy,
            error=result.error,
        )

    def commit_profile(self, command: CommitProfileCommand) -> ProfileCommandResult:
        policy = _policy_for(command.workflow, WorkflowAction.CONFIRM_PROFILE_DRAFT)
        if not policy.allowed:
            return ProfileCommandResult(policy=policy)

        safe_commit = self._safe_commit.commit(
            SafeCommitCommand(
                confirmation_id=command.confirmation_id,
                idempotency_record_id=command.idempotency_record_id,
                committed_record_id=command.committed_record_id,
                audit_event_id=command.audit_event_id,
                user_id=command.user_id,
                operation=PROFILE_COMMIT_OPERATION,
                entity_type=PROFILE_ENTITY_TYPE,
                entity_id=profile_entity_id(command.user_id),
                expected_version=command.expected_version,
                draft_version=command.draft_version,
                summary_hash=command.summary_hash,
                idempotency_key=command.idempotency_key,
                now=command.now,
            )
        )
        profile_version = None
        if safe_commit.committed_record is not None:
            profile_version = ProfileVersionedRecordRepository(
                _SingleRecordRepository(safe_commit.committed_record)
            ).get_committed(command.user_id, command.draft_version)
        return ProfileCommandResult(
            profile_version=profile_version,
            safe_commit=safe_commit,
            policy=policy,
        )

    def get_current_profile(self, user_id: str) -> ProfileVersion | None:
        with self._unit_of_work_factory() as unit_of_work:
            profiles = ProfileVersionedRecordRepository(unit_of_work.versioned_records)
            profile = profiles.get_current_committed(user_id)
            unit_of_work.rollback()
        return profile

    def get_workflow_status(self, workflow: WorkflowRun) -> PolicyDecision:
        return _policy_for(workflow, WorkflowAction.SHOW_STATUS)


def _policy_for(workflow: WorkflowRun, action: WorkflowAction) -> PolicyDecision:
    return decide_policy(_intent_for_action(action), workflow)


def _intent_for_action(action: WorkflowAction) -> ParsedIntent:
    return ParsedIntent(
        schema_version=SCHEMA_VERSION,
        intent=action.value,
        confidence=1.0,
        parameters={},
        missing_fields=[],
        ambiguities=[],
        operation_class=OperationClass.READ_ONLY,
        requires_confirmation=False,
        scope="m4_profile",
        suggested_next_action=action.value,
    )


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


class _SingleRecordRepository:
    def __init__(self, record: VersionedRecord) -> None:
        self._record = record

    def add(self, record: VersionedRecord) -> None:
        raise NotImplementedError

    def get(
        self,
        user_id: str,
        entity_type: str,
        entity_id: str,
        version: int,
        lifecycle_status: str,
    ) -> VersionedRecord | None:
        if (
            self._record.user_id == user_id
            and self._record.entity_type == entity_type
            and self._record.entity_id == entity_id
            and self._record.version == version
            and self._record.lifecycle_status == lifecycle_status
        ):
            return self._record
        return None

    def get_current_committed(
        self,
        user_id: str,
        entity_type: str,
        entity_id: str,
    ) -> VersionedRecord | None:
        return self.get(
            user_id,
            entity_type,
            entity_id,
            self._record.version,
            "committed",
        )
