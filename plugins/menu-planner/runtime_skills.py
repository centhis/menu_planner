"""Versioned runtime skills packaged with the Menu Planner Hermes plugin."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

SKILL_VERSION = "m8.v1"
SKILLS_ROOT = Path(__file__).resolve().parent / "skills"


@dataclass(frozen=True)
class RuntimeSkill:
    name: str
    path: Path
    description: str


def all_runtime_skills() -> tuple[RuntimeSkill, ...]:
    return (
        _skill(
            "intent-interpretation-v1",
            "Interpret user intent and choose among structured Menu Planner tools.",
        ),
        _skill(
            "clarification-v1",
            "Ask bounded clarification questions when structured inputs are missing.",
        ),
        _skill(
            "menu-generation-v1",
            "Use structured menu draft tools without bypassing validation.",
        ),
        _skill(
            "validation-repair-v1",
            "Repair local draft payloads from validation errors before retry.",
        ),
        _skill(
            "preview-explanation-v1",
            "Explain previews and confirmations from structured tool results.",
        ),
    )


def register_runtime_skills(ctx) -> None:
    for skill in all_runtime_skills():
        ctx.register_skill(
            name=skill.name,
            path=str(skill.path),
            description=skill.description,
        )


def _skill(name: str, description: str) -> RuntimeSkill:
    return RuntimeSkill(
        name=name,
        path=SKILLS_ROOT / name / "SKILL.md",
        description=description,
    )
