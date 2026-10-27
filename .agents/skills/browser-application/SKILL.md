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

A supported authorized host browser and the execution CLI. Read ../../../docs/execution.md for protocol 1.0 and measured limits. Optional experimental TinyFish Browser uses separate cloud scope and a client dependency; see ../../../docs/TINYFISH_BROWSER.md.

## Steps

For dynamic forms and compact browser context, load references/observed-ui.md
only when needed. Use current observed controls, dependency-aware action groups
and finite readiness waits; preserve the execution checks and host-specific APIs.

Firecrawl and TinyFish Fetch are public research, not application bridges.
TinyFish Browser is opt-in for explicit single-page guest forms. Preview its
exact cloud/form fingerprint, review the extra provider disclosure and start
with one worker. It never reuses host logins or submits autonomous Agent goals.
Never convert a host-bound manifest into
cloud disclosure, send private files to a research provider, or fabricate staged
receipts after an autonomous remote-agent application. The six-stage host loop
and fresh action checks below remain required. See ../../../docs/FAST_WEB.md.

1. Inspect resume and existing applications. Verify the actual destination/account and current permission for each operation. Unknown permission stays manual. Do not activate this workflow for maintainer tasks.
2. Obtain an exact reviewed manifest binding the bridge ID, runtime, candidate, jobs, answers, consents, documents, expiry and submission limit. Preparation-only approvals cannot execute. Do not fabricate candidate approval proof.
3. Start one run with start-execution. Request one next-action. Bind inspect to the explicitly authorized tab and exact visible employer/requisition/destination. Map visible labels to approved answer IDs.
4. Immediately before the requested action call check-action, inspect fresh UI and satisfy any host/tool confirmation. A pending request does not override expiry, revocation, platform rules or host policy. Block challenges, legal agreements, new required fields/consents or redirects before any further mutation.
5. Perform only the requested action through supported host browser tools. Never use private browser APIs, exported sessions or an alternate tool to avoid a denial. Fill exact values, upload only the frozen approved file and verify visible file selection/byte identity using supported evidence. Re-observe after every action.
6. Save an observed receipt in the external private workspace and prefer advance-execution to record it and return one successor request. Do not call next-action again when that response already contains a request. record-action plus next-action remains compatible. Successful inspect/fill/upload/review require a fresh unchanged form observation. Review must match visible answers, consent choices and document hash. See protocol for exact keys. Do not copy expectations into receipts without observing the UI.
7. Repeat sequentially within each job lane. Opt-in isolated parallel lanes use the concurrent-batch protocol below. Only APPROVED_BATCH returns submit, after a durable unique attempt has already been committed. Click once. Acknowledge it, then verify visible employer/requisition/success and retain a private screenshot. An issued click is not confirmation.
8. Stop on non-ok outcomes. A pending submit resumes as read-only verify; it never returns another submit. A terminal unknown may use recover-execution for reconciliation only. Do not retry that vacancy or infer success. Sequential runs stop; independent parallel lanes may continue under their own valid scope. ASSIST ends after review without submitting.

For mailbox duplicate/receipt checks, distinguish exact application evidence
from related search suggestions. Prefer Most recent when offered, wait for the
query to settle, and verify the actual message's account, recipients, role and
date. Missing email evidence never authorizes resubmission. Read the mailbox
search section in ../../../docs/execution.md; do not collect unrelated mail.

For email applications, inspect the matching conversation for an immediate
delivery rejection during the bounded verify pass. A Sent message does not
override a mailbox-not-found response. Save both privately, return a failed
verify receipt with the observed reason, and do not confirm or resend. The
current engine uses its broader non-confirmed state; automatic late-bounce
reclassification is not implemented. See the email verification section in
../../../docs/execution.md before reporting counts or closing a completed tab.

## Optional local MCP plugins

Draft and review application emails through the application-tailoring skill's
references/evidence-writing.md before freezing the exact package. That writing
workflow never grants disclosure or send authority.

Read ../../../docs/LOCAL_PLUGINS.md for Gmail OAuth and isolated local employer
windows. Use the same canonical workspace and exact bridge-specific reviewed
manifests. Login does not approve applications. Verify the connected sender;
never create approval evidence through a tool. Gmail API acknowledgement proves
sending, not employer delivery. On a lost acknowledgement, preserve the uncertain
attempt and never resend. Local browsing stops on new terms, challenges, frames
or origin changes; user login stays inside its dedicated window. No imported
personal browser profiles, cookies or passwords. Native host compatibility must
be verified separately from stdio protocol tests.

## Standing authorization

An exact manifest may derive from approved standing campaign authority. Reuse
matching authority without repeat local approval prompts; check-action still
rechecks the parent. Never treat standing consent as a host action-time decision.
Report unresolved host confirmations as blockers. After parent revocation or
expiry, issued submits permit read-only recovery only. See
../../../docs/STANDING_AUTHORIZATION.md.

Use launch-execution for a new standing-authorized run to receive its initial
request without separate authorize/start/next calls. Repeated launch returns
existing-run reconciliation metadata, not a duplicate action. See execution.md.

## Completed-tab cleanup

When the candidate requested cleanup, handle cleanup.requests returned after a
confirmed receipt is committed. Verify the saved screenshot and the exact
bridge/binding in the host's agent-created tab registry and refresh the visible
employer/requisition immediately before closing that tab through
supported tools. Preserve unrelated/user-owned tabs, explicit deliverables and
all uncertain/manual handoffs. Record the observed closed/already_absent result
with record-cleanup; never manufacture it. A failed close leaves the application
confirmed and cleanup pending. Do not resubmit. cleanup-execution resumes this
work separately without renewing disclosure authority. See execution.md.
Bindings reused for later applications are ineligible. Recheck cleanup-execution
before acting on earlier output. Track cleanup status separately from application
blockers; a failed close never cancels the saved submission.

## Outputs

For rate targets, use small exact finite batches and record actual confirmation
time; see ../../../docs/THROUGHPUT.md. All-entry checks still run for every action.
Do not put 100 jobs in one manifest merely to pursue a 100/hour KPI, omit required
checks, infer missing answers or replay a pending action to raise throughput.

Permitted observed outcome or accurate manual handoff with documents, missing questions, destination verification and steps. Finish each pass with the application-tracking skill's timestamped tracker table. Reuse an existing still-current exact approved scope without requesting the same approval again; host confirmations and material scope changes still apply.

## Failure behavior

Wrong account, unknown destination, challenge, missing approval or guard stops that action. No credential extraction, stealth, private endpoints or assessments.

## Side-effect limits

No browser connection is granted by this skill. Only one designated operator; no profile-wide changes or unapproved messages.

## Tests and examples

python scripts/kit.py --data-dir PATH execution-status --run-id ID; tests/test_execution.py; scripts/serve_fixture.py is a separate local UI smoke fixture. Native real-employer integration remains unverified.

## Concurrent batches

For explicitly authorized batches, use ../../../docs/PARALLEL_APPLICATIONS.md and ../../../prompts/ten-job-batch.md. Keep the above action sequence per lane; only independent isolated bindings may progress concurrently. One coordinator writes the ledger. Never use a shared tab across workers.

## Optional BrowserAct host

When BrowserAct is explicitly selected and the host permits it, read
../../../docs/BROWSERACT.md. `browser-act-plan` checks an already-issued request
and returns offline session/state argument arrays. It does not launch a browser
or translate fill/upload/submit; those return manual_required. Recheck the
listed canonical preflight before any host action. Keep one owned session per
job, refresh compact state after UI changes and preserve unknown outcomes for
read-only recovery. Same-browser sessions share cookies; shared accounts use
one worker. A planned session name is not proof of live isolation.
