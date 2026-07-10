from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from menu_planner.application.profile_persistence import (
    ProfileVersionedRecordRepository,
)
from menu_planner.application.profile_service import (
    CommitProfileCommand,
    ConfirmProfileCommitCommand,
    CreateProfileConfirmationCommand,
    CreateProfilePreviewCommand,
    ProfileApplicationService,
    ProfileCommandResult,
    SaveProfileDraftCommand,
)
from menu_planner.application.safe_commit import (
    ConfirmationRecord,
    SafeCommitUnitOfWork,
)
from menu_planner.domain.contracts.models import (
    SCHEMA_VERSION,
    JsonObject,
    OperationPreview,
    ProfileDraft,
    ProfileVersion,
    WorkflowRun,
    WorkflowState,
)
from menu_planner.domain.contracts.validation import ContractValidationResult
from menu_planner.domain.workflow import allowed_actions


@dataclass(frozen=True)
class ProfileScenarioIds:
    run_id: str
    idempotency_key: str
    draft_version: int = 1

    @property
    def draft_record_id(self) -> str:
        return f"{self.run_id}:profile_draft_record:{self.draft_version}"

    @property
    def draft_id(self) -> str:
        return f"{self.run_id}:profile_draft:{self.draft_version}"

    @property
    def preview_id(self) -> str:
        return f"{self.run_id}:profile_preview:{self.draft_version}"

    @property
    def confirmation_id(self) -> str:
        return f"{self.run_id}:profile_confirmation:{self.draft_version}"

    @property
    def idempotency_record_id(self) -> str:
        return f"{self.run_id}:profile_idempotency:{self.draft_version}"

    @property
    def committed_record_id(self) -> str:
        return f"{self.run_id}:profile_committed_record:{self.draft_version}"

    @property
    def audit_event_id(self) -> str:
        return f"{self.run_id}:profile_audit:{self.draft_version}"


@dataclass(frozen=True)
class ProfileScenarioResult:
    save_result: ProfileCommandResult | None
    validation: ContractValidationResult | None
    preview: OperationPreview | None
    confirmation: ConfirmationRecord | None
    confirm_result: ProfileCommandResult | None
    commit_result: ProfileCommandResult | None
    current_profile: ProfileVersion | None
    reused_draft: bool
    reused_confirmation: bool

    @property
    def replayed(self) -> bool:
        return (
            self.commit_result is not None
            and self.commit_result.safe_commit is not None
            and self.commit_result.safe_commit.replay
        )

    @property
    def ok(self) -> bool:
        if self.validation is None or not self.validation.is_valid:
            return False
        if self.current_profile is None:
            return False
        if self.commit_result is None:
            return False
        if self.commit_result.ok:
            return True
        return self.replayed


def m4_profile_fields() -> JsonObject:
    """Return the experimental M4 profile shape from ADR-0006."""

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


def run_m4_profile_scenario(
    *,
    service: ProfileApplicationService,
    unit_of_work_factory: Callable[[], SafeCommitUnitOfWork],
    user_id: str,
    ids: ProfileScenarioIds,
    now: datetime,
    expires_at: datetime,
    fields: JsonObject | None = None,
) -> ProfileScenarioResult:
    draft = _get_draft(unit_of_work_factory, user_id, ids.draft_version)
    save_result = None
    reused_draft = draft is not None
    if draft is None:
        save_result = service.save_draft(
            SaveProfileDraftCommand(
                record_id=ids.draft_record_id,
                user_id=user_id,
                draft_id=ids.draft_id,
                draft_version=ids.draft_version,
                fields=fields or m4_profile_fields(),
                workflow=_workflow(user_id, WorkflowState.PROFILE_REQUIRED),
            )
        )
        if not save_result.ok or save_result.profile_draft is None:
            return ProfileScenarioResult(
                save_result=save_result,
                validation=save_result.validation,
                preview=None,
                confirmation=None,
                confirm_result=None,
                commit_result=None,
                current_profile=service.get_current_profile(user_id),
                reused_draft=reused_draft,
                reused_confirmation=False,
            )
        draft = save_result.profile_draft

    validation = service.validate_draft(draft)
    if not validation.is_valid:
        return ProfileScenarioResult(
            save_result=save_result,
            validation=validation,
            preview=None,
            confirmation=None,
            confirm_result=None,
            commit_result=None,
            current_profile=service.get_current_profile(user_id),
            reused_draft=reused_draft,
            reused_confirmation=False,
        )

    confirmation = _get_confirmation(
        unit_of_work_factory,
        ids.confirmation_id,
        user_id,
    )
    reused_confirmation = confirmation is not None
    preview = None
    if confirmation is None:
        preview_result = service.create_preview(
            CreateProfilePreviewCommand(
                preview_id=ids.preview_id,
                user_id=user_id,
                draft_version=ids.draft_version,
                workflow=_workflow(user_id, WorkflowState.PROFILE_REQUIRED),
            )
        )
        if not preview_result.ok or preview_result.preview is None:
            return ProfileScenarioResult(
                save_result=save_result,
                validation=validation,
                preview=None,
                confirmation=None,
                confirm_result=None,
                commit_result=None,
                current_profile=service.get_current_profile(user_id),
                reused_draft=reused_draft,
                reused_confirmation=False,
            )
        preview = preview_result.preview
        confirmation_result = service.create_confirmation(
            CreateProfileConfirmationCommand(
                confirmation_id=ids.confirmation_id,
                user_id=user_id,
                draft_version=ids.draft_version,
                expected_version=_expected_version(preview),
                expires_at=expires_at,
                summary_hash=preview.summary_hash,
                workflow=_workflow(
                    user_id,
                    WorkflowState.PROFILE_WAITING_CONFIRMATION,
                ),
            )
        )
        confirmation = confirmation_result.confirmation
        if not confirmation_result.ok or confirmation is None:
            return ProfileScenarioResult(
                save_result=save_result,
                validation=validation,
                preview=preview,
                confirmation=confirmation,
                confirm_result=None,
                commit_result=None,
                current_profile=service.get_current_profile(user_id),
                reused_draft=reused_draft,
                reused_confirmation=False,
            )

    confirm_result = None
    if confirmation.status == "pending":
        confirm_result = service.confirm_profile_commit(
            ConfirmProfileCommitCommand(
                confirmation_id=confirmation.confirmation_id,
                user_id=user_id,
                summary_hash=confirmation.summary_hash,
                now=now,
                workflow=_workflow(
                    user_id,
                    WorkflowState.PROFILE_WAITING_CONFIRMATION,
                ),
            )
        )
        if confirm_result.confirmation is not None:
            confirmation = confirm_result.confirmation

    commit_result = service.commit_profile(
        CommitProfileCommand(
            confirmation_id=confirmation.confirmation_id,
            idempotency_record_id=ids.idempotency_record_id,
            committed_record_id=ids.committed_record_id,
            audit_event_id=ids.audit_event_id,
            user_id=user_id,
            expected_version=confirmation.expected_version,
            draft_version=confirmation.draft_version,
            summary_hash=confirmation.summary_hash,
            idempotency_key=ids.idempotency_key,
            now=now,
            workflow=_workflow(user_id, WorkflowState.PROFILE_WAITING_CONFIRMATION),
        )
    )
    current_profile = service.get_current_profile(user_id)
    return ProfileScenarioResult(
        save_result=save_result,
        validation=validation,
        preview=preview,
        confirmation=confirmation,
        confirm_result=confirm_result,
        commit_result=commit_result,
        current_profile=current_profile,
        reused_draft=reused_draft,
        reused_confirmation=reused_confirmation,
    )


def _workflow(user_id: str, state: WorkflowState) -> WorkflowRun:
    return WorkflowRun(
        schema_version=SCHEMA_VERSION,
        workflow_id=f"m4_profile_scenario:{user_id}:{state.value}",
        user_id=user_id,
        state=state,
        allowed_actions=[action.value for action in allowed_actions(state)],
        attempts=0,
    )


def _get_draft(
    unit_of_work_factory: Callable[[], SafeCommitUnitOfWork],
    user_id: str,
    draft_version: int,
) -> ProfileDraft | None:
    with unit_of_work_factory() as unit_of_work:
        profiles = ProfileVersionedRecordRepository(unit_of_work.versioned_records)
        draft = profiles.get_draft(user_id, draft_version)
        unit_of_work.rollback()
        return draft


def _get_confirmation(
    unit_of_work_factory: Callable[[], SafeCommitUnitOfWork],
    confirmation_id: str,
    user_id: str,
) -> ConfirmationRecord | None:
    with unit_of_work_factory() as unit_of_work:
        confirmation = unit_of_work.confirmations.get_for_user(
            confirmation_id,
            user_id,
        )
        unit_of_work.rollback()
        return confirmation


def _expected_version(preview: OperationPreview) -> int:
    for change in preview.changes:
        value = change.get("expected_version")
        if isinstance(value, int):
            return value
    return 0
