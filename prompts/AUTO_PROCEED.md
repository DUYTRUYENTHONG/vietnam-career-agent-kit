# Continue applications and close completed tabs

Use this optional prompt for an explicitly requested job-seeker campaign. It is
instruction-only: it does not create standing authorization, authenticate an
approval, acquire a browser or install a background worker. Replace bracketed
fields with the candidate's actual scope. Read STARTUP.md, MASTER_PROMPT.md and
the selected host's browser rules first.

## Reusable campaign prompt

```text
Continue my campaign in [existing external private workspace] toward [target]
new suitable confirmed applications for [role families/seniority], limited to
[locations, remote eligibility, employment type and exclusions]. Reuse the
canonical ledger, confirmed profile, answer bank and valid authorization.
Skip prior applications and preserve uncertain attempts for read-only recovery.

Proceed automatically with routine steps when the exact recipient, destination,
files, answers, consents, actions, cap and expiry match valid authority and the
source and host permit them. Do not ask again for unchanged local approval.
If no matching authority exists, complete independent preparation and identify
the smallest missing scoped decision. Never manufacture an approval record.

Evaluate employer requirements against my evidence. Answer yes only when the
specific claim is supported; preserve confirmed no answers. A job description
does not add qualifications to my profile. Unknown required answers remain
pending; omit optional unknowns. Never infer citizenship, years, proficiency,
salary basis or legal consent. Obtain any specific confirmation required by the
host at action time. Move to another suitable job while a vacancy is blocked.

Tailor supported evidence, inspect every rendered page and pin the reviewed
files and exact answers in each manifest. Use launch-execution for a new run,
check-action before each permitted browser mutation and advance-execution to
record an observed receipt and obtain the next step. Reconcile existing runs
without replaying outstanding actions. Reserve a unique attempt before the
single final submit action. Never resubmit an uncertain outcome.

Close each completed application tab after saving its visible confirmation,
screenshot and immutable receipt. Use cleanup-execution to obtain the exact
bridge/binding, verify that it is still the same agent-created application tab,
then close it through supported host tools. Verify absence and record-cleanup
with the actual result. Preserve user-owned or unrelated tabs, deliverables and
uncertain/manual handoffs. Close only the matching application tab, not the
whole browser. A failed close leaves the application confirmed and cleanup
pending; it never triggers another submission or changes application counts.

After every pass, export the tracker table with employer/role, source, status,
blocker, next step, update time and separate cleanup status. Count only qualifying
new confirmed receipts. Report actual throughput separately from the campaign
total. Continue successive finite batches within valid scope; do not claim a
background campaign or completion before the target is reconciled.
```

## Harness contract and limits

The existing [standing authorization](../docs/STANDING_AUTHORIZATION.md) and
[execution/cleanup protocol](../docs/execution.md) enforce local scope and
attempt bookkeeping. A host bridge may implement `close_application_tab(request)`;
otherwise it returns cleanup instructions for the operator. The CLI cannot
close tabs itself. Local receipts do not independently prove browser ownership,
user intent or employer acceptance; the host must observe and report them.

For a fictional bridge, expected outcomes are:

| Observation | Application state | Cleanup |
|---|---|---|
| Saved exact-job confirmation and screenshot | Confirmed | Close matching agent tab; verify absence; acknowledge |
| No reliable receipt after final action | Uncertain | Preserve for reconciliation; never submit again |
| Tab reused for another application | Confirmed original | Reject stale closure request |
| Close fails or host lacks closure capability | Confirmed | Pending with reason; no submission retry |
| Matching tab already absent and verified | Confirmed | Record `already_absent` with verified ownership/intent |

These existing engine invariants are covered in `tests/test_cleanup.py`.
This prompt adds no schema, executable hooks, global auto-yes setting, native
integration certification or live throughput guarantee.
