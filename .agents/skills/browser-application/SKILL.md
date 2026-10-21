---
name: browser-application
description: Operate only explicitly approved, platform-permitted application UI through an available supported host connection, otherwise prepare a manual handoff.
---

Read ../../../docs/job-seeker-policy.md first. Root AGENTS.md governs maintainer work; this skill activates only for an explicit career request.

## Purpose and invocation

Operate only explicitly approved, platform-permitted application UI through an available supported host connection, otherwise prepare a manual handoff.

## Inputs

Exact current approval, recipient/destination, allowed mode/actions, documents/answers and visible browser state.

## Required capabilities

A supported authorized browser plus execution/attempt guards. Slice 1 has no live browser adapter.

## Steps

Use handoff now. A later permitted adapter must inspect required fields/consents, fill small groups and re-observe. Only APPROVED_BATCH may submit a listed job after all guards and host confirmations. Persist attempt before final action; uncertain outcomes never retry.

## Outputs

Permitted observed outcome or accurate manual handoff with documents, missing questions, destination verification and steps.

## Failure behavior

Wrong account, unknown destination, challenge, missing approval or guard stops that action. No credential extraction, stealth, private endpoints or assessments.

## Side-effect limits

No browser connection is granted by this skill. Only one designated operator; no profile-wide changes or unapproved messages.

## Tests and examples

python scripts/kit.py --data-dir PATH handoff --job-id ID; tests/test_cli.py; local portal tests pending.
