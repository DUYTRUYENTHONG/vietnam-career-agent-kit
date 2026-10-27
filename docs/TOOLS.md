# Local tools and document workflow

The opt-in experimental `tinyfish-browser` command is an exception to the local-only
commands below: preview is offline; `--live` explicitly creates cloud sessions and
executes exact approved form actions. See [Browser setup and limits](TINYFISH_BROWSER.md).
Core preparation remains standard-library-only; optional CDP uses requirements-browser.lock.

Current Slice 1 adds a working preparation CLI: TXT/Markdown CV import, versioned profile/JD/matrix/plan validation, explicit profile confirmation, source-preserving Markdown drafts, checkpoint/report export and manual handoff. See DATA_CONTRACT.md and setup.md for actual commands/envelopes.

Core preparation/tests remain standard library only. Slice 2 implements optional DOCX/PDF generation and page review using the fully pinned Python closure in requirements-documents.lock plus separately provisioned LibreOffice/DejaVu Sans. See documents-and-approval.md. CV PDF/DOCX extraction remains unimplemented. No browser executor or native integration is implied by shared skills.

The core CLI and hook helper use Python 3.11+ standard library only: argparse, pathlib, sqlite3, hashlib, json and datetime. They do not call an AI API, install packages, open a browser or submit an application. Use `python scripts/kit.py --help` and each subcommand's help for exact arguments.

The selected agent supplies reasoning, policy-permitted web research and optional browser/computer control. A search result is a discovery lead, not proof that a role is live. No scraped private API, session reuse helper or unrestricted portal collector is bundled.

For documents, render uses the same confirmed source model and DOCX-to-PDF layout. Optional dependency installation is explicit via requirements-documents.lock; requirements-documents.txt includes that same hash-enforced lock. The kit never installs them automatically. PDF/Word creation is not proof of correct layout; review every page before creating a manifest.

Required verification: reopen generated files; extract text and compare with the approved model; render every PDF page; inspect glyphs, clipping, page breaks, headings, links and reading order. Render the DOCX with an available Word/LibreOffice path before delivering it as visually verified. Report missing renderers honestly and provide a checked alternative plus editable text. Do not upload private documents to an external converter without explicit disclosure approval.

For Unicode PDF output use an appropriate locally licensed TrueType font. Do not bundle a proprietary system font in this public repository. For TeX, use Unicode-capable compilation, escape supplied text and disable shell escape. Never run a compile command from an untrusted JD.

The execution CLI emits guarded requests for supported host tools; it does not
drive a browser itself. The browser-application skill documents the request and
receipt loop. Standing authorization adds five local controls for approved
recipient/answer/consent scopes; see STANDING_AUTHORIZATION.md. Unknown source
permission, required answers and host confirmations remain actionable exceptions.
A handoff separates the CV from private source-map review artifacts; the source
map is not an employer attachment.

launch-execution composes approved standing derivation, start and first request.
cleanup-execution/record-cleanup manage exact completed-tab instructions and
host-reported results after saved confirmation. Only the supported host closes
tabs, after verifying cleanup intent and agent ownership; the CLI cannot close
the browser itself. See execution.md for recovery and trust boundaries.
