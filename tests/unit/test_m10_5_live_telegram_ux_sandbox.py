from __future__ import annotations

import importlib.util
import pathlib
import sys
import unittest
from typing import Any

ROOT = pathlib.Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "m10_5_live_telegram_ux_sandbox.py"


def _load_script() -> Any:
    spec = importlib.util.spec_from_file_location("m10_5_live_ux", SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["m10_5_live_ux"] = module
    spec.loader.exec_module(module)
    return module


class M105LiveTelegramUxSandboxTests(unittest.TestCase):
    def test_screens_are_demo_labeled_and_not_active_state(self) -> None:
        script = _load_script()

        self.assertIn(script.DEMO_LABEL, script.home_text())
        self.assertIn(script.DEMO_LABEL, script.menu_ready_text())

        for screen_id in script.CORE_SCREEN_IDS:
            with self.subTest(screen_id=screen_id):
                text = script.screen_text(screen_id)
                self.assertIn(script.DEMO_LABEL, text)
                self.assertIn("Выбери действие ниже.", text)
                self.assertNotIn("confirmation_id", text)
                self.assertNotIn("активное состояние", text.casefold())

    def test_callback_data_is_short_and_stable(self) -> None:
        script = _load_script()

        callback_values = script.callback_data_values()

        self.assertEqual(
            callback_values,
            ("cl:<clarify_id>:0", "cl:<clarify_id>:0"),
        )
        self.assertTrue(
            all(len(value.encode("utf-8")) <= 64 for value in callback_values)
        )
        self.assertNotIn("{", str(callback_values))
        self.assertNotIn("profile", str(callback_values).casefold())
        self.assertEqual(script.CALLBACK_PREFIX, "cl:")

    def test_dry_run_is_safe_and_network_free(self) -> None:
        script = _load_script()

        result = script.dry_run_result()

        self.assertTrue(result["ok"])
        self.assertFalse(result["telegram_network_used"])
        self.assertFalse(result["credentials_used"])
        self.assertTrue(result["demo_only"])
        self.assertFalse(result["active_state_changed"])
        self.assertLessEqual(result["callback_data_max_static_bytes"], 64)
        self.assertEqual(result["target_runtime_path"], "hermes_native_clarify")
        self.assertEqual(result["button_label_mode"], "user_visible_text")
        self.assertFalse(result["global_close_button"])
        self.assertEqual(result["text_input_policy"], "only_declared_screens")
        self.assertEqual(result["button_only_text_policy"], "block_inside_sandbox")
        self.assertEqual(
            result["prompt_injection_policy"],
            "planned_schema_guard_for_text_screens",
        )
        self.assertEqual(result["ux_model"], "light_menu_planning_flow")
        self.assertEqual(result["screen_count"], 15)
        self.assertEqual(
            result["primary_flow_taps"],
            {
                "generate_menu_from_empty_home": 1,
                "return_to_active_home_after_menu": 1,
                "open_shopping_list_from_active_home": 1,
                "change_menu_from_active_home": 1,
                "open_menu_text_edit_from_active_home": 1,
            },
        )
        self.assertEqual(set(result["screens"]), set(script.CORE_SCREEN_IDS))

    def test_hermes_native_prompt_uses_clarify_without_state_change(self) -> None:
        script = _load_script()

        prompt = script.hermes_native_prompt()

        self.assertIn("встроенный clarify tool", prompt)
        self.assertIn("Предложи ровно один вариант: Составить меню.", prompt)
        self.assertIn("одним вариантом: Главная.", prompt)
        self.assertIn(script.home_with_menu_text(), prompt)
        self.assertIn("Не меняй активное состояние продукта.", prompt)
        self.assertIn(script.DEMO_LABEL, prompt)
        self.assertNotIn("ux:", prompt)

    def test_clarify_demo_launcher_is_safe_and_russian(self) -> None:
        script = _load_script()

        self.assertEqual(
            script.HERMES_NATIVE_ENTRY_COMMAND,
            "Открыть UX-песочницу Menu Planner",
        )
        self.assertIn("лёгкий UX", script.CLARIFY_DEMO_LAUNCHER_TEXT)
        self.assertIn("демо", script.CLARIFY_DEMO_LAUNCHER_TEXT)
        self.assertNotIn("TELEGRAM_BOT_TOKEN", script.CLARIFY_DEMO_LAUNCHER_TEXT)

    def test_co_design_catalog_covers_core_screens(self) -> None:
        script = _load_script()

        catalog = script.screen_catalog()

        self.assertEqual(set(catalog), set(script.CORE_SCREEN_IDS))
        for screen_id, screen in catalog.items():
            with self.subTest(screen_id=screen_id):
                self.assertIn(script.DEMO_LABEL, screen["text"])
                self.assertIn("Выбери действие ниже.", screen["text"])
                self.assertTrue(screen["ux_logic"])
                self.assertTrue(screen["suggested_improvements"])
                self.assertTrue(screen["feedback_status"])

    def test_co_design_prompt_is_safe_and_complete(self) -> None:
        script = _load_script()

        prompt = script.co_design_prompt()

        self.assertIn("Используй встроенный clarify tool", prompt)
        self.assertIn("Не меняй активное состояние продукта.", prompt)
        self.assertIn("что изменить", prompt)
        self.assertNotIn("TELEGRAM_BOT_TOKEN", prompt)
        self.assertNotIn("auth.json", prompt)
        for screen_id in script.CORE_SCREEN_IDS:
            with self.subTest(screen_id=screen_id):
                self.assertIn(screen_id, prompt)

    def test_co_design_messages_are_chunked_for_telegram(self) -> None:
        script = _load_script()

        messages = script._co_design_messages()
        joined = "\n".join(messages)

        self.assertGreater(len(messages), 1)
        self.assertTrue(all(len(message) <= 3200 for message in messages))
        self.assertIn("ДЕМО-ревью: ничего не сохраняю.", messages[0])
        self.assertIn("лёгкий сценарий планирования меню", messages[0])
        self.assertNotIn("Please review these core screens.", joined)
        self.assertNotIn("TELEGRAM_BOT_TOKEN", joined)
        for screen_id in script.CORE_SCREEN_IDS:
            with self.subTest(screen_id=screen_id):
                self.assertIn(script.screen_text(screen_id), joined)

    def test_telegram_preview_messages_are_static_action_previews(self) -> None:
        script = _load_script()

        previews = script._telegram_preview_messages()

        self.assertEqual(len(previews), len(script.CORE_SCREEN_IDS))
        for preview in previews:
            with self.subTest(screen_id=preview["screen_id"]):
                self.assertIn("Выбери действие ниже.", preview["text"])
                self.assertGreaterEqual(len(preview["buttons"]), 2)

    def test_settings_edit_buttons_are_user_visible_labels(self) -> None:
        script = _load_script()

        buttons = script._RU_PREVIEWS["settings_edit"]["buttons"]

        self.assertEqual(
            buttons,
            ("Назад к настройкам", "Главная"),
        )
        self.assertFalse({"1", "2", "3"}.intersection(buttons))

    def test_choice_tree_has_existing_targets_and_matching_button_counts(self) -> None:
        script = _load_script()

        self.assertEqual(
            set(script._HERMES_CLARIFY_NAVIGATION),
            set(script.CORE_SCREEN_IDS),
        )
        for screen_id in script.CORE_SCREEN_IDS:
            with self.subTest(screen_id=screen_id):
                buttons = script._RU_PREVIEWS[screen_id]["buttons"]
                targets = script._HERMES_CLARIFY_NAVIGATION[screen_id]

                self.assertEqual(len(buttons), len(targets))
                self.assertTrue(set(targets).issubset(set(script.CORE_SCREEN_IDS)))

    def test_settings_branch_does_not_generate_menu(self) -> None:
        script = _load_script()

        self.assertNotIn("Составить меню", script._RU_PREVIEWS["settings"]["buttons"])
        self.assertNotIn("menu_ready", script._HERMES_CLARIFY_NAVIGATION["settings"])
        self.assertEqual(
            script._HERMES_CLARIFY_NAVIGATION["settings"],
            ("store_sources", "settings_edit", "home"),
        )

    def test_menu_result_returns_to_active_home_without_awkward_buttons(self) -> None:
        script = _load_script()

        menu_buttons = script._RU_PREVIEWS["menu_ready"]["buttons"]
        home_with_menu_buttons = script._RU_PREVIEWS["home_with_menu"]["buttons"]
        home_with_menu_text = script.home_with_menu_text()

        self.assertEqual(menu_buttons, ("Главная", "Изменить меню"))
        self.assertNotIn("Всё ок", menu_buttons)
        self.assertNotIn("Заменить блюдо", menu_buttons)
        self.assertNotIn("Покупки", menu_buttons)
        self.assertEqual(
            script._HERMES_CLARIFY_NAVIGATION["menu_ready"],
            ("home_with_menu", "quick_adjust"),
        )
        self.assertIn("Покупки", home_with_menu_buttons)
        self.assertIn("Рецепт", home_with_menu_buttons)
        self.assertIn("Изменить меню", home_with_menu_buttons)
        self.assertIn("Настройки", home_with_menu_buttons)
        self.assertNotIn("Составить меню", home_with_menu_buttons)
        self.assertIn("осталось купить", home_with_menu_text)
        self.assertIn("ужин: боул с чечевицей", home_with_menu_text)
        self.assertEqual(
            script._HERMES_CLARIFY_NAVIGATION["home_with_menu"],
            ("shopping_list", "recipe_view", "quick_adjust", "settings"),
        )

    def test_change_menu_is_text_first_not_meal_button_choice(self) -> None:
        script = _load_script()

        change_text = script.quick_adjust_text()
        change_buttons = script._RU_PREVIEWS["quick_adjust"]["buttons"]
        preview_text = script.replacement_options_text()

        self.assertIn("Напиши, что изменить", change_text)
        self.assertIn("замени пасту во вторник", change_text)
        self.assertIn("сделай ужины дешевле", change_text)
        self.assertIn("покажу предпросмотр нового меню", change_text)
        self.assertEqual(change_buttons, ("Главная", "Покупки"))
        self.assertNotIn("Вторник: паста", change_buttons)
        self.assertNotIn("выбери конкретный приём пищи", change_text)
        self.assertEqual(
            script._HERMES_CLARIFY_NAVIGATION["quick_adjust"],
            ("home_with_menu", "shopping_list"),
        )
        self.assertIn("Предпросмотр правки", preview_text)
        self.assertIn("без подтверждения меню не изменится", preview_text)
        self.assertEqual(
            script._HERMES_CLARIFY_NAVIGATION["replacement_options"],
            ("home_with_menu", "quick_adjust"),
        )

    def test_store_sources_are_user_selected_without_text_input_or_live_prices(self) -> None:
        script = _load_script()

        settings_text = script.settings_text()
        store_sources_text = script.store_sources_text()
        store_selection_text = script.store_selection_text()
        store_selection_result_text = script.store_selection_result_text()
        store_refresh_text = script.store_refresh_text()

        self.assertIn("Источники цен", script._RU_PREVIEWS["settings"]["buttons"])
        self.assertIn("выбраны: Перекрёсток, ВкусВилл", settings_text)
        self.assertIn("не подключён: Лента", settings_text)
        self.assertIn("по умолчанию источники выключены", settings_text)
        self.assertIn("магазины не добавляются свободным текстом", settings_text)
        self.assertIn("Выбраны", store_sources_text)
        self.assertIn("Доступны", store_sources_text)
        self.assertIn("Перекрёсток - навык Hermes", store_sources_text)
        self.assertIn("ВкусВилл - навык Hermes", store_sources_text)
        self.assertIn("Лента - не подключена", store_sources_text)
        self.assertIn("по требованию", store_sources_text)
        self.assertIn("обновляются только выбранные источники", store_sources_text)
        self.assertIn("2+ источника дают группы покупок", store_sources_text)
        self.assertIn("Подключить Ленту", script._RU_PREVIEWS["store_selection"]["buttons"])
        self.assertIn("Отключить ВкусВилл", script._RU_PREVIEWS["store_selection"]["buttons"])
        self.assertIn("минимум один источник нужен для цен", store_selection_text)
        self.assertIn("кнопки показывают выбор, но ничего не сохраняют", store_selection_text)
        self.assertIn("1 источник - один список покупок", store_selection_result_text)
        self.assertIn("2+ источника - группы по каждому магазину", store_selection_result_text)
        self.assertIn("цены и наличие не загружаю", store_sources_text)
        self.assertIn("запущу навыки только выбранных магазинов", store_refresh_text)
        self.assertIn("меню и покупки не изменятся без подтверждения", store_refresh_text)
        self.assertNotIn("введи магазин", settings_text.casefold())
        self.assertNotIn("напиши магазин", settings_text.casefold())
        self.assertNotIn("живые цены", store_sources_text.casefold())

    def test_store_sources_navigation_does_not_generate_menu(self) -> None:
        script = _load_script()

        self.assertNotIn("menu_ready", script._HERMES_CLARIFY_NAVIGATION["store_sources"])
        self.assertNotIn("menu_ready", script._HERMES_CLARIFY_NAVIGATION["store_selection"])
        self.assertNotIn(
            "menu_ready",
            script._HERMES_CLARIFY_NAVIGATION["store_selection_result"],
        )
        self.assertNotIn("menu_ready", script._HERMES_CLARIFY_NAVIGATION["store_refresh"])
        self.assertEqual(
            script._HERMES_CLARIFY_NAVIGATION["store_sources"],
            ("store_selection", "store_refresh", "settings", "home"),
        )
        self.assertEqual(
            script._HERMES_CLARIFY_NAVIGATION["store_selection"],
            ("store_selection_result", "store_selection_result", "store_sources"),
        )
        self.assertEqual(
            script._HERMES_CLARIFY_NAVIGATION["store_selection_result"],
            ("store_sources", "shopping_list", "store_selection"),
        )
        self.assertEqual(
            script._HERMES_CLARIFY_NAVIGATION["store_refresh"],
            ("store_sources", "settings"),
        )

    def test_shopping_list_is_grouped_by_selected_store_sources(self) -> None:
        script = _load_script()

        menu_ready_text = script.menu_ready_text()
        shopping_text = script.shopping_list_text()

        self.assertIn("покупки сгруппированы по выбранным магазинам", menu_ready_text)
        self.assertIn("Перекрёсток:", shopping_text)
        self.assertIn("ВкусВилл:", shopping_text)
        self.assertIn("2 источника выбраны", shopping_text)
        self.assertNotIn("Лента:", shopping_text)
        self.assertNotIn("одним списком", menu_ready_text.casefold())
        self.assertNotIn("одним списком", shopping_text.casefold())

    def test_tree_avoids_static_dead_end_self_loops(self) -> None:
        script = _load_script()

        for screen_id, targets in script._HERMES_CLARIFY_NAVIGATION.items():
            with self.subTest(screen_id=screen_id):
                self.assertNotIn(screen_id, targets)

    def test_full_demo_prompt_uses_hermes_clarify_navigation(self) -> None:
        script = _load_script()

        prompt = script.hermes_native_full_demo_prompt()

        self.assertIn("clarify tool", prompt)
        self.assertIn("callback namespace должен быть cl:*", prompt)
        self.assertIn("Не вызывай Menu Planner tools", prompt)
        self.assertIn("не показывай технические статусы", prompt)
        self.assertNotIn("dm:", prompt)
        self.assertNotIn("pv:", prompt)
        self.assertEqual(
            set(script._HERMES_CLARIFY_NAVIGATION),
            set(script.CORE_SCREEN_IDS),
        )
        for screen_id in script.CORE_SCREEN_IDS:
            with self.subTest(screen_id=screen_id):
                self.assertIn(f"screen_id: {screen_id}", prompt)
                for target in script._HERMES_CLARIFY_NAVIGATION[screen_id]:
                    self.assertIn(target, script.CORE_SCREEN_IDS)

    def test_unsupported_callback_namespaces_are_declared_rejected(self) -> None:
        script = _load_script()

        result = script.dry_run_result()
        self.assertEqual(result["telegram_gateway_callback_namespace"], "cl:*")
        self.assertEqual(
            result["unsupported_callback_namespaces"],
            ["dm:*", "pv:*", "ux:*"],
        )
        self.assertNotIn("demo_callback_data", result)
        self.assertLessEqual(result["callback_data_max_static_bytes"], 64)


if __name__ == "__main__":
    unittest.main()
