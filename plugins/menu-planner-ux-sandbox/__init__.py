"""Stage 10.5 Telegram UX sandbox adapter.

The adapter is intentionally demo-only. It intercepts one narrow Telegram
command and drives a finite screen loop through Hermes' native clarify
primitive, so Telegram buttons use the installed ``cl:*`` callback path.
"""

from __future__ import annotations

import asyncio
import html
import importlib.util
import logging
import os
import uuid
from pathlib import Path
from typing import Any


COMMAND = "Открыть UX-песочницу Menu Planner"
PLUGIN_NAME = "menu-planner-ux-sandbox"
SESSION_PREFIX = "m10_5_ux_sandbox"
MAX_STEPS = 30
CLARIFY_TIMEOUT_SECONDS = 600
MAX_BUTTON_LABEL_CHARS = 32
TELEGRAM_SEND_TIMEOUT_SECONDS = 30
TELEGRAM_SEND_ATTEMPTS = 3
TELEGRAM_RETRY_DELAY_SECONDS = 1.0
SETTINGS_TEXT_SCREENS = frozenset({"settings", "settings_edit"})
MENU_EDIT_TEXT_SCREENS = frozenset({"quick_adjust"})
TEXT_INPUT_SCREENS = SETTINGS_TEXT_SCREENS | MENU_EDIT_TEXT_SCREENS
MAX_USER_TEXT_PREVIEW_CHARS = 80
STORE_TEXT_KEYWORDS = frozenset(
    {
        "вкусвилл",
        "источник",
        "лент",
        "магаз",
        "перекр",
        "цены",
    }
)
PROMPT_INJECTION_MARKERS = (
    "ignore previous",
    "ignore all previous",
    "system prompt",
    "developer message",
    "tool call",
    "auth.json",
    "api key",
    "secret",
    "jailbreak",
    "role:",
    "<system",
    "игнорируй",
    "предыдущие инструкции",
    "системн",
    "разработчик",
    "секрет",
    "токен",
    "ключ api",
    "инструмент",
    "промпт",
)
UNCERTAIN_TELEGRAM_ERROR_NAMES = frozenset(
    {
        "ConnectTimeout",
        "PoolTimeout",
        "ReadTimeout",
        "RemoteProtocolError",
        "TimedOut",
        "TimeoutException",
        "WriteTimeout",
    }
)

_ACTIVE_TASKS: dict[str, asyncio.Task[Any]] = {}
_ACTIVE_SCREENS: dict[str, str] = {}
_LOGGER = logging.getLogger(__name__)


def register(ctx: Any) -> None:
    ctx.register_hook("pre_gateway_dispatch", pre_gateway_dispatch)


def pre_gateway_dispatch(**kwargs: Any) -> dict[str, Any] | None:
    event = kwargs.get("event")
    gateway = kwargs.get("gateway")
    if event is None or gateway is None:
        return None

    text = _event_text(event)
    source = getattr(event, "source", None)
    if text == COMMAND:
        if source is None or not _is_authorized(gateway, source):
            return {"action": "allow"}
        try:
            _schedule_demo(gateway, event)
        except RuntimeError:
            _LOGGER.warning("Could not schedule Stage 10.5 UX sandbox demo")
            return {"action": "allow"}
        return {"action": "skip", "reason": PLUGIN_NAME}

    if source is None or not _is_authorized(gateway, source):
        return None

    session_key = _session_key(event)
    active_screen = _ACTIVE_SCREENS.get(session_key)
    if _should_block_prompt_injection(active_screen, text):
        try:
            _schedule_demo(
                gateway,
                event,
                start_screen=active_screen or "home",
                notice=_prompt_injection_notice(),
            )
        except RuntimeError:
            _LOGGER.warning("Could not schedule Stage 10.5 prompt guard demo")
            return {"action": "allow"}
        return {"action": "skip", "reason": PLUGIN_NAME}

    if _should_capture_settings_text(session_key, text):
        start_screen = "settings"
        notice = _settings_text_notice(text)
        if _looks_like_store_text(text):
            start_screen = "store_sources"
            notice = _store_text_notice(text)
        try:
            _schedule_demo(
                gateway,
                event,
                start_screen=start_screen,
                notice=notice,
            )
        except RuntimeError:
            _LOGGER.warning("Could not schedule Stage 10.5 settings text demo")
            return {"action": "allow"}
        return {"action": "skip", "reason": PLUGIN_NAME}

    if _should_capture_menu_edit_text(session_key, text):
        try:
            _schedule_demo(
                gateway,
                event,
                start_screen="replacement_options",
                notice=_menu_edit_text_notice(text),
            )
        except RuntimeError:
            _LOGGER.warning("Could not schedule Stage 10.5 menu edit demo")
            return {"action": "allow"}
        return {"action": "skip", "reason": PLUGIN_NAME}

    if _should_block_button_only_text(active_screen, text):
        try:
            _schedule_demo(
                gateway,
                event,
                start_screen=active_screen or "home",
                notice=_button_only_text_notice(),
            )
        except RuntimeError:
            _LOGGER.warning("Could not schedule Stage 10.5 button-only guard demo")
            return {"action": "allow"}
        return {"action": "skip", "reason": PLUGIN_NAME}

    return None


def _should_block_prompt_injection(active_screen: str | None, text: str) -> bool:
    if active_screen not in TEXT_INPUT_SCREENS or not text or text == COMMAND:
        return False
    normalized = str(text).casefold()
    return any(marker in normalized for marker in PROMPT_INJECTION_MARKERS)


def _should_block_button_only_text(active_screen: str | None, text: str) -> bool:
    if active_screen is None or not text or text == COMMAND:
        return False
    return active_screen not in TEXT_INPUT_SCREENS


def _should_capture_settings_text(session_key: str, text: str) -> bool:
    if not text or text == COMMAND:
        return False
    return _ACTIVE_SCREENS.get(session_key) in SETTINGS_TEXT_SCREENS


def _should_capture_menu_edit_text(session_key: str, text: str) -> bool:
    if not text or text == COMMAND:
        return False
    return _ACTIVE_SCREENS.get(session_key) in MENU_EDIT_TEXT_SCREENS


def _settings_text_notice(text: str) -> str:
    return (
        f"Понял: {_user_text_preview(text)}.\n"
        "ДЕМО: значения ниже не обновляю. В продукте здесь будет "
        "предпросмотр изменения перед сохранением."
    )


def _store_text_notice(text: str) -> str:
    return (
        f"Понял: {_user_text_preview(text)}.\n"
        "Магазины не меняются текстом. Открой Источники цен и выбери нужные "
        "магазины кнопками."
    )


def _menu_edit_text_notice(text: str) -> str:
    return (
        f"Понял: {_user_text_preview(text)}.\n"
        "ДЕМО: меню не меняю. Ниже показываю пример предпросмотра перед "
        "сохранением."
    )


def _button_only_text_notice() -> str:
    return (
        "На этом экране я принимаю только кнопки Menu Planner. "
        "Текст не передаю в общий агент и не выполняю как инструкцию."
    )


def _prompt_injection_notice() -> str:
    return (
        "Не выполню этот текст как инструкцию. Для безопасности здесь принимаются "
        "только правки меню или питания обычным пользовательским текстом."
    )


def _looks_like_store_text(text: str) -> bool:
    normalized = str(text).casefold()
    return any(keyword in normalized for keyword in STORE_TEXT_KEYWORDS)


def _user_text_preview(text: str) -> str:
    normalized = " ".join(str(text).split())
    if len(normalized) <= MAX_USER_TEXT_PREVIEW_CHARS:
        return normalized
    return f"{normalized[: MAX_USER_TEXT_PREVIEW_CHARS - 3].rstrip()}..."


def _clear_clarify_session(session_key: str) -> None:
    try:
        from tools import clarify_gateway

        clarify_gateway.clear_session(session_key)
    except Exception:
        pass


def _schedule_demo(
    gateway: Any,
    event: Any,
    *,
    start_screen: str = "home",
    notice: str | None = None,
) -> None:
    loop = asyncio.get_running_loop()
    session_key = _session_key(event)
    current = _ACTIVE_TASKS.get(session_key)
    if current is not None and not current.done():
        current.cancel()
    _clear_clarify_session(session_key)
    _ACTIVE_TASKS[session_key] = loop.create_task(
        _run_demo(
            gateway,
            event,
            start_screen=start_screen,
            notice=notice,
        )
    )


async def _run_demo(
    gateway: Any,
    event: Any,
    *,
    start_screen: str = "home",
    notice: str | None = None,
) -> None:
    source = getattr(event, "source", None)
    if source is None:
        return

    adapter = gateway.adapters.get(source.platform)
    chat_id = getattr(source, "chat_id", None)
    if adapter is None or not chat_id:
        return

    screen_module = _load_screen_module()
    session_key = _session_key(event)
    metadata = _metadata_from_event(event)
    screen_id = start_screen

    try:
        if notice:
            await adapter.send(
                str(chat_id),
                notice,
                metadata=metadata,
            )
        for _step in range(MAX_STEPS):
            _ACTIVE_SCREENS[session_key] = screen_id
            labels = list(screen_module._RU_PREVIEWS[screen_id]["buttons"])
            targets = list(screen_module._HERMES_CLARIFY_NAVIGATION[screen_id])
            response = await _ask_clarify(
                adapter=adapter,
                chat_id=str(chat_id),
                question=screen_module.screen_text(screen_id),
                choices=labels,
                session_key=session_key,
                metadata=metadata,
            )
            if not response:
                await adapter.send(
                    str(chat_id),
                    "Демо остановлено: ответ не получен вовремя.",
                    metadata=metadata,
                )
                return
            target = _target_for_response(response, labels, targets)
            if target is None:
                await adapter.send(
                    str(chat_id),
                    "В этом демо навигация работает кнопками. В продукте здесь "
                    "можно будет написать обычную правку меню.",
                    metadata=metadata,
                )
                continue
            screen_id = target

        await adapter.send(
            str(chat_id),
            "Демо остановлено после лимита шагов. Активное состояние не менялось.",
            metadata=metadata,
        )
    except asyncio.CancelledError:
        raise
    except Exception:
        _LOGGER.exception("Stage 10.5 UX sandbox demo failed")
        try:
            await adapter.send(
                str(chat_id),
                "Демо остановлено из-за ошибки sandbox adapter. "
                "Активное состояние не менялось.",
                metadata=metadata,
            )
        except Exception:
            pass
    finally:
        current_task = asyncio.current_task()
        if _ACTIVE_TASKS.get(session_key) is current_task:
            _ACTIVE_TASKS.pop(session_key, None)
            _ACTIVE_SCREENS.pop(session_key, None)


async def _ask_clarify(
    *,
    adapter: Any,
    chat_id: str,
    question: str,
    choices: list[str],
    session_key: str,
    metadata: dict[str, Any],
) -> str | None:
    from tools import clarify_gateway

    clarify_id = uuid.uuid4().hex[:10]
    clarify_gateway.register(
        clarify_id=clarify_id,
        session_key=session_key,
        question=question,
        choices=choices,
    )
    sent = await _send_labeled_clarify(
        adapter=adapter,
        chat_id=chat_id,
        question=question,
        choices=choices,
        clarify_id=clarify_id,
        session_key=session_key,
        metadata=metadata,
    )
    if not sent:
        clarify_gateway.clear_session(session_key)
        return None

    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(
        None,
        clarify_gateway.wait_for_response,
        clarify_id,
        float(CLARIFY_TIMEOUT_SECONDS),
    )


async def _send_labeled_clarify(
    *,
    adapter: Any,
    chat_id: str,
    question: str,
    choices: list[str],
    clarify_id: str,
    session_key: str,
    metadata: dict[str, Any],
) -> bool:
    if not choices or not getattr(adapter, "_bot", None):
        return False

    required_methods = (
        "_link_preview_kwargs",
        "_metadata_thread_id",
        "_reply_to_message_id_for_send",
        "_send_message_with_thread_fallback",
        "_thread_kwargs_for_send",
    )
    if any(
        not callable(getattr(adapter, method_name, None))
        for method_name in required_methods
    ):
        return False
    clarify_state = getattr(adapter, "_clarify_state", None)
    if not isinstance(clarify_state, dict):
        return False

    try:
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        from telegram.constants import ParseMode

        rows = [
            [
                InlineKeyboardButton(
                    spec["text"],
                    callback_data=spec["callback_data"],
                )
            ]
            for spec in _clarify_button_specs(clarify_id, choices)
        ]
        thread_id = adapter._metadata_thread_id(metadata)
        reply_to_id = adapter._reply_to_message_id_for_send(None, metadata)
        kwargs: dict[str, Any] = {
            "chat_id": int(chat_id),
            "text": f"❓ {html.escape(question)}",
            "parse_mode": ParseMode.HTML,
            "reply_markup": InlineKeyboardMarkup(rows),
            **adapter._link_preview_kwargs(),
        }
        kwargs.update(_telegram_timeout_kwargs())
        kwargs["reply_to_message_id"] = reply_to_id
        kwargs.update(
            adapter._thread_kwargs_for_send(
                chat_id,
                thread_id,
                metadata,
                reply_to_message_id=reply_to_id,
            )
        )

        clarify_state[clarify_id] = session_key

        last_error: Exception | None = None
        for attempt in range(TELEGRAM_SEND_ATTEMPTS):
            try:
                await adapter._send_message_with_thread_fallback(**kwargs)
                return True
            except Exception as exc:
                last_error = exc
                if not _is_uncertain_telegram_delivery_error(exc):
                    raise
                if attempt + 1 < TELEGRAM_SEND_ATTEMPTS:
                    await asyncio.sleep(TELEGRAM_RETRY_DELAY_SECONDS)
                    continue

        exc_info = (
            (type(last_error), last_error, last_error.__traceback__)
            if last_error is not None
            else None
        )
        _LOGGER.warning(
            "Labeled clarify send had Telegram timeout after retries; "
            "keeping clarify state because delivery is uncertain",
            exc_info=exc_info,
        )
        return True
    except Exception:
        clarify_state.pop(clarify_id, None)
        _LOGGER.warning(
            "Labeled clarify send failed; numeric Hermes fallback is disabled",
            exc_info=True,
        )
        return False


def _clarify_button_specs(clarify_id: str, choices: list[str]) -> list[dict[str, str]]:
    return [
        {
            "text": _button_label(choice),
            "callback_data": f"cl:{clarify_id}:{idx}",
        }
        for idx, choice in enumerate(choices)
    ]


def _button_label(choice: str) -> str:
    label = " ".join(str(choice).split())
    if not label:
        return "Вариант"
    if len(label) <= MAX_BUTTON_LABEL_CHARS:
        return label
    return f"{label[: MAX_BUTTON_LABEL_CHARS - 3].rstrip()}..."


def _telegram_timeout_kwargs() -> dict[str, int]:
    return {
        "connect_timeout": TELEGRAM_SEND_TIMEOUT_SECONDS,
        "read_timeout": TELEGRAM_SEND_TIMEOUT_SECONDS,
        "write_timeout": TELEGRAM_SEND_TIMEOUT_SECONDS,
        "pool_timeout": TELEGRAM_SEND_TIMEOUT_SECONDS,
    }


def _is_uncertain_telegram_delivery_error(exc: BaseException) -> bool:
    seen: set[int] = set()
    current: BaseException | None = exc
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        if type(current).__name__ in UNCERTAIN_TELEGRAM_ERROR_NAMES:
            return True
        current = current.__cause__ or current.__context__
    return False


def _target_for_response(
    response: str,
    labels: list[str],
    targets: list[str],
) -> str | None:
    normalized = _normalize(response)
    for label, target in zip(labels, targets, strict=True):
        if _normalize(label) == normalized:
            return target
    return None


def _load_screen_module() -> Any:
    candidates = [
        os.environ.get("MENU_PLANNER_UX_SANDBOX_SCRIPT", ""),
        "/opt/menu-planner/m10_5_live_telegram_ux_sandbox.py",
        str(Path(__file__).resolve().parents[2] / "scripts" / "m10_5_live_telegram_ux_sandbox.py"),
    ]
    for candidate in candidates:
        if not candidate:
            continue
        path = Path(candidate)
        if not path.exists():
            continue
        spec = importlib.util.spec_from_file_location(
            "m10_5_live_telegram_ux_sandbox",
            path,
        )
        if spec is None or spec.loader is None:
            continue
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    raise RuntimeError("Stage 10.5 screen module not found")


def _is_authorized(gateway: Any, source: Any) -> bool:
    checker = getattr(gateway, "_is_user_authorized", None)
    if not callable(checker):
        return False
    try:
        return bool(checker(source))
    except Exception:
        return False


def _metadata_from_event(event: Any) -> dict[str, Any]:
    metadata = dict(getattr(event, "metadata", None) or {})
    source = getattr(event, "source", None)
    thread_id = getattr(source, "thread_id", None)
    if thread_id is not None:
        metadata["thread_id"] = str(thread_id)
    return metadata


def _session_key(event: Any) -> str:
    source = getattr(event, "source", None)
    platform = getattr(getattr(source, "platform", None), "value", "")
    chat_id = str(getattr(source, "chat_id", "") or "")
    user_id = str(getattr(source, "user_id", "") or "")
    thread_id = str(getattr(source, "thread_id", "") or "")
    return f"{SESSION_PREFIX}:{platform}:{chat_id}:{thread_id}:{user_id}"


def _event_text(event: Any) -> str:
    return str(getattr(event, "text", "") or "").strip()


def _normalize(value: str) -> str:
    return " ".join(str(value).casefold().split())
