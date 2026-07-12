# Menu Planner Intent Interpretation

Version: m8.v1

Use this skill to map a user message to the narrow Menu Planner tool catalog.

Use only structured tool names and schemas from the plugin:

- `menu_planner_get_workflow_status`
- `menu_planner_preview_profile`
- `menu_planner_commit_profile`
- `menu_planner_generate_menu_draft`
- `menu_planner_generate_recipe_draft`
- `menu_planner_preview_menu_slot_replacement`
- `menu_planner_build_shopping_list`
- `menu_planner_update_shopping_checklist_item`

The Application HTTP API and Domain validation are authoritative. If intent,
workflow state or required fields are unclear, ask for clarification or call a
read/status tool. Do not invent state from memory and do not bypass policy
hooks, confirmation, idempotency or structured tool results.
