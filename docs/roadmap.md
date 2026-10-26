# Vertical-slice roadmap

Experimental runtime increment: [TinyFish Browser](TINYFISH_BROWSER.md) adds
explicit single-page guest forms, finite worker deadlines and safe quarantine.
Fictional tests verify protocol behavior; live CDP/provider acceptance, broader
ATS mappings and automatic cross-process session reconciliation remain pending.
Routing has a host callback contract; native dispatch still requires host support.

Quality-gated preparation enhancement: [first complete wording/review/render
consumption slice](QUALITY_FAST_PLAN.md), with v1 fallback and optional real
renderer CI. [Ten-lane execution and TinyFish Fetch](PARALLEL_APPLICATIONS.md) are
experimental opt-in additions. Candidate-local caches, validated form plans and
blind complete-package evaluation remain separate pending increments; none is implied by v2 schema support.

This records implemented evidence separately from intended product scope. No later slice is complete merely because a prompt describes it.

Optional local email/browser plugin transports now have implementations; see
[setup](LOCAL_PLUGINS.md) and [scoped QA](LOCAL_PLUGINS_QA.md). They reuse the
canonical ledger and do not close native host, live OAuth, real-employer or
public-directory acceptance gates.

| Slice | Acceptance gate | State |
|---|---|---|
| 1 | Clone/diagnose/private init/CV+profile+JD import/confirmed evidence matrix/Markdown draft/tracker/resume; two-user and failure tests | Implemented; measured evidence in RELEASE_SLICE1.md |
| 2 | Accurate DOCX/PDF from approved content; rendered page review; exact expiring manifests | Implemented; optional Linux renderer and local approval validation, evidence in RELEASE_SLICE2.md; preparation-only scopes stay disabled |
| 3 | Measured Codex/Claude runtime execution, synchronized project setup/dry run/backups/uninstall | Pending; wrappers alone are instruction-only |
| 4 | One permitted discovery connector plus manual import; permission evidence/rate limits/coverage/dedup tests | Manual import plus experimental bounded Greenhouse public GET; fictional coverage/dedup tests. Live employer verification pending; see BULK_DISCOVERY.md |
| 5 | Explicit browser bridge and local mock portals; ASSIST plus complete handoff; interruption tests | Host request/receipt engine implemented; deterministic bridge/CLI tests and separate Codex local UI smoke. Real employer/native end-to-end integration pending |
| 6 | Finite approved-batch authorization and sequential submission; unique attempts before final action; confirmation/unknown recovery | Implemented in deterministic engine/CLI tests; production host/employer verification remains separate |
| 7 | Identified Grok runtime integration with version/OS test evidence; additional sources | Pending; no runtime identity invented |
| 8 | Locked optional dependencies, install/upgrade/uninstall tests, bilingual guides, notices and release packaging | Incremental; final gate pending |

## Current implementation sequence

BrowserAct integration currently provides an offline authorized-request session
planner and reviewed skill guidance. Native browser acquisition, form-write
translation and live latency/isolation acceptance remain pending; see
[the integration scope](BROWSERACT.md). This does not close Slice 5's native gate.

Optional Fast Web increments 1–2 add contracts, the opt-in boundary and a complete
Firecrawl public research/evidence-import slice. Live verification remains
pending. Increment 3 (TinyFish interactive public research) and increment 4
(direct Browser plus cloud disclosure) are unimplemented and must preserve the
host executor. See FAST_WEB.md; they do not block delivery of public retrieval.

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


## Parallel execution update

Schema 6 adds opt-in independent application lanes and public TinyFish Fetch batches. See [PARALLEL_APPLICATIONS.md](PARALLEL_APPLICATIONS.md) for commands, host requirements and measured-versus-unverified limits. Earlier sequential-only/TinyFish-unsupported descriptions apply to previous increments. [TinyFish Browser](TINYFISH_BROWSER.md) now has an opt-in experimental guest-form adapter; Agent-goal submissions remain unsupported.
