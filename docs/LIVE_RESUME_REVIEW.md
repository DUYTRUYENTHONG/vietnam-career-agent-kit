# Live Resume review and writing-skill adoption

Reviewed 26 October 2026. Upstream:
[guilhermeborgesbastos/live-resume](https://github.com/guilhermeborgesbastos/live-resume/tree/07c0680129ecf0226d802d23233fe7d1bea9121f),
commit `07c0680129ecf0226d802d23233fe7d1bea9121f`, root MIT license,
copyright 2020 Guilherme Borges Bastos. Package version 2.0.0; the skill has no
separate version field. Exact Git-blob SHA-256 values for eight inspected files
are recorded in [the source record](../adapters/live-resume.source.json).

## What the repository actually supplies

Live Resume is an Angular résumé/portfolio website. Its single discovered
`SKILL.md`, `.claude/skills/add-post/SKILL.md`, creates English/Portuguese article
cards. It reads an article, drafts short text, calls an external Humanizer skill,
checks meaning/length/markup, obtains review and inserts validated JSON.
It is not a CV-tailoring engine, email writer or application sender.

The read-only review inspected the skill, guide, template, validator, README,
CLAUDE instructions, package metadata and license. No upstream script, installer,
hook, model, website, contact form, deployment or external plugin ran. Its
Angular/Firebase dependencies, Humanizer requirement and optional ImageMagick
are not installed or added to this kit. Humanizer itself is not adopted or
independently certified by this review.

## Adopted through original kit guidance

| Useful workflow idea | Kit implementation |
|---|---|
| Read actual source before drafting | Current JD and confirmed facts form a compact evidence brief |
| Polish text, then check facts again | Same-pass clarity edit checks tools, ownership, qualifiers and metric bases |
| Review each language for meaning | Requested English/Vietnamese versions preserve official names and facts |
| Validate before writing/publishing | Existing v2 review/render and exact manifest checks remain authoritative |
| Show the actual final content | Email package exposes exact sender, recipient, subject, body and attachment |

The canonical [application-tailoring skill](../.agents/skills/application-tailoring/SKILL.md)
now routes to [evidence-writing guidance](../.agents/skills/application-tailoring/references/evidence-writing.md).
The browser skill references the same guidance before package freezing. Claude's
wrapper is regenerated; the kit retains ten canonical skills. Use the copyable
[TAILOR_AND_EMAIL prompt](../prompts/TAILOR_AND_EMAIL.md).

Original implementation; no upstream skill, code, assets or candidate content
copied. Attribution is retained in the source record and notices. Excluded:
mandatory Humanizer installation, article publishing, thumbnails, Portuguese
defaults, HTML descriptions, the 275-character card constraint, Firebase/analytics
and website deployment. No second model API or per-edit model call is required.

## Fictional acceptance review

Instruction-level worked cases, manually compared against the stated sources.
These are not a live model benchmark, host discovery test or automatic semantic
validator. All people, addresses, jobs and claims below are fictional.

| Case | Input and task | Reviewed result |
|---|---|---|
| Qualifiers | F1: “Built a prototype campaign dashboard with AI assistance.” JD requests production BI | Retain the same qualified statement; flag production experience as missing |
| No invented results | F2: “Tracked USD 2,000 monthly advertising spend for one product.” JD asks for ROAS improvements | “Tracked monthly advertising spend of USD 2,000 for one product.” No revenue, ROAS or conversion lift added |
| Localization | Translate F2 to Vietnamese | “Theo dõi chi tiêu quảng cáo 2.000 USD mỗi tháng cho một sản phẩm.” Currency, period, action and scope retained |
| Application email | Verified fictional sender/recipient, junior marketing-data JD, F1/F2 | Exact draft below uses supported claims; no invented contact name, availability, pay or outcomes |
| Missing source/plugin | No accessible article text and no Humanizer plugin | Return the source gap; no invented content or plugin-install demand. Existing confirmed sources can support independent writing |

Fictional email draft, not a manifest or sending instruction:

```text
From: candidate@example.com
To: hiring@example.org
Subject: Application — Junior Marketing Data Analyst — Fictional Candidate A

Hello hiring team,

I am applying for the Junior Marketing Data Analyst role. I built a prototype
campaign dashboard with AI assistance and tracked USD 2,000 in monthly
advertising spend for one product.

I would welcome the opportunity to discuss how that experience relates to your
marketing-data work. Thank you for considering my application.

Best regards,
Fictional Candidate A
```

No attachment is claimed to exist. A real package adds only its actually
rendered/reviewed file. Short emails do not need padding to a word-count target.
Exact message answers require existing provenance/review; these cases create no
approval or candidate record.

Acceptance: all five cases satisfy the reference's stated criteria on manual
review. Existing core tests enforce source linkage, factual-review state and
package binding; they do not prove generated prose is true. Wrapper sync and
repository checks validate packaging separately. Native discovery, actual model
compliance, ATS outcomes and quality/latency improvements remain unverified.

## Use it

After evidence intake and fit assessment, ask your agent to use
`application-tailoring` for both CV wording and an application email. Supply the
workspace/job/fact references and language. Follow the [prompt](../prompts/TAILOR_AND_EMAIL.md),
then review the exact package before the existing [email transport](LOCAL_PLUGINS.md)
uses it. This changes instructions only: no schema, runtime dependency, model API,
send permission or delivery guarantee is added.
