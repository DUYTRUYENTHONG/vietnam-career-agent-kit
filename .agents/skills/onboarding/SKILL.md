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

## Outputs

Capability result, selected workspace and compact missing-input list.

## Failure behavior

Unsupported runtime uses generic/manual instructions; missing Python returns a prerequisite, not success.

## Side-effect limits

Only local initialization after explicit workspace selection; no account, hook trust, browser or disclosure.

## Tests and examples

python scripts/kit.py doctor --runtime generic; tests/test_cli.py; examples/fictional/.
