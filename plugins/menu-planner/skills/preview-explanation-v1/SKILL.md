# Menu Planner Preview Explanation

Version: m8.v1

Use this skill to explain a structured preview, confirmation request or tool
result to the user.

Base the explanation on `success`, `operation_id`, `correlation_id`,
`entity_id`, `entity_version`, `data`, `warnings`, `errors`, `retryable` and
`next_allowed_actions`. Keep the explanation faithful to the result payload.

The Application HTTP API and Domain validation are authoritative. Do not claim
that a draft, preview or checklist item was committed unless the structured
tool result says so.
