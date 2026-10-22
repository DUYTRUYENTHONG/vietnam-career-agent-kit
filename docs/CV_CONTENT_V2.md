# Source-bound wording and content model v2

V1 `prepare` remains the exact-quote fallback. A Markdown rewrite alone never
changes a PDF. V2 is an explicit opt-in local path:

```sh
python scripts/kit.py --data-dir ../private import-wording --job-id 1 --file ../private/inputs/model.json --include-review-packet
python scripts/kit.py --data-dir ../private wording-packet --job-id 1
python scripts/kit.py --data-dir ../private review-wording --job-id 1 --file ../private/inputs/independent-review.json
python scripts/kit.py --data-dir ../private render --job-id 1
python scripts/kit.py --data-dir ../private reject-wording --job-id 1 --reason "Factual issue found during review"
```

The optional `--include-review-packet` returns exactly the independently requested
packet after the same fresh checks. A failure after import can leave a committed,
unreviewed draft: reconcile `resume`/`wording-packet`; do not infer no commit.
No command invokes a model or fabricates a real review. Inputs must be within
the selected private workspace. Use the host agent for one structured drafting
pass, a separately prompted review pass and at most one focused repair; unresolved
findings block or fall back to separately reviewed exact claims.

The editor contract is [cv-content-v2.schema.json](../schemas/cv-content-v2.schema.json).
Start from [the fictional input example](../templates/wording.example.json),
replacing its bindings and text with this user's actual confirmed evidence.
`scripts/demo_wording.py` provides three fictional profile families and TEST ONLY
review assertions. Never use its review helper for a real candidate. An agent
must actually inspect the original evidence before recording a review.

## Representation and bindings

Imported profile facts remain immutable exact quotes with existing confirmation.
Every wording statement records ID, text, section/group, one source fact ID,
exact source locator, assessed requirement IDs, transformation, retained
qualifiers, unresolved questions and pending status. Exact selection/reordering
cannot change text; faithful compression/paraphrase/translation require review.
This first slice deliberately rejects multi-fact statement synthesis.

Identity/contacts come from the current confirmed profile. The proposed target
headline comes from the actual JD, separate from immutable historical context
quotes. Optional summary, skills, grouped experience/projects, education,
certifications and language sections appear only when supplied with evidence.
Employment/project groups require a confirmed context fact and matching
`scope#location` locators within one original source. These locator annotations
must be reviewed when confirming the profile; they are not automatic source-span
authentication. A group cannot borrow a fact from another scope/employer.

Numeric/date, capitalized-entity/title, sensitive tool/credential/ownership and
English/Vietnamese qualifier alarms are conservative deterministic checks.
They can produce false positives; clarify evidence or retain exact wording.
They are **not** a general semantic proof, entity recognizer, chronology parser
or machine translation evaluator. Independent review must examine scope,
chronology, omissions, language equivalence and wording beyond these alarms.

The fingerprint binds input model, candidate/profile/evidence fingerprint, exact
JD, current evidence matrix and review policy. Pending wording is stored in the
existing canonical `drafts` table and hashes private Markdown/model/source-map
files. There is no new SQLite schema version, alternate ledger or migration of
historical reviews. New wording becomes the latest draft and blocks rendering
until reviewed. Importing another model never inherits review from old bytes.

The independent review names a different pass from the author, binds the exact
fingerprint/policy and checks every statement with a concise rationale. Distinct
labels are bookkeeping, **not authentication or proof of reviewer independence**.
A separate prompt/context must actually perform that review. A false check stops
the package; no automatic repair loop converts it into approval.

## One rendered truth

The approved content model sets approved statement status and includes the exact
review hash. `core.rendering.content_lines` drives Markdown construction, DOCX
paragraphs and PDF extracted-text expectations. DOCX reopening, embedded-font
checks, PDFium locking, isolated LibreOffice profiles, per-page images and explicit
render review remain required. Editing any model, review, source, JD, DOCX, PDF or
page bytes invalidates affected current-render/manifest checks. Old historical
snapshots remain historical. A current model is not external disclosure consent.

No photos, DOB, marital status or national ID are added. Salary, eligibility,
availability and notice period remain separate confirmed screening answers.
Neither v2 review nor an identical reused file authorizes a new destination.
Current source checks mean the selected workspace bytes and fingerprints remain
valid; they do not independently re-observe a vacancy on the employer website.
Recheck the actual destination and applicable source permission before disclosure.

## Independent review prompt

Read the packet's selected original quotes/locators, complete requirements and
matrix, and exact v2 draft. Do not trust the author's rationale. Check every
statement for entailment, scope, qualifiers, language and requirement mapping;
inspect historical context and order as well. Reject invented ownership, outcomes,
numbers, credentials and technologies, omitted prototype/team/basic qualifiers,
and cross-employer combinations. Record concise evidence-based findings and the
rubric. Unknown remains unknown. Do not edit evidence to justify the draft.
Review is not candidate approval and never permits external action by itself.
