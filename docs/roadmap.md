# Vertical-slice roadmap

This records implemented evidence separately from intended product scope. No later slice is complete merely because a prompt describes it.

| Slice | Acceptance gate | State |
|---|---|---|
| 1 | Clone/diagnose/private init/CV+profile+JD import/confirmed evidence matrix/Markdown draft/tracker/resume; two-user and failure tests | Implemented; measured evidence in RELEASE_SLICE1.md |
| 2 | Accurate DOCX/PDF from approved content; rendered page review; exact expiring manifests | Implemented; optional Linux renderer and local approval validation, evidence in RELEASE_SLICE2.md; preparation-only scopes stay disabled |
| 3 | Measured Codex/Claude runtime execution, synchronized project setup/dry run/backups/uninstall | Pending; wrappers alone are instruction-only |
| 4 | One permitted discovery connector plus manual import; permission evidence/rate limits/coverage/dedup tests | Manual import in Slice 1; network connector pending |
| 5 | Explicit browser bridge and local mock portals; ASSIST plus complete handoff; interruption tests | Host request/receipt engine implemented; deterministic bridge/CLI tests and separate Codex local UI smoke. Real employer/native end-to-end integration pending |
| 6 | Finite approved-batch authorization and sequential submission; unique attempts before final action; confirmation/unknown recovery | Implemented in deterministic engine/CLI tests; production host/employer verification remains separate |
| 7 | Identified Grok runtime integration with version/OS test evidence; additional sources | Pending; no runtime identity invented |
| 8 | Locked optional dependencies, install/upgrade/uninstall tests, bilingual guides, notices and release packaging | Incremental; final gate pending |

## Current implementation sequence

Standing campaign authorization is an opt-in extension of Slice 6: one approved
recipient/profile/answer/consent scope can derive later exact reviewed batches
with a shared cap, expiry and revocation. Local deterministic tests do not close
the native host or real-employer gates. See STANDING_AUTHORIZATION.md.

1. Specify the portable product and preserve the existing legacy checks.
2. Move the existing core without behavior changes; retain its compatibility entrypoint.
3. Add versioned preparation contracts, immutable source import and one-candidate workspace state.
4. Add complete fit-matrix validation, quote-preserving Markdown tailoring, tracker/report/resume and fictional CLI integration tests.
5. Synchronize ten skills, document runtime/source support accurately, publish measured setup and a bounded review at the slice gate.

Next after Slice 2: verify actual Codex/Claude native runtime invocation and scoped integration, including installation preview/backups/uninstall. The host-mediated execution engine is now implemented; see execution.md for scope and measured limits. Native hooks and real employer integrations remain separate gates. Rendering is optional and local, without a second AI API.
