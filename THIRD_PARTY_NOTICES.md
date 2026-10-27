# Third-party notices

Live Resume writing reference: `guilhermeborgesbastos/live-resume` revision
`07c0680129ecf0226d802d23233fe7d1bea9121f`, MIT, copyright 2020 Guilherme Borges
Bastos. No upstream code, skill text, templates, assets or candidate content is
redistributed. Original writing guidance adapts source-checking/review ideas;
Humanizer and Angular/Firebase dependencies are not adopted. See
docs/LIVE_RESUME_REVIEW.md and adapters/live-resume.source.json.

Optional local plugins use separately installed MCP Python SDK 1.30.0 (MIT),
google-auth-oauthlib 1.5.0 (Apache-2.0), keyring 25.7.0 (MIT), and Playwright
1.58.0 (Apache-2.0), plus their dependencies. No library or browser executable is
vendored or relicensed. Exact dependency versions, PyPI metadata hashes/license
declarations and the Windows/Python3.12 profile are recorded in
adapters/local-plugins.source.json and requirements-plugins.lock. Preserve
installed distribution notices if redistributing those binaries. Google and
OpenAI documentation guided original implementation; no sample source copied.

BrowserAct review: `browser-act/skills` revision
`11c057b03f92101642cadc9f840564574120d184` is MIT, copyright 2026 BrowserAct.
No upstream code, skill text, assets or binaries are bundled. The offline session
planner is original code. The separately distributed CLI1.4.5 metadata supplies
no license expression; its compiled wheels and dependencies are not adopted or
relicensed. See docs/REFERENCE_REVIEW.md and adapters/browser-act.source.json.

Original toolkit code is licensed under LICENSE (MIT). No code, templates, biographies, candidate files or settings from the four reference repositories are vendored. Their ideas informed this original implementation. A public repository is not automatically reusable without its license.

| Reference | Reviewed commit | Root license and scope |
|---|---|---|
| [job-apply-assistant](https://github.com/saizongmm/job-apply-assistant) | fbce87dc99bc1ac09df4148b9677d5db9fb63d0e | MIT; no copied code |
| [career-ops](https://github.com/career-ops-hq/career-ops) | c87e0f05a5bf3b0e7bff1f6c87fd0865191e7da7 | MIT; no copied code/installers/browser orchestration |
| [ai-job-search](https://github.com/MadsLorentzen/ai-job-search) | 4339153f8f5e4bb69eaee2a50af713815409e8e7 | MIT; no copied candidates/market defaults/settings |
| [claude-resume-kit](https://github.com/ARPeeketi/claude-resume-kit) | 69930e9de21d5595f9b8c9427adc9c51a9fcbc0e | MIT root; cv.cls/resume.cls have Trey Hunner/LaTeXTemplates notices. Neither class is copied. |

MIT source reuse would require preserving the upstream copyright/license notices; class-specific attribution also survives if those assets are adopted later. Re-review every changed dependency/reference revision. Core preparation/tests/hooks have no third-party package requirements. Optional document libraries are explicitly installed from the Python wheel lock; they are not vendored or relicensed as original code.

Slice 2 optional package metadata reviewed on PyPI: python-docx 1.2.0 (MIT), lxml 6.1.1 (BSD-3-Clause plus its binary dependencies' notices), typing_extensions 4.16.0 (PSF-2.0), pypdf 6.10.0 (BSD-3-Clause), pypdfium2 5.14.0 (BSD-3-Clause/Apache-2.0 plus bundled PDFium dependency licenses), Pillow 12.3.0 (MIT-CMU plus optional binary dependency notices). Preserve installed wheel license files, especially PDFium's third-party notices, when redistributing binaries. The toolkit does not bundle those binaries. Package license/source records and hashes are in dependency-lock.json and requirements-documents.lock.

LibreOffice (MPL-2.0 and component licenses) and DejaVu fonts (Bitstream Vera/public-domain additions and font-specific notices) are externally provisioned. No renderer executable or font is copied into this repository. Consult the distribution's installed notices before redistributing a runtime. The pinned GitHub upload-artifact action is referenced for fictional CI evidence only; its code is not vendored. Metadata was read at ea165f8d65b6e75b540449e92b4886f43607fa02.

See docs/REFERENCE_REVIEW.md for exact inspected files, evidence hashes, useful ideas and limitations. Source audits are static review, not execution permission, full transitive security analysis or verification of every upstream claim.

## Optional public research adapters

The Firecrawl v2 adapter is original standard-library HTTP code. No Firecrawl
server, SDK, docs text or upstream example code is vendored. Official protocol
references and exact documentation hashes are recorded in docs/REFERENCE_REVIEW.md.
Hosted API access and billing are governed separately by the provider account;
MIT licensing of this kit does not grant source access or provider permission.
No TinyFish runtime or code has been adopted in this increment.
