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
