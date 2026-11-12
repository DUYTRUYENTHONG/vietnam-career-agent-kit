# Improve tailoring from observed errors

Status: **Instruction-only** host workflow. No core, schema, hook, model dispatch,
cloud upload or automatic promotion behavior changes.

Use [the error-driven prompt](../prompts/ERROR_DRIVEN_TAILORING.md) when a candidate
reports poor application results or asks to optimize a trained tailoring model.
It extends the existing [JD-specific contract](JD_SPECIFIC_TAILORING.md) and
[review cycle](CV_REVIEW_CYCLE.md), rather than replacing either.

## Diagnose the right problem

A confirmed submission proves the application action, not a successful CV screen.
A view is not an invitation; an invitation is not attendance or an offer. Unknown
outcomes remain unknown. A response-rate estimate needs a dated fixed cohort,
an explicit stage numerator, comparable observation windows and a stated cutoff.
Even a valid descriptive rate does not identify the cause of rejection.

For an existing compatible portable workspace, reuse
[`outcome-record` / `outcome-report`](CV_OUTCOMES.md): bind observations to the
frozen submitted CV and source bytes, and report explicit age/as-of cohorts.
Do not create a competing outcome ledger. Legacy trackers are not migrated by
these commands; a dated host audit of their existing records must remain labelled
advisory and must not manufacture portable submission IDs or timestamps.

Check three independent sources of loss:

1. **Vacancy selection:** mandatory seniority, location, work type and experience
   gaps. Better prose cannot supply missing qualifications.
2. **Document selection:** the strongest relevant evidence is buried, unrelated
   duties dominate, or a generic master is reused without explaining its fit.
3. **Generation errors:** the model copies a JD into experience, drops qualifiers,
   inflates contribution scope or mistakes valid JSON for factual support.

Compare original and revised content against the same JD and rubric. Separate
new evidence from editorial changes. Preserve the master/history and submit only
the newly reviewed exact document under valid disclosure authority. Do not resend
historical applications merely to obtain more training data.

## Evidence-first drafting sequence

The host builds claim budgets from source facts, selects detail for the JD's
delivery priorities, drafts inside those budgets, and reviews claim deltas.
The existing schema and one-fact-per-statement rule remain authoritative.
Specificity means a concrete supported method/check, not more keywords or length.
Put group-level qualifiers where a recruiter can see them; standalone learning
rows must not depend on an absent heading to preserve their meaning.

Retain complete mandatory coverage in the private matrix even when the application
CV selects fewer examples. A concise CV is not permission to hide a required
screening answer. Do not automatically reduce a source-rich CV to a page quota.

## Real-data model improvement

Create private error observations bound to raw output and source hashes. A model
failure is useful diagnostic data, but its proposed correction is not human gold.
Independently review corrections before using the existing supervised exporter.
Keep grading targets separate from bullet-wording targets and recruitment events.

Keep exposed evaluation cases in development/regression. Split by actual source
fact/project groups as well as employers; report unavoidable overlap. If the same
fact/target occurs in training and evaluation, label the result an exposed-fact
diagnostic, not unseen-fact tailoring performance. Do not regenerate references
from a model's answer or silently relabel historical scores.

Changing model families requires a fresh compatible base; changing the prompt
requires a separate measured condition. Compare the frozen base, prompt-only and
adapter conditions with the same source cases, decoding and complete denominators.
Check unsupported claims and qualifier preservation before reference loss or
style preference. Report actual token/timing measurements and invalid outputs.
Do not invent uplift, ATS scores or hiring probabilities from reference matching.

## Acceptance evidence and limits

This update supplies a host prompt and fictional review exercises. Repository
checks can verify source hygiene, synchronized wrappers and unchanged program
behavior. They cannot establish prompt adherence, trained-model improvement,
independent semantic review or recruiter outcomes. Existing optional training,
evaluation and approval interfaces retain their previous compatibility status.

Keep real CVs, outcome records, training rows, checkpoints and model-error examples
in the selected external private workspace. Public examples remain fictional.
