# Real campaign results — public, anonymized snapshot

**100-application milestone reached; 120 confirmed submissions as of 29 October
2026.** The private tracker records three interview invitations and one assessment
request. These are recruiter/TA response outcomes, not job offers or completed
interviews. Raw CVs, recruiter contacts, messages, receipts, employer identities
and account details remain private.

![120 confirmed submissions and latest recorded response stages](diagrams/campaign-results.svg)

| Latest recorded response stage | Applications | What it means |
|---|---:|---|
| Interview invitation | 3 | Verify schedule and reply; attendance is not inferred |
| Assessment / recorded-interview request | 1 | Candidate task requested; not an offer or completed assessment |
| Employer rejection | 3 | Later outcome; original submission remains in cumulative history |
| Receipt / screening acknowledgment | 39 | Acknowledgment, not a shortlist or interview |
| No matching reply found | 67 | No match within the recorded mailbox-review scope |
| Recently sent; response review pending | 7 | Sending verified; no comprehensive response review yet |
| **Total confirmed submissions** | **120** | **No job offers observed** |

Four uncertain attempts and one historical user-reported application are excluded.
Response checks are incremental and retain their individual dates: this is not a
fresh full-inbox audit of all 120 applications. A pending review differs from a
review that found no matching reply.

[Current aggregate JSON](../examples/community/campaign-results-2026-10-29.json) ·
[Archived 27 October 100-row tracker](../examples/community/campaign-tracker-2026-10-27.md) ·
[Archived CSV](../examples/community/campaign-tracker-2026-10-27.csv) ·
[Archived 100-application summary](../examples/community/campaign-results-2026-10-27.json)

The archived rows remain a dated milestone snapshot; they are not the live
120-application tracker. Public snapshots never become another user's progress.

## Recruiter / TA contact and next steps

The campaign received interview invitations for three applications and an
assessment request for one. Private records preserve the sender, exact role,
message date, timezone, requested action and evidence. No recruiter email list or
private correspondence is distributed with this kit.

| Response | Candidate's next step | Record before updating status |
|---|---|---|
| Interview invitation | Check timezone, availability and requested documents; confirm or propose a time | Employer-confirmed time and response evidence |
| Proposed reschedule | Wait for employer acceptance; do not label it a confirmed meeting | Accepted time, or pending confirmation |
| Assessment request | Read scope and deadline; complete the actual candidate work | Actual submission and receipt, separately from invitation |
| Acknowledgment | Monitor the application mailbox, CV contact mailbox and Spam | Review date and exact role match |
| Rejection | Close that opportunity and preserve submission history | Employer decision, not a missing reply |

An invitation can be past its scheduled date without evidence of attendance.
Do not infer completion, a missed interview or an offer. Follow-up dates suggested
by the tracker are internal reminders unless the employer states a deadline.
Reading a message does not itself send a reply, accept a meeting or complete a
recorded interview. Use a verified employer contact and the host's applicable
permissions when taking the next action.

## What this evidence supports

The maintainer reconciled the private canonical ledger, immutable receipts and
message evidence. Prior user-reported applications, failed/uncertain attempts and
duplicates were excluded from the confirmed total. Rejections are later outcomes and do not erase
the fact that an application was submitted. The public summary is intentionally
not an independent audit: raw records are not published for readers to inspect.

This was a **host-assisted campaign**, with research, evidence review, tailored
documents, user-confirmed facts, browser/email operations and human steps where
required. It is not proof that a fresh clone can autonomously send 100 applications
through every runtime, provider or employer. It does not establish 100/hour, a
100x speedup, employer delivery for every sent email or 100 employment offers.

The historical scope included explicitly approved adjacent and stretch roles.
It has **not** been reclassified as 120 Strong/Plausible-fit applications. The new
default goal uses the user's reviewed Strong/Plausible-fit scope; those stricter
criteria must be recorded prospectively rather than retrofitted to this example.

## Lessons for your campaign

- Check both the application mailbox and the CV contact mailbox, including Spam.
  One time-sensitive invitation in this review was in Spam.
- Match exact role/requisition, not just employer or email domain. Two roles at
  the same company are distinct; suggested jobs in a receipt are not responses.
- Acknowledgments, optional event advertisements and generic interview-process
  wording do not mean a shortlist, interview or offer.
- Keep submission state and response stage separate. Store source/date, timezone,
  next action and the employer's actual deadline wording. A soft target is not a
  guaranteed cutoff; routine review dates are suggestions, not employer promises.
- A mailbox review is not authority to send replies, accept meetings, record a
  candidate, share repositories or submit assessments. Use the actual host rules.

This is a dated snapshot, not a live public inbox monitor. Use your own private
tracker and [CV-first start prompt](../prompts/COMMUNITY_START.md) for your campaign.
