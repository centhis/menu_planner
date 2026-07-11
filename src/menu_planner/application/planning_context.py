from __future__ import annotations

from dataclasses import dataclass
from typing import cast

from menu_planner.domain.contracts.models import (
    SCHEMA_VERSION,
    JsonObject,
    JsonValue,
    PlanningContext,
    ProfileVersion,
)
from menu_planner.domain.contracts.validation import (
    ContractValidationResult,
    validate_contract,
)
from menu_planner.domain.errors import DomainError, ownership_required


@dataclass(frozen=True)
class PlanningMealSlotRequest:
    slot_id: str
    date: str
    meal_type: str
    requirements: JsonObject


@dataclass(frozen=True)
class BuildPlanningContextRequest:
    planning_request_id: str
    user_id: str
    context_id: str
    period_start: str
    period_end: str
    meal_slots: tuple[PlanningMealSlotRequest, ...]


@dataclass(frozen=True)
class PlanningContextBuildResult:
    context: PlanningContext | None
    validation: ContractValidationResult
    errors: tuple[DomainError, ...]

    @property
    def ok(self) -> bool:
        return self.context is not None and self.validation.is_valid and not self.errors


def build_planning_context(
    *,
    confirmed_profile: ProfileVersion,
    request: BuildPlanningContextRequest,
) -> PlanningContextBuildResult:
    profile_validation = validate_contract(
        "profile_version",
        _profile_version_payload(confirmed_profile),
    )
    if not profile_validation.is_valid:
        return PlanningContextBuildResult(
            context=None,
            validation=profile_validation,
            errors=profile_validation.errors,
        )
    if confirmed_profile.user_id != request.user_id:
        return PlanningContextBuildResult(
            context=None,
            validation=profile_validation,
            errors=(
                ownership_required(
                    confirmed_profile.profile_id,
                    request.user_id,
                ),
            ),
        )

    profile_fields = confirmed_profile.fields
    user_facts = cast(JsonObject, profile_fields["user_facts"])
    context_payload = _planning_context_payload(
        confirmed_profile=confirmed_profile,
        request=request,
        constraints={
            "profile_id": confirmed_profile.profile_id,
            "strict_restrictions": profile_fields["strict_restrictions"],
            "available_equipment": user_facts["available_equipment"],
            "max_active_time_minutes": user_facts[
                "default_max_active_time_minutes"
            ],
        },
    )
    context_validation = validate_contract("planning_context", context_payload)
    if not context_validation.is_valid or context_validation.value is None:
        return PlanningContextBuildResult(
            context=None,
            validation=context_validation,
            errors=context_validation.errors,
        )

    return PlanningContextBuildResult(
        context=cast(PlanningContext, context_validation.value),
        validation=context_validation,
        errors=(),
    )


def _profile_version_payload(profile: ProfileVersion) -> JsonObject:
    return {
        "schema_version": profile.schema_version,
        "user_id": profile.user_id,
        "profile_id": profile.profile_id,
        "version": profile.version,
        "fields": profile.fields,
    }


def _planning_context_payload(
    *,
    confirmed_profile: ProfileVersion,
    request: BuildPlanningContextRequest,
    constraints: JsonObject,
) -> JsonObject:
    return {
        "schema_version": SCHEMA_VERSION,
        "user_id": request.user_id,
        "context_id": request.context_id,
        "profile_version": confirmed_profile.version,
        "planning_request_id": request.planning_request_id,
        "period_start": request.period_start,
        "period_end": request.period_end,
        "meal_slots": cast(
            JsonValue,
            [
                {
                    "schema_version": SCHEMA_VERSION,
                    "slot_id": slot.slot_id,
                    "date": slot.date,
                    "meal_type": slot.meal_type,
                    "requirements": slot.requirements,
                }
                for slot in request.meal_slots
            ],
        ),
        "constraints": constraints,
    }
