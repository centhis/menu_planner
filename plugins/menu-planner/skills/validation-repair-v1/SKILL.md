# Menu Planner Validation Repair

Version: m8.v1

Use this skill to repair a local draft payload after a structured validation
error. Repair only the payload fields named by stable error codes or fields in
the tool result.

Use structured errors, `retryable`, `warnings` and `next_allowed_actions` from
the tool result. Do not retry indefinitely. Treat policy, user mismatch,
confirmation, idempotency and workflow errors as hard stops.

The Application HTTP API and Domain validation are authoritative. A repaired
payload must be sent back through the same structured tool boundary.
