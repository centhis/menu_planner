from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import cast

from menu_planner.application.recipe_validation import RecipeDraftValidationResult
from menu_planner.application.safe_commit import (
    AuditEventRecord,
    SafeCommitUnitOfWork,
    VersionedRecord,
    VersionedRecordRepository,
)
from menu_planner.domain.contracts.models import JsonObject, JsonValue, RecipeVersion
from menu_planner.domain.contracts.validation import validate_contract
from menu_planner.domain.errors import DomainError

RECIPE_ENTITY_TYPE = "recipe"
RECIPE_PERSIST_OPERATION = "persist_recipe_version"


def recipe_entity_id(
    user_id: str,
    source_menu_id: str,
    source_meal_slot_id: str,
) -> str:
    return f"recipe:{user_id}:{source_menu_id}:{source_meal_slot_id}"


@dataclass(frozen=True)
class SaveRecipeVersionCommand:
    record_id: str
    audit_event_id: str
    recipe_id: str
    version: int
    validation: RecipeDraftValidationResult


@dataclass(frozen=True)
class SaveRecipeVersionResult:
    recipe_version: RecipeVersion | None
    errors: tuple[DomainError, ...] = ()
    audit_event: AuditEventRecord | None = None
    side_effects_executed: bool = False
    active_menu_changed: bool = False

    @property
    def ok(self) -> bool:
        return self.recipe_version is not None and not self.errors


class RecipeVersionedRecordRepository:
    def __init__(self, records: VersionedRecordRepository) -> None:
        self._records = records

    def add_version(
        self,
        record_id: str,
        recipe: RecipeVersion,
        *,
        audit_event_id: str | None = None,
    ) -> None:
        self._records.add(
            VersionedRecord(
                record_id=record_id,
                user_id=recipe.user_id,
                entity_type=RECIPE_ENTITY_TYPE,
                entity_id=recipe.recipe_id,
                version=recipe.version,
                lifecycle_status="committed",
                payload=_recipe_version_payload(recipe),
                audit_event_id=audit_event_id,
            )
        )

    def get_version(
        self,
        user_id: str,
        recipe_id: str,
        version: int,
    ) -> RecipeVersion | None:
        record = self._records.get(
            user_id,
            RECIPE_ENTITY_TYPE,
            recipe_id,
            version,
            "committed",
        )
        if record is None:
            return None
        return _recipe_version_from_record(record)

    def get_current_version(
        self,
        user_id: str,
        recipe_id: str,
    ) -> RecipeVersion | None:
        record = self._records.get_current_committed(
            user_id,
            RECIPE_ENTITY_TYPE,
            recipe_id,
        )
        if record is None:
            return None
        return _recipe_version_from_record(record)


class RecipePersistenceService:
    def __init__(
        self,
        unit_of_work_factory: Callable[[], SafeCommitUnitOfWork],
    ) -> None:
        self._unit_of_work_factory = unit_of_work_factory

    def save_validated_recipe_version(
        self,
        command: SaveRecipeVersionCommand,
    ) -> SaveRecipeVersionResult:
        validation = command.validation
        if not validation.can_persist_valid_version or validation.draft is None:
            return SaveRecipeVersionResult(
                recipe_version=None,
                errors=validation.errors,
            )

        draft = validation.draft
        recipe = RecipeVersion(
            schema_version=draft.schema_version,
            user_id=draft.user_id,
            recipe_id=command.recipe_id,
            version=command.version,
            source_menu_id=draft.source_menu_id,
            source_menu_version=draft.source_menu_version,
            source_meal_slot_id=draft.source_meal_slot_id,
            title=draft.title,
            portions=draft.portions,
            ingredients=draft.ingredients,
            equipment=draft.equipment,
            active_time_minutes=draft.active_time_minutes,
            total_time_minutes=draft.total_time_minutes,
            steps=draft.steps,
            storage=draft.storage,
            reheating=draft.reheating,
        )
        audit_event = AuditEventRecord(
            audit_event_id=command.audit_event_id,
            user_id=recipe.user_id,
            operation=RECIPE_PERSIST_OPERATION,
            entity_type=RECIPE_ENTITY_TYPE,
            entity_id=recipe.recipe_id,
            result_status="success",
            new_version=recipe.version,
            event_metadata={
                "draft_id": draft.draft_id,
                "source_menu_id": draft.source_menu_id,
                "source_meal_slot_id": draft.source_meal_slot_id,
            },
        )

        with self._unit_of_work_factory() as unit_of_work:
            try:
                recipes = RecipeVersionedRecordRepository(
                    unit_of_work.versioned_records
                )
                unit_of_work.audit_events.add(audit_event)
                recipes.add_version(
                    command.record_id,
                    recipe,
                    audit_event_id=command.audit_event_id,
                )
                unit_of_work.commit()
            except Exception:
                unit_of_work.rollback()
                raise

        return SaveRecipeVersionResult(
            recipe_version=recipe,
            audit_event=audit_event,
            side_effects_executed=True,
        )


def _recipe_version_payload(recipe: RecipeVersion) -> JsonObject:
    return {
        "schema_version": recipe.schema_version,
        "user_id": recipe.user_id,
        "recipe_id": recipe.recipe_id,
        "version": recipe.version,
        "source_menu_id": recipe.source_menu_id,
        "source_menu_version": recipe.source_menu_version,
        "source_meal_slot_id": recipe.source_meal_slot_id,
        "title": recipe.title,
        "portions": recipe.portions,
        "ingredients": cast(JsonValue, recipe.ingredients),
        "equipment": cast(JsonValue, recipe.equipment),
        "active_time_minutes": recipe.active_time_minutes,
        "total_time_minutes": recipe.total_time_minutes,
        "steps": cast(JsonValue, recipe.steps),
        "storage": recipe.storage,
        "reheating": recipe.reheating,
    }


def _recipe_version_from_record(record: VersionedRecord) -> RecipeVersion:
    _ensure_recipe_record(record)
    result = validate_contract("recipe_version", record.payload)
    if not result.is_valid or result.value is None:
        raise ValueError("stored recipe version failed domain validation")
    return cast(RecipeVersion, result.value)


def _ensure_recipe_record(record: VersionedRecord) -> None:
    if record.entity_type != RECIPE_ENTITY_TYPE:
        raise ValueError("record is not a recipe record")
    if record.lifecycle_status != "committed":
        raise ValueError("record lifecycle status does not match recipe mapping")
