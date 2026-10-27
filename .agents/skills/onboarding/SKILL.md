---
name: onboarding
description: Diagnose runtime capabilities and initialize one private job-seeker workspace after an explicit career request; never start intake during product development.
---

Read ../../../docs/job-seeker-policy.md first. Root AGENTS.md governs maintainer work; this skill activates only for an explicit career request.

## Purpose and invocation

Diagnose runtime capabilities and initialize one private job-seeker workspace after an explicit career request; never start intake during product development.

## Inputs

Runtime name, explicit external directory, interface language and any existing tracker.

## Required capabilities

Local Python 3.11+ CLI. Browser/model APIs are optional and not assumed.

## Steps

Run doctor --runtime HOST. Inspect docs/compatibility.md; initialize with --data-dir PATH init --language en or vi. Reuse existing state. Record only missing preferences and finite campaign scope. Do not import a real CV for a maintainer task.

For a new CV-first campaign, use `--data-dir PATH start-campaign --cv FILE`.
It creates a private intake packet with target 100 by default; `--target N` is
an explicit override. Read ../../../prompts/COMMUNITY_START.md and ask only for
missing material intake fields. This packet does not extract PDF/DOCX, confirm
facts, create a persistent host goal or authorize disclosure. Use supported host
extraction and verify against the original before importing text evidence.

For model routing, read ../../../docs/MODEL_ROUTING.md and use route-task with actual host model/effort/skill inventory and the existing owner. Use tools directly for deterministic work. Load only the selected skill and compact relevant context; never use a second model to classify tasks. Unavailable routes block until an explicit policy alternative is configured. A plan does not switch the running model or grant browser authority.

## Outputs

Capability result, selected workspace and compact missing-input list.

## Failure behavior

Unsupported runtime uses generic/manual instructions; missing Python returns a prerequisite, not success.

## Side-effect limits

Only local initialization after explicit workspace selection; no account, hook trust, browser or disclosure.

## Tests and examples

python scripts/kit.py doctor --runtime generic; tests/test_cli.py; examples/fictional/.
