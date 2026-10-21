# Local tools and document workflow

Current Slice 1 adds a working preparation CLI: TXT/Markdown CV import, versioned profile/JD/matrix/plan validation, explicit profile confirmation, source-preserving Markdown drafts, checkpoint/report export and manual handoff. See DATA_CONTRACT.md and setup.md for actual commands/envelopes.

Core/test/demo dependencies are standard library only, recorded in dependency-lock.json. Optional document libraries below are not an implemented rendering/extraction pipeline. No browser executor or native integration is implied by shared skills.

The core CLI and hook helper use Python 3.11+ standard library only: argparse, pathlib, sqlite3, hashlib, json and datetime. They do not call an AI API, install packages, open a browser or submit an application. Use `python scripts/kit.py --help` and each subcommand's help for exact arguments.

The selected agent supplies reasoning, policy-permitted web research and optional browser/computer control. A search result is a discovery lead, not proof that a role is live. No scraped private API, session reuse helper or unrestricted portal collector is bundled.

For documents, prefer existing host document/PDF skills and renderers. Optional tested library versions are listed in requirements-documents.txt. Review and install only if needed, inside your own virtual environment; the kit never installs them automatically. PDF/Word creation is not proof of correct layout.

Required verification: reopen generated files; extract text and compare with the approved model; render every PDF page; inspect glyphs, clipping, page breaks, headings, links and reading order. Render the DOCX with an available Word/LibreOffice path before delivering it as visually verified. Report missing renderers honestly and provide a checked alternative plus editable text. Do not upload private documents to an external converter without explicit disclosure approval.

For Unicode PDF output use an appropriate locally licensed TrueType font. Do not bundle a proprietary system font in this public repository. For TeX, use Unicode-capable compilation, escape supplied text and disable shell escape. Never run a compile command from an untrusted JD.

No generic submit CLI is supplied. The browser-application skill documents the planned permitted workflow and current manual handoff. Unknown permissions or missing required answers require manual preparation. A handoff separates the CV from private source-map review artifacts; the source map is not an employer attachment.
