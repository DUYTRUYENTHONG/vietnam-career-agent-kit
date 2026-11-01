# Efficient observed browser work

Use only for an already selected browser task and a supported host connection.
The canonical skill, current host instructions and execution protocol retain
authority. This is an original procedure, not an installed upstream browser.

## Prepare one small action context

Carry the current job/run/request IDs, employer and requisition, exact destination,
session/tab ownership, approved answer IDs, frozen file hash, pending action,
deadline and last observed result. Load only the relevant form or recovery detail.
Conversation history and a planned session name do not prove browser isolation.

## Observe, act, verify

1. Inspect the actual page through the host's supported snapshot or screenshot.
   Prefer observed role, label or stable test ID when available. Resolve duplicate
   labels deliberately; do not select the first match without checking context.
2. Treat element references as scoped to that observation. Refresh after navigation,
   form rerender, upload, modal, validation error, user handoff or session change.
   Never carry references across tabs or reconstruct hidden form endpoints.
3. Group known independent field edits only when the host supports them and the
   controls remain stable. Then observe the result. Keep dependent choices and
   each lane's actions ordered; stop a group if a re-render invalidates its targets.
4. Reuse the exact current authority and confirmed facts; do not ask again merely
   because another tool call is needed. New required facts, changed recipients,
   files or terms need the affected scope resolved before proceeding.
5. Use host-supported readiness waits with finite deadlines. Do not add arbitrary
   sleeps, poll an unchanged page indefinitely or restart a pending submission.
   An expired login or missing dependency does not become a model-quality retry.
6. Before a possible submit, use the engine's durable unique attempt and current
   action check. On timeout or lost acknowledgement, verify read-only and preserve
   uncertainty. A successful click, upload or SDK reply is not a hiring receipt.
7. Save the observed employer/job outcome and required private visual evidence.
   Close only a completed owned tab/session after the receipt is committed; preserve
   user tabs, deliverables and unresolved handoffs. Cleanup failure does not resend.

## Check retained values before a human handoff

Finish document, source, fit, duplicate and answer review before asking the user
to complete a short-lived verification step. Confirm that controlled inputs have
retained the approved values after blur or rerender. A successful fill call does
not establish this: phone controls may keep a country prefix while dropping the
subscriber number. Use the host's documented input method and observe the result;
correct only the already approved value, without changing its meaning.

If the host redacts private fields, a redacted DOM value or comparison is not
evidence of a match or mismatch. Use supported visual inspection where available;
otherwise report that the value could not be verified. Never read hidden stores,
extract challenge tokens or change page state through evaluation.

On return from a human handoff, refresh the actual form: references and layout
may have changed. Check the current approval/expiry, retained fields, exact file,
consents, challenge status and existing attempt. Then perform only the next
permitted action. Keep unrelated research, rerendering and repeat document review
outside this short path. These ordering rules do not remove execution preflight
or host confirmation requirements.

An unchecked, disabled or expired verification control is not verified merely
because the user replied. Preserve the form and its existing attempt; never click
Submit to test readiness or allocate another attempt. A pending/uncertain submit
still resumes read-only. Reuse unchanged valid approval rather than requesting it
again, and ask only for the unresolved human step.

This is instruction-only guidance. No browser adapter, automatic challenge
handling or measured speed improvement is introduced. Bounded review cases:
retained text; country-prefix-only phone; redacted values; expired verification;
and an already pending submit. In each case, visible state and existing execution
authority determine the next action.

## Verify native and custom dropdown selections

A successful text fill is not a selected option. Some custom controls retain
their previous option or highlight the first item even after a search term was
filled. Do not press Enter assuming it will select the intended label.

Use the host's documented selection method for the observed control. A native
`selectOption({label: approvedLabel})` is appropriate only when that API and the
native select are actually available. For a custom menu, open it, observe the
current options and choose the exact approved visible option. Verify both the
selected value and the displayed label; resolve contradictions before uploading
or submitting. Never set a framework's internal store through page evaluation.

Grouping independent edits remains useful, but a partially failed group may
already have changed earlier fields. Inspect the retained values and continue
from the first unresolved field. Do not replay the whole group or trust a native
selection while a stale custom label still shows a different role or level.

## Handle file-chooser failures without losing the filled form

Start the documented chooser wait before clicking the observed upload control.
Attach a rejection handler immediately: an unattended chooser timeout can become
an unhandled rejection while the click is still waiting. Prefer the visible
associated control when the host cannot click the actual file input. Observe the
page before changing targets; do not guess another input or use hidden endpoints.

The following JavaScript recipe requires an existing supported tab, an observed
upload locator, the current exact file approval and completed execution preflight.
Its return objects are local recovery hints, not canonical action receipts:

```javascript
async function chooseApprovedFile(tab, uploadControl, approvedPath) {
  const pending = tab.playwright.waitForEvent('filechooser', {timeoutMs: 10000})
    .then(chooser => ({ok: true, chooser}), error => ({ok: false, error}));
  try {
    await uploadControl.click({timeoutMs: 10000});
  } catch (error) {
    await pending; // Drain the bounded wait; its rejection is already handled.
    return {next: 'observe', stage: 'control', error: String(error)};
  }
  const result = await pending;
  if (!result.ok) {
    return {next: 'observe', stage: 'chooser', error: String(result.error)};
  }
  try {
    await result.chooser.setFiles([approvedPath]);
  } catch (error) {
    return {next: 'observe', stage: 'attachment', error: String(error)};
  }
  return {next: 'verify-visible-attachment'};
}
```

On any failure, reconcile the same tab and selected-file state first. If browser
control resets, restore its documentation and recover the existing owned binding;
do not create another application merely because a handle was lost. Never repeat
`setFiles` until supported observation proves the earlier selection did not occur
and the existing authority still permits the action. A selected filename proves
selection, not upload completion, employer receipt or submission. The local frozen
file hash, current form review and durable pre-submit attempt remain required.

These are instruction-only host procedures. A bounded Codex in-app-browser session
on Windows exposed stale custom labels and a chooser timeout; the host version was
not identified. This does not verify another runtime, portal, SDK bridge or automatic
recovery, and supplies no measured throughput gain. Review cases: wrong highlighted
option, native/custom disagreement, partial edit failure, click failure, chooser
timeout, interrupted attachment and a previously pending submit. All must preserve
the existing approval, current form evidence and no-automatic-retry boundary.

## Choose the correct execution surface

| Surface | Appropriate use | Evidence still needed |
|---|---|---|
| Host browser tools | Permitted UI in the user's selected host | Actual supported methods, account and owned binding |
| Local browser plugin | Explicitly configured isolated local windows | Current scope, reviewed files and tested host transport |
| TinyFish Browser | Opt-in reviewed guest form with cloud disclosure | Provider scope and verified independent session |
| Public Fetch providers | Bounded public research | Source identity and operation permission; no private CV |
| Copilot SDK conversation | Host-specific conversational work | Does not create a browser context or permission |

Use [the upstream review](../../../../docs/AWESOME_COPILOT_REVIEW.md) when evaluating
an alternative. Do not auto-install its SDK or browser, reuse a personal profile,
attach an arbitrary debugging endpoint, adopt an approve-all handler or imitate
human timing to evade a site's controls. Ordinary visible browser interaction is
the goal; a source collection cannot override the host or employer's rules.
