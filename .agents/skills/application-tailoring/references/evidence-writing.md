# Evidence-first CV and application writing

Use this during the existing tailoring/review pass. This is original kit guidance
informed by the source-first, language-review workflow reviewed in
[Live Resume adoption](../../../../docs/LIVE_RESUME_REVIEW.md). It does not require
the upstream Humanizer plugin or introduce a second model API.

## 1. Build a small evidence brief

Read the full current JD and confirmed candidate facts. Select the strongest
relevant requirements and the facts that actually support them. Keep a private
mapping from each proposed claim to its source/fact ID. An employer requirement,
portfolio teaser or suggested example is not proof of the candidate's experience.

For a CV statement, retain the existing v2 one-fact-per-statement rule and the
reviewed employment/project grouping. Do not silently combine facts into a new
causal claim. Target titles can express a direction; historical titles remain exact.

For an email, also capture the requisition/title, published recipient evidence,
verified sender, requested language, employer's subject/attachment instructions,
known availability and compensation basis only when relevant. Unknown required
facts remain gaps. No home-directory scan or unrelated inbox collection.

## 2. Draft the content before polishing

CV bullets should make the candidate's action, tool and scope easy to identify.
Use a measured result only when its exact meaning is supported. Keep prototype,
assisted, coursework, team contribution and basic-exposure qualifiers. Preserve
the currency, period, population and per-product/per-account budget basis.

For application emails, prefer a short subject identifying the actual role and
candidate, unless the employer specifies another format. In the body:

- State the role and application purpose in the first sentence.
- Connect one or two relevant supported examples to the work.
- Include the reviewed CV/portfolio reference and a simple invitation to discuss.
- Add confirmed availability or pay only when requested or useful.

About 100–180 words is a useful English-email starting point, not an engine limit
or a reason to pad short messages. Follow the actual destination's field limits.
Use plain text for the Gmail plugin. Do not add HTML, tracking images, CC/BCC,
unsolicited sensitive identifiers or extra attachments. A web contact form is not
automatically an employer-published application destination.

## 3. Edit for natural language without changing facts

Replace generic self-praise with the supported action. Remove repeated keywords,
empty introductions, inflated adjectives and unsupported claims of expertise.
Use the candidate's voice in email, and direct action language in CV bullets.
Keep necessary technical terms. Do not present this as AI-detection evasion.

Compare before and after: actor, seniority, ownership, tools, dates, quantities,
units, causal claims and outcome must remain supported. A budget is not revenue;
activity is not a measured conversion lift. Shortening must not hide a qualifier.
If an edit changes a fact, restore it or request actual evidence.

For English/Vietnamese versions, write naturally in each language while preserving
proper names, official titles, tool names, amounts and qualifiers. Check meanings
side by side. Do not create extra languages or translations unless requested.
Upstream post-card rules about Portuguese, HTML and 275 characters do not apply.

## 4. Professional reframing and euphemism

Use tactful professional language to make a supported contribution clear. Change
the expression, emphasis and placement without changing the underlying fact.
Replace self-criticism with the actual deliverable and contribution level.

| Supported fact | Professional wording | Unsupported escalation |
|---|---|---|
| Built a keyword-indexed help prototype with an AI coding assistant | Built an AI-assisted help prototype using keyword retrieval and source-linked answers | Deployed production vector RAG |
| Assisted a senior developer with responsive UI fixes | Contributed responsive UI fixes alongside a senior developer | Led front-end architecture |
| Investigated service issues and escalated unresolved cases | Diagnosed service incidents, documented findings and coordinated engineering escalations | Resolved every incident or reduced downtime by an invented percentage |

Keep statements such as "no production experience claimed", "unestablished
expertise" and lists of missing tools in the private requirement map. The CV
should name the actual project, method and scope. A required employer question
still receives the accurate answer; do not conceal a missing mandatory fact or
relabel exposure as proficiency. Do not invent results to complete a formula.

Place material qualifiers where they are clear without repeating them in every
bullet: for example, an "AI-assisted personal project" heading followed by
accurate contributions. Distinguish the candidate's work from team/tool output.
Do not remove the qualifier if the remaining wording implies independent work,
professional tenure or production deployment that the evidence does not support.

Avoid vague euphemisms such as "seasoned AI expert" or "advanced model training"
when the source supports only a small prototype or training-data preparation.
Tool-use duration is not engineering tenure or a measured product outcome. If a
candidate explicitly wants a less relevant detail retained, use a compact
additional-information section rather than letting it displace stronger evidence.

## 5. Relevance before expansion

Use the JD's main responsibilities to choose the evidence and its placement.
For an engineering vacancy, put supported implementation and validation examples
ahead of lengthy unrelated support/sales duties when those examples better
demonstrate the work. Preserve official job titles and dates; selected projects
can precede employment without being represented as paid roles.

More detail means a more useful explanation of relevant work, not a longer list
of every past responsibility. Keep the full history in the private inventory;
compress less relevant duties in the application CV. Follow employer limits and
candidate preferences when selecting the final length.

Before review, explain privately which examples earned prominence, which duties
were shortened and which important requirements remain partial or missing.
Compare the previous and new versions: changing only a headline, company name,
profile or project order is insufficient if the strongest evidence is still
buried or generic. Reuse an existing version when a current JD review shows its
priorities and evidence selection already match; do not manufacture differences.

Fictional review exercise: for a knowledge-assistant vacancy, foreground the
keyword-retrieval prototype and its source checks. For a responsive-frontend
vacancy using the same candidate inventory, foreground UI implementation and
debugging. Keep each fact unchanged. Neither version may claim production vector
search or technical leadership. This exercise illustrates judgment; it is not
an automated semantic validator or proof of better hiring outcomes.

## 6. Review the package, not just the prose

Return the CV wording through the existing factual-review/render/page-review flow.
Keep the source map out of the employer-facing CV. For email, show the exact
sender, recipient, subject, body, attachment identity and remaining evidence gaps
in the private review package. Reuse still-valid scope without inventing new
candidate confirmation. An edited body or attachment changes the bound package.

The Gmail adapter accepts exactly four answer keys: `sender`, `to`, `subject`,
`body`. Each uses the current provenance object; a multi-claim message normally
needs actual candidate review under `candidate_confirmed`, not fabricated
`profile_fact` IDs. Existing finite/standing authority and host requirements
remain separate from stylistic review. Do not invoke a send tool while drafting.

## 7. Stop the affected writing task when needed

Missing source text → ask for authorized text or return an evidence gap.
Unconfirmed metric → omit it or retain an explicitly supported weaker claim.
Unknown recipient → prepare locally, verify the application destination first.
Changed facts after review → invalidate/review the affected content and package.
Missing optional stylistic plugin → use this local guidance; no installation gate.

The kit validates evidence linkage and exact packages; it does not automatically
prove semantic equivalence or certify that a model's prose is factually correct.
