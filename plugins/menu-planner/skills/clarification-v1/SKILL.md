# Menu Planner Clarification

Version: m8.v1

Use this skill when the requested Menu Planner action is missing fields needed
by a strict tool schema.

Ask for the smallest missing structured input. Prefer the current workflow
status and `next_allowed_actions` from structured tool results over guesses.
Do not collect secrets, credentials, tokens or private runtime configuration.

The Application HTTP API and Domain validation are authoritative. A
clarification answer is only candidate input for a later structured tool call;
it is not committed state and it cannot replace confirmation.
