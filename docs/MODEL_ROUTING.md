# Model routing and context budgets

Run `python scripts/kit.py route-task --packet task.json`. This read-only command
needs no candidate workspace. It returns the normal versioned outcome envelope,
keeps the existing owner, and makes no model, network or browser calls. The host
must apply a successful plan through a supported explicit override; a plan does
not switch an already running agent. Blocked plans must not dispatch.

The routing packet is defined in `schemas/routing.schema.json`. Required fields
are `schema_version: "1.0"`, `owner_id`, `task_kind`, `risk` and `complexity`.
Agent tasks also need the actual `available_models` map (exact model IDs to
supported effort arrays), `available_skill_names`, and ordered `skill_candidates`.
The inventory is caller-reported, not a verified provider entitlement.

| Deterministic task metadata | Default route |
|---|---|
| test, build, format, status, metrics | Direct tool; no model |
| planning or consolidated_review | gpt-6-astra / high |
| high risk, complex, auth or data_migration | gpt-5.6-sol / high |
| low risk and simple | gpt-5.6-luna / low |
| Remaining agent tasks | gpt-5.6-terra / medium |

These defaults preserve the requested policy; they are not a claim that every
host offers those IDs or that they are the cheapest. An unavailable ID or effort
blocks with its exact reason. An explicit `policy` may replace the four roles
(`planning`, `simple`, `routine`, `complex`), each containing `model` and `effort`.
Never silently substitute a model or assume Codex model availability proves an
API provider supports it. Hosts without per-task overrides can use the current
owner, but must report that selection was not applied rather than claiming a
model switch.

Example for a tool task (no model inventory required):

```json
{"schema_version":"1.0","owner_id":"existing-owner","task_kind":"metrics","risk":"low","complexity":"simple"}
```

`previous_failure` contains `kind`, positive integer `count`, and `model`.
Credentials/infrastructure failures stop retries. A single failed simple code
task can escalate once from the configured simple model to the configured
complex model, if available. Repeated failures and other automatic escalations
block. Missing tools, skills or credentials are not model-quality failures.

For token-efficient execution:

1. Use deterministic commands for import, deduplication, validation, rendering,
   tracker export, tests and metrics. Do not ask a second model to classify work.
2. Keep one existing owner per workstream. Do not create an agent for routing.
   Load only the selected skill and its necessary references.
3. Pass compact deltas: relevant job requirements, confirmed fact IDs/claims,
   unresolved questions, changed files and acceptance criteria. Keep source paths
   and hashes available for inspection. Avoid forwarding full campaign history,
   repeated unchanged tracker rows or unrelated CVs.
4. Reuse confirmed facts and prepared artifacts by fingerprint. Freshness checks
   still run before disclosures; a context shortcut grants no authorization.
5. Consolidate review at a meaningful feature/batch gate; escalate early for real
   security or data-loss concerns. Preserve document and submission checks.
6. Record actual input/output tokens, elapsed time, acceptance outcome and pricing
   only when supplied by the host. Unknown usage or price stays unknown. The
   planner's `usage_cost_usd` is null. No quota-to-dollar conversion or estimated
   savings is reported, and no telemetry is installed.

Local tests cover selection, unavailable inventory, explicit overrides, failure
limits and CLI errors. They do not invoke models or certify native dispatch.
