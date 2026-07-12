# Menu Planner Menu Generation

Version: m8.v1

Use this skill to guide local menu draft generation through structured tools.

Call `menu_planner_generate_menu_draft` only when the active toolset allows it
and the required schema fields are available. Treat generated drafts as drafts
or previews. Accepted state changes remain behind Application HTTP API policy,
validation, idempotency and confirmation where required.

The Application HTTP API and Domain validation are authoritative. Do not encode
nutrition, profile, pricing, shopping or replacement business rules only in
this prompt.
