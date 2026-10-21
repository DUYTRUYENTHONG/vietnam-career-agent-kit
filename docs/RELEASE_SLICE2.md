# Slice 2 rendering and approval evidence

Reviewed 21 October 2026. Scope: optional local document generation, every-page review and exact finite expiring approval bookkeeping. No browser, live employer application, paid model or submission executor was used. Full product release and later slices remain separate gates.

## Implemented

The same confirmed source model produces DOCX and a PDF converted from that exact file in an isolated LibreOffice profile. The toolkit reopens DOCX and compares paragraphs, checks normalized ordered PDF text and embedded/unsubstituted fonts, then renders every page. Files, source/content/draft fingerprints and preview images are hashed into a document set. Review requires its exact fingerprint, all ordered page numbers and explicit content/layout/glyph/language checks. Rejection invalidates dependent approval checks.

Manifests bind candidate/profile, employer/job/requisition, exact destination, reviewed CV/hash, full ordinary answer set/hash, explicit consent text/choices/hash, allowed operations, UTC expiry, finite entries and submission limit. Unknown required answers, stale evidence/review/permission, changed export/artifact/preview bytes, mismatched intent and expiry block. Overlapping changed scopes revoke prior relevant approvals; unchanged approved scopes remain idempotent. Revoked fingerprints cannot replay an old confirmation. Confirmation files are local bookkeeping and do not authenticate a human or prove platform authorization.

Schema 2 adds document/review/manifest/approval tables while retaining the canonical SQLite tracker, candidate data and legacy approvals. Explicit init upgrades only the selected private workspace. Core preparation and state tests remain standard library only; optional Python dependencies have a full six-package closure with exact versions/PyPI wheel hashes. LibreOffice/fonts are externally provisioned, measured dependencies, not a hermetically locked OS image.

## Checks and actual rendering

Local Windows/Python 3.12.14: **55 standard-library tests passed**; real DOCX paragraph roundtrip and two native DOCX/PDFium preview tests passed. No local LibreOffice was available, so Windows full conversion is not labeled verified. Core unit tests use explicitly named fake converters for state tests, not claimed PDF layout evidence.

The [Linux rendering run](https://github.com/DUYTRUYENTHONG/vietnam-career-agent-kit/actions/runs/39557082895) passed the four ordinary Python 3.11/3.12 Linux/Windows jobs at that implementation checkpoint plus **six optional integration tests** on Python 3.12.15. Renderer: LibreOffice 24.2.7.2, DejaVu Sans, python-docx 1.2.0, pypdf 6.10.0, pypdfium2 5.14.0, Pillow 12.3.0. Exact current-head CI is visible in the PR; this fixed run identifies the actual visually reviewed output.

The real suite covers two isolated English/Vietnamese candidate flows through CLI render/review/manifest/approval/check/rejection, a long Vietnamese name with multiline literal markup across three pages, missing converter, timeout after version inventory, mismatched PDF, native page-handle cleanup and inherited title-rule removal. The optional timeout regression was subsequently tightened to isolate conversion after successful inventory; source layout code is unchanged.

Every one of the **five emitted pages** was opened at original resolution. Initial visual review found an inherited blue Title border. It was removed from OOXML/styles; all regenerated pages were inspected. Diacritics, literal <requirements>/ampersands, margins, line wrapping, page breaks and reading order remained clear without clipping or overlap. Page/artifact SHA-256 and dimensions are recorded in [fictional evidence metadata](evidence/slice2-visual.json). CI artifacts retain only fictional output for seven days; the metadata persists and tests can regenerate output. No real candidate files are uploaded to CI or committed.

## Review findings resolved

- Moved runner-specific CI paths from job-level context into the execution step.
- Replaced an unsupported PDFium page context manager with explicit native handle cleanup and a regression.
- Removed inherited title borders after actual visual inspection.
- Preserved existing unchanged approvals across repeated creation/init; blocked revoked proof replay.
- Excluded private source maps/content/previews from employer attachment lists.
- Kept optional parser/converter exceptions structured and registered no partial document set on failure.

The consolidated review checked correctness, boundaries, readability, data retention and bounded renderer behavior. The shared core accepts structured evidence only; no arbitrary shell text originates from job content. Explicit trusted executable selection is still a host/user trust boundary, not an OS sandbox. No third-party source, proprietary font or runtime executable is vendored.

## Reproduce and remaining limits

```sh
python -m unittest discover -s tests -v
python scripts/generate_adapters.py --check
python scripts/check_repository.py
python -m pip install --require-hashes --only-binary=:all: -r requirements-documents.lock
# Provision LibreOffice Writer/DejaVu Sans explicitly; choose its trusted absolute path.
# Set CAREER_KIT_SOFFICE, then:
python -m unittest discover -s tests_optional -v
python scripts/demo_slice2.py --data-dir ../career-doc-demo --soffice /absolute/path/to/soffice
```

See documents-and-approval.md for the full private review/approval commands and schema. Every manifest result reports execution_enabled=false. No submission budget is consumed and no attempt is recorded. Required legal/sensitive declarations and unknown fields need direct user action. CV PDF/DOCX input extraction, native host integrations, permitted network discovery, browser/attempt recovery and actual finite-batch execution remain pending. Word layout can vary across machines; the reviewed PDF is the fixed visual artifact when accepted by the employer.

Next: Slice 3, measured Codex/Claude native integration and scoped setup/dry-run/backup/uninstall behavior. Do not enable browser operations merely because local approval checks pass.
