# Render documents and approve exact scope

Slice 2 introduced local preparation and approval bookkeeping. Plans without execution scope still return execution_enabled=false. The newer [host-mediated execution engine](execution.md) requires an explicitly reviewed bridge/runtime scope and consumes submission limits through durable attempts. The CLI does not acquire a browser or constrain arbitrary external computer tools.

## Explicit optional setup

Core preparation/tests still require only Python 3.11+. In a separate virtual environment, opt into the complete Python dependency closure:

```sh
python -m pip install --require-hashes --only-binary=:all: -r requirements-documents.lock
```

The lock pins python-docx, lxml, typing_extensions, pypdf, pypdfium2 and Pillow with PyPI wheel SHA-256 hashes. No extras or source builds are selected. LibreOffice Writer and DejaVu Sans fonts are separate user-provisioned system dependencies; they are not locked by this Python file or silently installed by the kit. Review their source/licenses and record actual versions. CI provisions Ubuntu distribution packages explicitly. Windows without LibreOffice returns manual_required; installed Python packages alone cannot produce a verified conversion. An explicitly supplied --soffice path must be absolute and trusted, never taken from a JD.

Run init on an existing external workspace to add schema 2. This preserves schema-1 candidate facts, jobs, drafts, events and legacy approvals. Initialization never scans or migrates other workspaces; older toolkit versions reject the newer schema.

## Render and inspect

Use a current confirmed profile, active structured JD, complete assessment and Markdown draft. The renderer rebuilds a structured content model from the canonical confirmed facts/source map; it does not execute or interpret Markdown/HTML/JD instructions. Historical claims remain exact quotes. The target title remains explicitly a target role. The content snapshot, DOCX, PDF and every page image have bound hashes.

```sh
python scripts/kit.py --data-dir ../career-private init
python scripts/kit.py --data-dir ../career-private render --job-id 1 --soffice /absolute/path/to/soffice
```

DOCX uses A4 pages, 20 mm margins, black DejaVu Sans typography and ordinary paragraphs. LibreOffice converts that exact DOCX with a fresh temporary profile, so PDF previews also check the DOCX layout. The toolkit reopens DOCX, compares its complete paragraph text, compares normalized PDF text in order, checks embedded/unsubstituted fonts, caps output at ten pages and renders every page at 144 dpi using PDFium. This is not a universal ATS, semantic-truth or visual-quality certificate. Open every page image and content.json to inspect clipping, overlap, glyphs, breaks, language and facts. Word may paginate differently on another system; use the reviewed PDF where the employer accepts it.

Conversion errors/timeouts, missing tools, changed evidence or text mismatches register no document set or approval. Rejected/stale sets cannot enter a manifest. Output remains inside the selected private workspace. No external converter, browser or AI service is called by these commands.

For a reproducible fictional example in a new empty directory:

```sh
python scripts/demo_slice2.py --data-dir ../career-doc-demo --soffice /absolute/path/to/soffice
```

Use --candidate b for Vietnamese. The demo creates page images, a false/unfilled review template and a fictional campaign-plan template. It never auto-reviews or approves. Replace the following placeholders with returned values, not literal strings. After inspecting ALL current page images, set reviewed_pages to their ordered numbers and affirm only checks actually performed:

```json
{"schema_version":"1.0","render_fingerprint":"CURRENT_RENDER_FINGERPRINT","reviewed_pages":[1],"checks":{"content":true,"layout":true,"glyphs":true,"language":true}}
```

Save this as a small UTF-8 file inside the private workspace, then:

```sh
python scripts/kit.py --data-dir ../career-doc-demo review-documents --render-id RENDER_ID --review ../career-doc-demo/document-review.json
python scripts/kit.py --data-dir ../career-doc-demo create-manifest --plan ../career-doc-demo/campaign-plan.json
```

Use reject-documents --render-id RENDER_ID --reason "Specific issue" to remove the review and make dependent approval checks fail. Keep artifacts as evidence. Fix the source/selection and render/review again. A source map/content snapshot is private review material, never an employer attachment. Handoff lists DOCX/PDF separately and reports whether the set is reviewed.

## Manifest contract

A strict versioned plan selects 1-100 unique workspace job IDs, render IDs, PDF/DOCX format, exact HTTPS destinations, operations, ordinary screening answers, required-answer IDs, exact consent text/choices and per-host permission evidence. Unknown required answers are blockers. Each answer records value, source (candidate_confirmed or profile_fact), fact_ids and kind=ordinary. Profile-derived answers require exact current confirmed field values. Candidate-confirmed answers need actual candidate review; legal/sensitive declarations require direct user action and are excluded. Generated assertions are not authenticated candidate evidence.

ASSIST permits fill/upload with submission_limit=0. APPROVED_BATCH must explicitly include submit and a positive limit no larger than the finite entry count. Expiry is explicit UTC, future and at most 30 days away. Permission evidence must name the exact destination host/port and authorized operations, have permission=permitted and a checked UTC date within seven days. These declarations do not prove a platform permits automation. Unknown/manual permission returns manual_required. Never convert public search visibility into write permission.

The generated immutable scope binds candidate/profile, employer, platform job/requisition, JD, reviewed render, selected CV path/hash, full answer set/hash, consent choices/hash, exact destination, allowed actions, mode, expiry and finite submission limit. SQLite is authoritative; the exported manifest is a review copy whose content must match. Changes require a new manifest and review. Creating a changed overlapping scope revokes prior approvals for the affected batch; disjoint batches are preserved.

After reviewing that exact exported scope, save a private file containing APPROVE MANIFEST followed by a space and the full current fingerprint:

```sh
python scripts/kit.py --data-dir ../career-doc-demo approve-manifest --fingerprint MANIFEST_FINGERPRINT --confirmation ../career-doc-demo/manifest-approval.txt
python scripts/kit.py --data-dir ../career-doc-demo check-manifest --fingerprint MANIFEST_FINGERPRINT
python scripts/kit.py --data-dir ../career-doc-demo revoke-manifest --fingerprint MANIFEST_FINGERPRINT --reason "Candidate revoked"
python scripts/kit.py --data-dir ../career-doc-demo resume
```

check-manifest optionally accepts --intent for an exact private JSON object with schema_version=1.0, job_id, destination, action, document_sha256, answers_sha256 and consents_sha256. Any mismatch blocks. Every check revalidates profile/source/JD/draft/render/page hashes, current review, expiry, policy freshness and revocation. Recreating an unchanged approved scope retains its approval; a revoked/superseded fingerprint cannot replay its old proof and needs a new reviewed manifest/expiry. Local confirmation files cannot authenticate a human or prevent unrelated host tools from bypassing the CLI. An ok outcome means this local check passed; execution_enabled is true only for a newly reviewed optional execution scope. No submission is inferred from approval; see [the execution protocol](execution.md).

## Tests and external components

The standard-library suite tests state/approval invariants using explicit fake converter output; it does not claim that stubbed files are real PDFs. The separately invoked optional suite tests the real CLI, two fictional candidate/language flows, multi-page Vietnamese/markup layout, missing converter, timeout and mismatched PDF. CI page artifacts contain fictional data only and require a separate maintainer visual inspection before claiming the slice reviewed. Do not upload a real candidate workspace to CI.

Implementation references: [python-docx](https://python-docx.readthedocs.io/en/latest/), [LibreOffice conversion filters](https://help.libreoffice.org/latest/en-US/text/shared/guide/convertfilters.html), [pypdf extraction limits](https://pypdf.readthedocs.io/en/stable/user/extract-text.html), [PDFium lifecycle/thread safety](https://pypdfium2.readthedocs.io/en/stable/python_api.html). The Python wheel lock is exact; external renderer/font/OS versions remain measured dependencies, not a fully hermetic runtime.
