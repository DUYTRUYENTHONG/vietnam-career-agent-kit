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

A supported authorized host browser and the execution CLI. Read ../../../docs/execution.md for protocol 1.0 and measured limits. No standalone browser driver is bundled.

## Steps

1. Inspect resume and existing applications. Verify the actual destination/account and current permission for each operation. Unknown permission stays manual. Do not activate this workflow for maintainer tasks.
2. Obtain an exact reviewed manifest binding the bridge ID, runtime, candidate, jobs, answers, consents, documents, expiry and submission limit. Preparation-only approvals cannot execute. Do not fabricate candidate approval proof.
3. Start one run with start-execution. Request one next-action. Bind inspect to the explicitly authorized tab and exact visible employer/requisition/destination. Map visible labels to approved answer IDs.
4. Immediately before the requested action call check-action, inspect fresh UI and satisfy any host/tool confirmation. A pending request does not override expiry, revocation, platform rules or host policy. Block challenges, legal agreements, new required fields/consents or redirects before any further mutation.
5. Perform only the requested action through supported host browser tools. Never use private browser APIs, exported sessions or an alternate tool to avoid a denial. Fill exact values, upload only the frozen approved file and verify visible file selection/byte identity using supported evidence. Re-observe after every action.
6. Save an observed receipt in the external private workspace and prefer advance-execution to record it and return one successor request. Do not call next-action again when that response already contains a request. record-action plus next-action remains compatible. Successful inspect/fill/upload/review require a fresh unchanged form observation. Review must match visible answers, consent choices and document hash. See protocol for exact keys. Do not copy expectations into receipts without observing the UI.
7. Repeat sequentially. Only APPROVED_BATCH returns submit, after a durable unique attempt has already been committed. Click once. Acknowledge it, then verify visible employer/requisition/success and retain a private screenshot. An issued click is not confirmation.
8. Stop on non-ok outcomes. A pending submit resumes as read-only verify; it never returns another submit. A terminal unknown may use recover-execution for reconciliation only. Do not retry that vacancy, continue other entries or infer success. ASSIST ends after review without submitting.

## Outputs

Permitted observed outcome or accurate manual handoff with documents, missing questions, destination verification and steps. Finish each pass with the application-tracking skill's timestamped tracker table. Reuse an existing still-current exact approved scope without requesting the same approval again; host confirmations and material scope changes still apply.

## Failure behavior

Wrong account, unknown destination, challenge, missing approval or guard stops that action. No credential extraction, stealth, private endpoints or assessments.

## Side-effect limits

No browser connection is granted by this skill. Only one designated operator; no profile-wide changes or unapproved messages.

## Tests and examples

python scripts/kit.py --data-dir PATH execution-status --run-id ID; tests/test_execution.py; scripts/serve_fixture.py is a separate local UI smoke fixture. Native real-employer integration remains unverified.
