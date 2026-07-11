from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from menu_planner.application.menu_generation import (
    FakeMenuDraftGenerator,
    MenuDraftGenerationRequest,
    MenuDraftGenerator,
)
from menu_planner.application.menu_validation import (
    MenuDraftValidationResult,
    validate_menu_draft_for_context,
)
from menu_planner.domain.contracts.models import JsonObject, MenuDraft
from menu_planner.domain.errors import DomainError

DEFAULT_MAX_REPAIR_ATTEMPTS = 2


class MenuDraftRepairGenerator(Protocol):
    @property
    def name(self) -> str: ...

    @property
    def version(self) -> str: ...

    def generate_repair(
        self,
        *,
        request: MenuDraftGenerationRequest,
        previous_errors: tuple[DomainError, ...],
    ) -> JsonObject: ...


@dataclass(frozen=True)
class RegeneratingMenuDraftRepairGenerator:
    generator: MenuDraftGenerator

    @property
    def name(self) -> str:
        return self.generator.name

    @property
    def version(self) -> str:
        return self.generator.version

    def generate_repair(
        self,
        *,
        request: MenuDraftGenerationRequest,
        previous_errors: tuple[DomainError, ...],
    ) -> JsonObject:
        return self.generator.generate(request)


@dataclass(frozen=True)
class MenuDraftRepairAttempt:
    attempt_number: int
    generator_name: str
    generator_version: str
    ok: bool
    error_count: int
    error_codes: tuple[str, ...]
    error_paths: tuple[tuple[str | int, ...], ...]
    side_effects_executed: bool = False


@dataclass(frozen=True)
class MenuDraftRepairLoopResult:
    validation: MenuDraftValidationResult
    draft: MenuDraft | None
    errors: tuple[DomainError, ...]
    attempts: tuple[MenuDraftRepairAttempt, ...]
    max_attempts: int
    side_effects_executed: bool = False
    confirmed_state_changed: bool = False

    @property
    def ok(self) -> bool:
        return self.draft is not None and self.validation.ok and not self.errors


def repair_menu_draft(
    *,
    request: MenuDraftGenerationRequest,
    max_attempts: int = DEFAULT_MAX_REPAIR_ATTEMPTS,
    repair_generator: MenuDraftRepairGenerator | None = None,
) -> MenuDraftRepairLoopResult:
    if max_attempts < 1:
        raise ValueError("max_attempts must be at least 1")

    selected_generator: MenuDraftRepairGenerator = (
        repair_generator
        or RegeneratingMenuDraftRepairGenerator(FakeMenuDraftGenerator())
    )
    previous_errors: tuple[DomainError, ...] = ()
    attempts: list[MenuDraftRepairAttempt] = []
    last_validation: MenuDraftValidationResult | None = None

    for attempt_number in range(1, max_attempts + 1):
        payload = selected_generator.generate_repair(
            request=request,
            previous_errors=previous_errors,
        )
        validation = validate_menu_draft_for_context(
            draft=payload,
            planning_context=request.planning_context,
        )
        attempts.append(
            _attempt_metadata(
                attempt_number=attempt_number,
                generator=selected_generator,
                validation=validation,
            )
        )
        last_validation = validation
        if validation.ok and validation.draft is not None:
            return MenuDraftRepairLoopResult(
                validation=validation,
                draft=validation.draft,
                errors=(),
                attempts=tuple(attempts),
                max_attempts=max_attempts,
            )
        previous_errors = validation.errors

    if last_validation is None:
        raise AssertionError("repair loop must execute at least one attempt")
    return MenuDraftRepairLoopResult(
        validation=last_validation,
        draft=None,
        errors=last_validation.errors,
        attempts=tuple(attempts),
        max_attempts=max_attempts,
    )


def _attempt_metadata(
    *,
    attempt_number: int,
    generator: MenuDraftRepairGenerator,
    validation: MenuDraftValidationResult,
) -> MenuDraftRepairAttempt:
    return MenuDraftRepairAttempt(
        attempt_number=attempt_number,
        generator_name=generator.name,
        generator_version=generator.version,
        ok=validation.ok,
        error_count=len(validation.errors),
        error_codes=tuple(error.code.value for error in validation.errors),
        error_paths=tuple(error.path for error in validation.errors),
    )
