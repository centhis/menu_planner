#!/usr/bin/env python3
"""Live Telegram UX sandbox shell for Stage 10.5."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import time
from typing import Any

CALLBACK_HOME = "cl:<clarify_id>:0"
CALLBACK_STATUS = "cl:<clarify_id>:0"
CALLBACK_PREFIX = "cl:"
HERMES_NATIVE_ENTRY_COMMAND = "Открыть UX-песочницу Menu Planner"
DEMO_LABEL = "ДЕМО: ничего не сохраняю"
CLARIFY_DEMO_LAUNCHER_TEXT = (
    "Нажми кнопку ниже, чтобы открыть лёгкий UX Menu Planner. "
    "Это демо: кнопки работают, данные не сохраняются."
)
SCHEMA_VERSION = "m10_5.live_telegram_ux_sandbox.v1"
CORE_SCREEN_IDS = (
    "home",
    "home_with_menu",
    "menu_ready",
    "quick_adjust",
    "replacement_options",
    "shopping_list",
    "settings",
    "store_sources",
    "store_selection",
    "store_selection_result",
    "store_refresh",
    "settings_edit",
    "recipe_view",
    "done",
    "error_state",
)


def home_text() -> str:
    return screen_text("home")


def home_with_menu_text() -> str:
    return screen_text("home_with_menu")


def menu_ready_text() -> str:
    return screen_text("menu_ready")


def quick_adjust_text() -> str:
    return screen_text("quick_adjust")


def replacement_options_text() -> str:
    return screen_text("replacement_options")


def shopping_list_text() -> str:
    return screen_text("shopping_list")


def settings_text() -> str:
    return screen_text("settings")


def store_sources_text() -> str:
    return screen_text("store_sources")


def store_selection_text() -> str:
    return screen_text("store_selection")


def store_selection_result_text() -> str:
    return screen_text("store_selection_result")


def store_refresh_text() -> str:
    return screen_text("store_refresh")


def settings_edit_text() -> str:
    return screen_text("settings_edit")


def recipe_view_text() -> str:
    return screen_text("recipe_view")


def clarification_text() -> str:
    return settings_edit_text()


def done_text() -> str:
    return screen_text("done")


def error_state_text() -> str:
    return screen_text("error_state")


def status_text() -> str:
    return menu_ready_text()


def profile_draft_text() -> str:
    return settings_text()


def profile_preview_text() -> str:
    return settings_text()


def menu_draft_text() -> str:
    return quick_adjust_text()


def menu_preview_text() -> str:
    return menu_ready_text()


def validation_warnings_text() -> str:
    return replacement_options_text()


def confirmation_text() -> str:
    return done_text()


def shopping_checklist_text() -> str:
    return shopping_list_text()


def item_disambiguation_text() -> str:
    return clarification_text()


def cancel_flow_text() -> str:
    return home_text()


def expired_confirmation_text() -> str:
    return error_state_text()


def restart_recovery_text() -> str:
    return home_text()


def screen_text(screen_id: str) -> str:
    try:
        return _render_preview(_RU_PREVIEWS[screen_id])
    except KeyError as exc:
        raise ValueError(f"unknown screen id: {screen_id}") from exc


def screen_catalog() -> dict[str, dict[str, Any]]:
    return {
        screen_id: {
            "text": screen_text(screen_id),
            "ux_logic": _UX_LOGIC[screen_id],
            "suggested_improvements": list(_SUGGESTED_IMPROVEMENTS[screen_id]),
            "feedback_status": _FEEDBACK_STATUS[screen_id],
        }
        for screen_id in CORE_SCREEN_IDS
    }


def co_design_prompt() -> str:
    return "\n".join(
        [
            "Открыть UX-песочницу Menu Planner: цикл ревью экранов.",
            "",
            "Используй встроенный clarify tool для навигации в Telegram.",
            "Не используй terminal, files, web или внешние API.",
            "Не меняй активное состояние продукта.",
            "Все экраны ниже - ДЕМО-превью Stage 10.5.",
            "",
            "Покажи пользователю каждый экран в Telegram.",
            "Для каждого экрана кратко объясни UX-логику, предложи улучшения",
            "и спроси, что изменить. Варианты давай партиями до 4 пунктов.",
            "Если пользователь говорит, что правки не нужны, отметь экран принятым.",
            "",
            _co_design_screen_block(),
        ]
    )


def _co_design_screen_block() -> str:
    blocks: list[str] = []
    for index, screen_id in enumerate(CORE_SCREEN_IDS, start=1):
        blocks.extend(
            [
                f"{index}. {screen_id}",
                screen_text(screen_id),
                f"UX-логика: {_UX_LOGIC[screen_id]}",
                "Возможные улучшения:",
                *[
                    f"- {improvement}"
                    for improvement in _SUGGESTED_IMPROVEMENTS[screen_id]
                ],
                "",
            ]
        )
    return "\n".join(blocks).rstrip()


def home_keyboard() -> list[list[dict[str, str]]]:
    return [
        [
            {
                "text": "Составить меню",
                "callback_data": CALLBACK_STATUS,
            }
        ]
    ]


def status_keyboard() -> list[list[dict[str, str]]]:
    return [
        [
            {
                "text": "Главная",
                "callback_data": CALLBACK_HOME,
            }
        ]
    ]


def callback_data_values() -> tuple[str, ...]:
    return (CALLBACK_HOME, CALLBACK_STATUS)


def hermes_native_prompt() -> str:
    return "\n".join(
        [
            HERMES_NATIVE_ENTRY_COMMAND,
            "",
            "Используй встроенный clarify tool для навигации в Telegram.",
            "Не используй terminal, files, web или внешние API.",
            "Не меняй активное состояние продукта.",
            "Сначала покажи этот экран как clarify question:",
            home_text(),
            "",
            "Предложи ровно один вариант: Составить меню.",
            "Когда пользователь выберет Составить меню, ответь этим экраном:",
            menu_ready_text(),
            "",
            "Затем задай ещё один clarify-вопрос с одним вариантом: Главная.",
            "После выбора Главная покажи экран активного меню:",
            home_with_menu_text(),
            "",
            "Это только ДЕМО-песочница Stage 10.5.",
        ]
    )


def hermes_native_full_demo_prompt() -> str:
    return "\n".join(
        [
            HERMES_NATIVE_ENTRY_COMMAND,
            "",
            "Построй интерактивное ДЕМО в Telegram только через встроенный",
            "clarify tool. Не отправляй кастомные callback_data.",
            "Каждая кнопка должна быть настоящим Hermes clarify choice,",
            "то есть callback namespace должен быть cl:*.",
            "",
            "Не используй terminal, files, web или внешние API.",
            "Не меняй активное состояние продукта.",
            "Не вызывай Menu Planner tools и не выполняй commit.",
            "",
            "Правило навигации:",
            "- покажи текущий экран как clarify question;",
            "- предложи только варианты из списка для этого экрана;",
            "- после выбора покажи целевой экран и снова задай clarify;",
            "- не показывай технические статусы, черновики и confirmation_id;",
            "- если пользователь просит остановить демо, заверши без действий.",
            "",
            _clarify_demo_screen_block(),
        ]
    )


def _clarify_demo_screen_block() -> str:
    blocks: list[str] = []
    for screen_id in CORE_SCREEN_IDS:
        button_lines = [
            f"- {label} -> {_RU_PREVIEWS[target]['title']} ({target})"
            for label, target in zip(
                _RU_PREVIEWS[screen_id]["buttons"],
                _HERMES_CLARIFY_NAVIGATION[screen_id],
                strict=True,
            )
        ]
        blocks.extend(
            [
                f"screen_id: {screen_id}",
                screen_text(screen_id),
                "Кнопки clarify:",
                *button_lines,
                "",
            ]
        )
    return "\n".join(blocks).rstrip()


def dry_run_result() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "mode": "dry_run",
        "ok": True,
        "telegram_network_used": False,
        "credentials_used": False,
        "screens": {
            screen_id: screen_text(screen_id) for screen_id in CORE_SCREEN_IDS
        },
        "screen_count": len(CORE_SCREEN_IDS),
        "callback_data": list(callback_data_values()),
        "callback_data_shape": f"{CALLBACK_PREFIX}<clarify_id>:<choice_index>",
        "callback_data_max_static_bytes": max(
            len(value.encode("utf-8")) for value in callback_data_values()
        ),
        "demo_only": True,
        "active_state_changed": False,
        "target_runtime_path": "hermes_native_clarify",
        "entry_command": HERMES_NATIVE_ENTRY_COMMAND,
        "telegram_gateway_callback_namespace": "cl:*",
        "button_label_mode": "user_visible_text",
        "global_close_button": False,
        "text_input_policy": "only_declared_screens",
        "button_only_text_policy": "block_inside_sandbox",
        "prompt_injection_policy": "planned_schema_guard_for_text_screens",
        "ux_model": "light_menu_planning_flow",
        "primary_flow_taps": {
            "generate_menu_from_empty_home": 1,
            "return_to_active_home_after_menu": 1,
            "open_shopping_list_from_active_home": 1,
            "change_menu_from_active_home": 1,
            "open_menu_text_edit_from_active_home": 1,
        },
        "unsupported_callback_namespaces": ["dm:*", "pv:*", "ux:*"],
    }


async def run_live(*, poll_seconds: int) -> dict[str, Any]:
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    allowed = _first_csv_value(os.environ.get("TELEGRAM_ALLOWED_USERS", ""))
    if not token or not allowed:
        return _live_result(
            ok=False,
            sent=False,
            callback_received=False,
            error_code="telegram_config_missing",
        )

    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    from telegram.request import HTTPXRequest
    from telegram.ext import ExtBot

    try:
        request = HTTPXRequest(proxy=os.environ.get("TELEGRAM_PROXY") or None)
        bot = ExtBot(token=token, request=request)
        sent = await bot.send_message(
            chat_id=allowed,
            text=home_text(),
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "Составить меню",
                            callback_data=CALLBACK_STATUS,
                        )
                    ]
                ]
            ),
        )
    except Exception as exc:  # pragma: no cover - live network guard
        return _live_result(
            ok=False,
            sent=False,
            callback_received=False,
            telegram_network_used=True,
            credentials_used=True,
            error_code=_live_error_code(exc),
        )

    offset: int | None = None
    deadline = time.monotonic() + poll_seconds
    callback_received = False
    callback_shape = ""
    while time.monotonic() < deadline:
        try:
            updates = await bot.get_updates(
                offset=offset,
                timeout=5,
                allowed_updates=["callback_query"],
            )
        except Exception as exc:  # pragma: no cover - live network guard
            if _live_error_code(exc) == "telegram_timeout":
                continue
            return _live_result(
                ok=False,
                sent=True,
                callback_received=False,
                message_sent=True,
                sent_screen="home",
                telegram_network_used=True,
                credentials_used=True,
                active_state_changed=False,
                callback_data_max_bytes=max(
                    len(value.encode("utf-8")) for value in callback_data_values()
                ),
                poll_seconds=poll_seconds,
                error_code=_live_error_code(exc),
                sent_message_sanitized=True,
            )
        for update in updates:
            offset = update.update_id + 1
            query = update.callback_query
            if query is None or query.data not in callback_data_values():
                continue
            callback_received = True
            callback_shape = _callback_shape(query.data)
            await query.answer("Sandbox navigation")
            if query.data == CALLBACK_STATUS:
                await query.edit_message_text(
                    text=menu_ready_text(),
                    reply_markup=InlineKeyboardMarkup(
                        [[InlineKeyboardButton("Главная", callback_data=CALLBACK_HOME)]]
                    ),
                )
            else:
                await query.edit_message_text(
                    text=home_with_menu_text(),
                    reply_markup=InlineKeyboardMarkup(
                        [
                            [
                                InlineKeyboardButton(
                                    "Покупки",
                                    callback_data=CALLBACK_STATUS,
                                )
                            ]
                        ]
                    ),
                )
            break
        if callback_received:
            break

    return _live_result(
        ok=callback_received,
        sent=True,
        callback_received=callback_received,
        callback_shape=callback_shape,
        message_sent=True,
        message_id_recorded=False,
        sent_screen="home",
        response_screen="menu_ready" if callback_received else "",
        telegram_network_used=True,
        credentials_used=True,
        active_state_changed=False,
        callback_data_max_bytes=max(
            len(value.encode("utf-8")) for value in callback_data_values()
        ),
        poll_seconds=poll_seconds,
        error_code="" if callback_received else "callback_not_received",
        sent_message_sanitized=True if sent is not None else False,
    )


async def send_co_design_review() -> dict[str, Any]:
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    allowed = _first_csv_value(os.environ.get("TELEGRAM_ALLOWED_USERS", ""))
    if not token or not allowed:
        return _live_result(
            ok=False,
            sent=False,
            callback_received=False,
            error_code="telegram_config_missing",
        )

    from telegram.request import HTTPXRequest
    from telegram.ext import ExtBot

    previews = _telegram_preview_messages()
    try:
        request = HTTPXRequest(proxy=os.environ.get("TELEGRAM_PROXY") or None)
        bot = ExtBot(token=token, request=request)
        for preview in previews:
            await bot.send_message(
                chat_id=allowed,
                text=preview["text"],
            )
    except Exception as exc:  # pragma: no cover - live network guard
        return _live_result(
            ok=False,
            sent=False,
            callback_received=False,
            telegram_network_used=True,
            credentials_used=True,
            error_code=_live_error_code(exc),
        )

    return _live_result(
        ok=True,
        sent=True,
        callback_received=False,
        message_sent=True,
        sent_screen="core_screen_catalog",
        message_count=len(previews),
        screen_count=len(CORE_SCREEN_IDS),
        inline_keyboards_sent=False,
        action_labels_sent=True,
        telegram_network_used=True,
        credentials_used=True,
        active_state_changed=False,
        sent_message_sanitized=True,
    )


async def send_clarify_demo_launcher() -> dict[str, Any]:
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    allowed = _first_csv_value(os.environ.get("TELEGRAM_ALLOWED_USERS", ""))
    if not token or not allowed:
        return _live_result(
            ok=False,
            sent=False,
            callback_received=False,
            error_code="telegram_config_missing",
        )

    from telegram import KeyboardButton, ReplyKeyboardMarkup
    from telegram.request import HTTPXRequest
    from telegram.ext import ExtBot

    try:
        request = HTTPXRequest(proxy=os.environ.get("TELEGRAM_PROXY") or None)
        bot = ExtBot(token=token, request=request)
        await bot.send_message(
            chat_id=allowed,
            text=CLARIFY_DEMO_LAUNCHER_TEXT,
            reply_markup=ReplyKeyboardMarkup(
                [[KeyboardButton(HERMES_NATIVE_ENTRY_COMMAND)]],
                resize_keyboard=True,
                one_time_keyboard=True,
                input_field_placeholder=HERMES_NATIVE_ENTRY_COMMAND,
            ),
        )
    except Exception as exc:  # pragma: no cover - live network guard
        return _live_result(
            ok=False,
            sent=False,
            callback_received=False,
            telegram_network_used=True,
            credentials_used=True,
            error_code=_live_error_code(exc),
        )

    return _live_result(
        ok=True,
        sent=True,
        callback_received=False,
        message_sent=True,
        sent_screen="clarify_demo_launcher",
        launcher_button_text=HERMES_NATIVE_ENTRY_COMMAND,
        telegram_network_used=True,
        credentials_used=True,
        active_state_changed=False,
        sent_message_sanitized=True,
    )


def _telegram_preview_messages() -> list[dict[str, Any]]:
    return [
        {
            "screen_id": screen_id,
            "text": screen_text(screen_id),
            "buttons": list(_RU_PREVIEWS[screen_id]["buttons"]),
        }
        for screen_id in CORE_SCREEN_IDS
    ]


def _co_design_messages() -> list[str]:
    header = "\n".join(
        [
            "Menu Planner - UX-песочница",
            "ДЕМО-ревью: ничего не сохраняю.",
            "",
            "Ниже лёгкий сценарий планирования меню.",
            "Ответь названиями экранов и нужными правками.",
        ]
    )
    chunks = [header]
    current: list[str] = []
    current_len = 0
    for screen_id in CORE_SCREEN_IDS:
        block = "\n".join(
            [
                screen_text(screen_id),
                f"UX-логика: {_UX_LOGIC[screen_id]}",
                "Возможные улучшения:",
                *[
                    f"- {improvement}"
                    for improvement in _SUGGESTED_IMPROVEMENTS[screen_id]
                ],
            ]
        )
        block_len = len(block) + 2
        if current and current_len + block_len > 3200:
            chunks.append("\n\n".join(current))
            current = []
            current_len = 0
        current.append(block)
        current_len += block_len
    if current:
        chunks.append("\n\n".join(current))
    return chunks


def _live_result(**overrides: Any) -> dict[str, Any]:
    result: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "mode": "live",
        "ok": False,
        "sent": False,
        "callback_received": False,
        "callback_shape": "",
        "telegram_network_used": False,
        "credentials_used": False,
        "demo_only": True,
        "active_state_changed": False,
        "error_code": "",
    }
    result.update(overrides)
    return result


def _first_csv_value(value: str) -> str:
    for part in value.split(","):
        normalized = part.strip()
        if normalized:
            return normalized
    return ""


def _callback_shape(callback_data: str) -> str:
    if callback_data.startswith(CALLBACK_PREFIX):
        return f"{CALLBACK_PREFIX}*"
    return "unknown"


def _live_error_code(exc: Exception) -> str:
    name = type(exc).__name__.casefold()
    message = str(exc).casefold()
    if "timeout" in name or "timed out" in message:
        return "telegram_timeout"
    if "conflict" in name or "conflict" in message:
        return "telegram_get_updates_conflict"
    return "telegram_live_error"


def _render_preview(preview: dict[str, Any]) -> str:
    lines = [
        "Menu Planner",
        DEMO_LABEL,
        "",
        preview["title"],
        "",
    ]
    for section in preview["sections"]:
        lines.append(f"{section['label']}:")
        lines.extend(f"- {item}" for item in section["items"])
        lines.append("")
    warnings = preview.get("warnings", ())
    if warnings:
        lines.append("Предупреждения:")
        lines.extend(f"- {warning}" for warning in warnings)
        lines.append("")
    lines.append("Выбери действие ниже.")
    return "\n".join(lines).rstrip()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--prompt", action="store_true")
    parser.add_argument("--full-demo-prompt", action="store_true")
    parser.add_argument("--co-design-prompt", action="store_true")
    parser.add_argument("--send-co-design-review", action="store_true")
    parser.add_argument("--send-clarify-demo-launcher", action="store_true")
    parser.add_argument("--catalog", action="store_true")
    parser.add_argument("--poll-seconds", type=int, default=60)
    args = parser.parse_args()

    if args.catalog:
        print(json.dumps(screen_catalog(), ensure_ascii=False, sort_keys=True))
        return 0
    if args.co_design_prompt:
        print(co_design_prompt())
        return 0
    if args.full_demo_prompt:
        print(hermes_native_full_demo_prompt())
        return 0
    if args.prompt:
        print(hermes_native_prompt())
        return 0
    if args.dry_run:
        result = dry_run_result()
    elif args.send_co_design_review:
        result = asyncio.run(send_co_design_review())
    elif args.send_clarify_demo_launcher:
        result = asyncio.run(send_clarify_demo_launcher())
    else:
        result = asyncio.run(run_live(poll_seconds=max(1, args.poll_seconds)))
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if result["ok"] else 1


_RU_PREVIEWS: dict[str, dict[str, Any]] = {
    "home": {
        "title": "Что приготовить?",
        "sections": (
            {
                "label": "Быстрый старт",
                "items": (
                    "соберу меню на неделю по текущим привычкам",
                    "сразу покажу меню, замены и покупки",
                ),
            },
            {
                "label": "Можно написать",
                "items": (
                    "меню на 5 дней без рыбы",
                    "быстрые ужины на неделю",
                ),
            },
        ),
        "buttons": ("Составить меню", "Настройки"),
    },
    "home_with_menu": {
        "title": "Главная",
        "sections": (
            {
                "label": "Сегодня",
                "items": (
                    "ужин: боул с чечевицей",
                    "30 минут",
                    "рецепт доступен с главной",
                ),
            },
            {
                "label": "Покупки",
                "items": (
                    "осталось купить: чечевица, томаты, тофу",
                    "список сгруппирован по выбранным магазинам",
                ),
            },
            {
                "label": "Меню",
                "items": ("составлено на 5 ужинов",),
            },
        ),
        "buttons": ("Покупки", "Рецепт", "Изменить меню", "Настройки"),
    },
    "menu_ready": {
        "title": "Меню составлено",
        "sections": (
            {
                "label": "Ужины",
                "items": (
                    "Пн: боул с чечевицей",
                    "Вт: паста с томатами",
                    "Ср: тофу с рисом и овощами",
                    "Чт: суп с фасолью",
                    "Пт: шакшука",
                ),
            },
            {
                "label": "Подходит под запрос",
                "items": (
                    "до 35 минут в будни",
                    "без рыбы в будни",
                    "покупки сгруппированы по выбранным магазинам",
                ),
            },
            {
                "label": "Дальше",
                "items": (
                    "вернись на главную, там появятся покупки и рецепт",
                    "меню можно изменить с главной",
                ),
            },
        ),
        "buttons": ("Главная", "Изменить меню"),
    },
    "quick_adjust": {
        "title": "Изменить меню",
        "sections": (
            {
                "label": "Напиши, что изменить",
                "items": (
                    "замени пасту во вторник",
                    "сделай ужины дешевле",
                    "убери острое",
                    "добавь больше белка",
                ),
            },
            {
                "label": "Что будет дальше",
                "items": (
                    "покажу предпросмотр нового меню",
                    "покупки пересчитаются только после подтверждения",
                ),
            },
            {
                "label": "В демо",
                "items": ("текст не сохраняю, только показываю логику",),
            },
        ),
        "buttons": ("Главная", "Покупки"),
    },
    "replacement_options": {
        "title": "Предпросмотр правки",
        "sections": (
            {
                "label": "Пример изменения",
                "items": (
                    "вторник: паста -> рис с овощами",
                    "пятница остаётся без изменений",
                    "покупки обновятся после сохранения",
                ),
            },
            {
                "label": "Безопасность",
                "items": (
                    "в продукте сначала будет предпросмотр",
                    "без подтверждения меню не изменится",
                ),
            },
            {
                "label": "В демо",
                "items": ("ничего не сохраняю",),
            },
        ),
        "buttons": ("Главная", "Написать иначе"),
    },
    "shopping_list": {
        "title": "Покупки",
        "sections": (
            {
                "label": "Перекрёсток",
                "items": (
                    "чечевица - 400 г",
                    "томаты - 6 шт",
                    "фасоль - 2 банки",
                ),
            },
            {
                "label": "ВкусВилл",
                "items": (
                    "тофу - 300 г",
                    "йогурт - 1 шт",
                ),
            },
            {
                "label": "Проверь дома",
                "items": ("рис", "оливковое масло", "специи"),
            },
            {
                "label": "Группировка",
                "items": ("2 источника выбраны, поэтому список разделён по магазинам",),
            },
        ),
        "buttons": ("Рецепт", "Главная"),
    },
    "settings": {
        "title": "Настройки питания",
        "sections": (
            {
                "label": "Сейчас",
                "items": (
                    "2 человека",
                    "ужины до 35 минут",
                    "без рыбы в будни",
                    "бюджетный режим",
                ),
            },
            {
                "label": "Правка питания",
                "items": ("напиши текстом только про привычки и ограничения",),
            },
            {
                "label": "Магазины",
                "items": (
                    "выбраны: Перекрёсток, ВкусВилл",
                    "не подключён: Лента",
                    "по умолчанию источники выключены",
                    "магазины не добавляются свободным текстом",
                ),
            },
        ),
        "buttons": ("Источники цен", "Изменить питание", "Назад"),
    },
    "store_sources": {
        "title": "Источники цен",
        "sections": (
            {
                "label": "Выбраны",
                "items": (
                    "Перекрёсток - навык Hermes, ежедневно 07:00",
                    "ВкусВилл - навык Hermes, по требованию",
                ),
            },
            {
                "label": "Доступны",
                "items": (
                    "Лента - не подключена",
                    "новый источник подключается только выбором пользователя",
                ),
            },
            {
                "label": "Как это работает",
                "items": (
                    "каждый магазин - отдельный управляемый источник",
                    "обновляются только выбранные источники",
                    "сырой сайт магазина пользователь не настраивает",
                    "2+ источника дают группы покупок по магазинам",
                ),
            },
            {
                "label": "ДЕМО",
                "items": ("сейчас ничего не парсю, цены и наличие не загружаю",),
            },
        ),
        "buttons": ("Выбрать магазины", "Обновить сейчас", "Назад", "Главная"),
    },
    "store_selection": {
        "title": "Выбор магазинов",
        "sections": (
            {
                "label": "Сейчас выбраны",
                "items": ("Перекрёсток", "ВкусВилл"),
            },
            {
                "label": "Можно изменить",
                "items": (
                    "Лента доступна, но не подключена",
                    "ВкусВилл можно отключить",
                    "минимум один источник нужен для цен",
                ),
            },
            {
                "label": "ДЕМО",
                "items": ("кнопки показывают выбор, но ничего не сохраняют",),
            },
        ),
        "buttons": ("Подключить Ленту", "Отключить ВкусВилл", "Назад"),
    },
    "store_selection_result": {
        "title": "Изменение источников",
        "sections": (
            {
                "label": "В продукте",
                "items": (
                    "сохраню выбранные магазины после проверки",
                    "обновлю только подключённые источники",
                    "перегруппирую покупки по выбранным магазинам",
                ),
            },
            {
                "label": "Правило списков",
                "items": (
                    "1 источник - один список покупок",
                    "2+ источника - группы по каждому магазину",
                ),
            },
            {
                "label": "В демо",
                "items": ("выбор не сохраняю",),
            },
        ),
        "buttons": ("К источникам", "Показать покупки", "Назад"),
    },
    "store_refresh": {
        "title": "Обновить источники",
        "sections": (
            {
                "label": "В продукте",
                "items": (
                    "запущу навыки только выбранных магазинов",
                    "покажу время обновления и ошибки источника",
                    "меню и покупки не изменятся без подтверждения",
                ),
            },
            {
                "label": "В демо",
                "items": ("ничего не запускаю и не загружаю цены",),
            },
        ),
        "buttons": ("К источникам", "Настройки"),
    },
    "settings_edit": {
        "title": "Изменить питание",
        "sections": (
            {
                "label": "Как это должно работать",
                "items": (
                    "напиши одной фразой, что поменять в питании",
                    "например: без рыбы",
                    "или: ужины до 30 минут",
                    "или: теперь 3 человека",
                    "магазины меняются через Источники цен",
                ),
            },
            {
                "label": "В демо",
                "items": ("кнопки только показывают логику переходов",),
            },
        ),
        "buttons": ("Назад к настройкам", "Главная"),
    },
    "recipe_view": {
        "title": "Рецепты",
        "sections": (
            {
                "label": "Сегодня",
                "items": (
                    "боул с чечевицей",
                    "30 минут",
                    "чечевица, рис, огурец, йогурт",
                ),
            },
            {
                "label": "Показ",
                "items": ("короткая карточка сейчас, шаги отдельным сообщением",),
            },
        ),
        "buttons": ("Покупки", "Главная"),
    },
    "done": {
        "title": "Готово",
        "sections": (
            {
                "label": "Меню принято",
                "items": (
                    "в демо я ничего не сохраняю",
                    "в продукте эта кнопка сохранит меню с текущего экрана",
                ),
            },
            {
                "label": "Следующий шаг",
                "items": ("открыть покупки или рецепты",),
            },
        ),
        "buttons": ("Покупки", "Рецепт", "Главная"),
    },
    "error_state": {
        "title": "Не получилось",
        "sections": (
            {
                "label": "Что произошло",
                "items": ("я не смог собрать демо-экран",),
            },
            {
                "label": "Безопасность",
                "items": ("ничего не сохранилось",),
            },
        ),
        "buttons": ("Повторить", "Главная"),
    },
}


_SCREEN_TEXT_BUILDERS = {
    "home": home_text,
    "home_with_menu": home_with_menu_text,
    "menu_ready": menu_ready_text,
    "quick_adjust": quick_adjust_text,
    "replacement_options": replacement_options_text,
    "shopping_list": shopping_list_text,
    "settings": settings_text,
    "store_sources": store_sources_text,
    "store_selection": store_selection_text,
    "store_selection_result": store_selection_result_text,
    "store_refresh": store_refresh_text,
    "settings_edit": settings_edit_text,
    "recipe_view": recipe_view_text,
    "done": done_text,
    "error_state": error_state_text,
}

_HERMES_CLARIFY_NAVIGATION: dict[str, tuple[str, ...]] = {
    "home": ("menu_ready", "settings"),
    "home_with_menu": ("shopping_list", "recipe_view", "quick_adjust", "settings"),
    "menu_ready": ("home_with_menu", "quick_adjust"),
    "quick_adjust": ("home_with_menu", "shopping_list"),
    "replacement_options": ("home_with_menu", "quick_adjust"),
    "shopping_list": ("recipe_view", "home_with_menu"),
    "settings": ("store_sources", "settings_edit", "home"),
    "store_sources": ("store_selection", "store_refresh", "settings", "home"),
    "store_selection": (
        "store_selection_result",
        "store_selection_result",
        "store_sources",
    ),
    "store_selection_result": ("store_sources", "shopping_list", "store_selection"),
    "store_refresh": ("store_sources", "settings"),
    "settings_edit": ("settings", "home"),
    "recipe_view": ("shopping_list", "home_with_menu"),
    "done": ("shopping_list", "recipe_view", "home_with_menu"),
    "error_state": ("home", "home"),
}

_UX_LOGIC = {
    "home": "Пустая главная предлагает составить меню без лишних действий.",
    "home_with_menu": (
        "Главная с меню показывает текущий приём пищи, покупки и настройки."
    ),
    "menu_ready": (
        "После составления меню экран показывает результат и возвращает на "
        "главную с активным меню."
    ),
    "quick_adjust": "Изменение меню начинается с обычного текстового запроса.",
    "replacement_options": "После текста показывается preview изменения без commit.",
    "shopping_list": (
        "Покупки доступны в один тап и при нескольких источниках сгруппированы "
        "по магазинам."
    ),
    "settings": (
        "Настройки разделяют пищевые предпочтения и управляемые источники цен."
    ),
    "store_sources": (
        "Магазины показаны как выбранные источники, а не как список включенный "
        "по умолчанию."
    ),
    "store_selection": (
        "Выбор магазинов показывает включение/отключение источников без "
        "текстового ввода."
    ),
    "store_selection_result": (
        "После изменения объясняется влияние на обновления и группировку "
        "покупок."
    ),
    "store_refresh": (
        "Ручное обновление объясняет запуск навыков Hermes без изменения меню."
    ),
    "settings_edit": "Правка питания объясняет text-first ввод без магазинов.",
    "recipe_view": "Рецепт показывается карточкой, без длинной стены шагов.",
    "done": "Кнопка принятия на экране меню является подтверждением без второго шага.",
    "error_state": "Ошибка объясняет результат и даёт один безопасный выход.",
}

_SUGGESTED_IMPROVEMENTS = {
    "home": ("Оставить одну кнопку старта до появления активного меню.",),
    "home_with_menu": (
        "Показывать покупки только когда меню уже составлено.",
    ),
    "menu_ready": (
        "Не использовать подтверждающие или слишком общие кнопки на результате меню.",
    ),
    "quick_adjust": ("Не заставлять выбирать блюдо кнопкой; принимать текст.",),
    "replacement_options": ("Показывать diff перед сохранением.",),
    "shopping_list": (
        "При 2+ выбранных источниках держать группы по каждому магазину.",
    ),
    "settings": (
        "Не добавлять магазины текстом; вести в отдельный экран источников цен.",
    ),
    "store_sources": (
        "Показывать доступные, выбранные и отключенные источники без перегруза.",
    ),
    "store_selection": (
        "Не включать все магазины по умолчанию; дать быстрые toggle-кнопки.",
    ),
    "store_selection_result": (
        "В продукте показать, как выбор повлияет на покупки перед сохранением.",
    ),
    "store_refresh": (
        "Запускать обновление только для выбранных источников.",
    ),
    "settings_edit": ("Показать примеры текстовых правок только про питание.",),
    "recipe_view": ("Оставить шаги рецепта вторичным раскрытием.",),
    "done": ("Не добавлять отдельный экран подтверждения после понятного preview.",),
    "error_state": ("Давать 1-2 действия восстановления, не стек ошибок.",),
}

_FEEDBACK_STATUS = {
    "home": "обновлено после feedback: убрать инженерный UX",
    "home_with_menu": (
        "обновлено после feedback: покупки доступны на главной после меню"
    ),
    "menu_ready": "обновлено после feedback: результат первым экраном после старта",
    "quick_adjust": "обновлено после feedback: изменение меню стало text-first",
    "replacement_options": "обновлено после feedback: preview после текстовой правки",
    "shopping_list": "обновлено после feedback: покупки в один тап",
    "settings": (
        "исправлено после feedback: настройки больше не составляют меню; "
        "магазины вынесены в управляемые источники цен"
    ),
    "store_sources": (
        "обновлено после feedback: не все магазины включены по умолчанию"
    ),
    "store_selection": (
        "обновлено после feedback: пользователь выбирает нужные магазины"
    ),
    "store_selection_result": (
        "обновлено после feedback: показано влияние выбора на покупки"
    ),
    "store_refresh": (
        "обновлено после feedback: ручной запуск показан как демо-действие"
    ),
    "settings_edit": "обновлено после feedback: text-first только для питания",
    "recipe_view": "обновлено после feedback: рецепты без стены текста",
    "done": "обновлено после feedback: без лишнего confirm screen",
    "error_state": "обновлено после feedback: короткое восстановление",
}


if __name__ == "__main__":
    raise SystemExit(main())
