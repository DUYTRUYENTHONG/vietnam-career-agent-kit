# Community preview 0.2.0 — contract and release evidence

Scope: CV-first local intake, the default campaign goal, community documentation,
an anonymized real-results snapshot and committed-source ZIP distribution.
This release does not add a universal browser driver or certify native host setup.

## New local contract

`start-campaign --cv FILE [--target N] [--language en|vi]` requires an explicitly
selected external `--data-dir`. Target defaults to 100; explicit integer overrides
must be 1–10000. The input is a nonempty PDF/DOCX/TXT/Markdown file, at most 10 MB.
Only the path and SHA256 are recorded in `starter/intake.json`; the command does
not execute, extract or import the document. The output has `schema_version:1.0`,
nullable required-information fields, `mode:PREPARE`, a finite target and
`execution_authorized:false`. No SQLite schema change is introduced.

The existing initializer creates/reuses the canonical workspace. A matching
starter resumes without replacing user edits. Changed source bytes/path, target
or language blocks this starter call until explicitly reviewed. An incomplete
packet requires recovery. No facts, profiles, approvals, submissions, persistent
host goals or background workers are created by intake.

`scripts/package_community.py --output EXTERNAL.zip` reads the exact HEAD commit
with Git archive. It checks the archived content, excludes untracked files/Git
metadata, refuses private artifact patterns, binary/non-UTF8 files and symlinks,
and publishes a ZIP plus per-file/archive SHA256 manifest without overwriting
existing artifacts. These are bounded checks, not an exhaustive secret scanner.

## Acceptance performed on 27 October 2026

- Six focused fictional regressions passed: default/overridden finite target,
  inert intake, separate-user CLI execution, edited-packet preservation, changed
  evidence/target rejection, invalid input before workspace creation, exact source
  archive/digest, untracked-private exclusion, tracked-private rejection and
  output/release overwrite refusal.
- Public summary/CSV/Markdown have 100 unique anonymous application rows, and their
  response categories reconcile to 100. No private contacts, email links, raw
  recruiter content or local candidate paths are published in these artifacts.
- The SVG parsed as XML and was rendered in the Codex in-app browser at localhost.
  The full graphic was visually inspected: all cards, legends, counts and scope
  text were readable, with no clipping. Screenshot retained outside the repository.
- The complete standard suite, repository hygiene, wrapper synchronization,
  fictional demo, link checks and distribution acceptance are release gates;
  final measured results are recorded below before publication.

## Runtime and result limits

The portable start prompt is Instruction-only host guidance. The local CLI
tests do not certify Codex/Claude native discovery, Grokbot/Muse adapters,
PDF/DOCX extraction, Gmail access, employer write permission, multi-browser
isolation or live TinyFish/Firecrawl acceptance. Optional services keep their
existing setup/fees. No new model SDK, credential, telemetry or active hook.

The public 100-application snapshot is a real **host-assisted** case study,
including explicitly approved adjacent/stretch roles. It is not an audited
100-best-fit engine cohort, a 100/hour benchmark or 100 job offers. Historical
receipts and response outcomes remain separate. No personal campaign is started
or continued while maintaining or testing this release.

The preview is distributed by the immutable `community-v0.2.0` tag and release
assets. A pushed development PR or release tag does not claim a merge to `main`.

## Measured local results

On Windows with Python 3.12.14:

- `python -m unittest discover -s tests -v`: **277 tests passed**, 570.122 seconds.
- `python scripts/check_repository.py`: **248 UTF-8 source files passed**, including
  ten canonical skills and synchronized adapters; bounded hygiene only.
- `python scripts/generate_adapters.py --check`: passed, no generated drift.
- `python scripts/demo_slice1.py`: passed using a disposable fictional workspace.
- CLI help and the public tracker/category reconciliation passed.
- The staged implementation received one consolidated maintainer review, including
  path boundaries, preservation of edits, inert intake, archive contents, counting
  claims and publication privacy. No independent peer review is claimed.

GitHub matrix/document/plugin checks are reported on the linked release commit
and PR. Local results alone do not establish those remote checks.

Distribution acceptance also passed from a clean extraction of the committed
248-file ZIP: every per-file/archive SHA256 matched; license/authorship/notices
were present and Git metadata absent. Generic `doctor`, the disposable fictional
demo and a fresh default-100 `start-campaign` succeeded from the extracted source.
The starter retained `execution_authorized:false`. Relative links and Markdown
fences passed for all 18 changed guides. The final release is rebuilt from its
published commit; the attached digest manifest identifies those exact bytes.

The preview evidence above is historical. The reviewed stack is now integrated
into `main`; see [main release QA](MAIN_RELEASE_QA.md) for the merge and
community-clone acceptance. The preview tag and its archive remain immutable.
