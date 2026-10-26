# Local plugin release evidence — 26 October 2026

Scope: original local Gmail and Chromium MCP transports. No real candidate data,
credential vault, Google grant, paid provider or employer application was used.

| Check | Observed result | What it establishes |
|---|---|---|
| Full standard-library core suite | 266 tests passed in 523.559 s | Existing suite plus initial plugin regressions, before final review fixes |
| Final email regressions | 7 passed in 21.672 s | Exact MIME/PDF and sender binding, immutable canonical receipts, no replay, preflight failure without a claim, reserved transport, revocation/staleness |
| Final local-browser regressions | 6 passed in 26.242 s | Isolated lane bindings, full fictional protocol/cleanup, mapped identity, revocation/replay, DNS/setup failures, retained failed-disposal handles |
| Final optional integration suite | 3 passed in 11.659 s | Actual SDK stdio initialize/list/call/invalid-input handling, generated paths, mocked vault/send boundary, real headless Chromium form and blocked cross-origin WebSocket |
| Portable package schemas | Both generated packages validated | Fetched Agent Plugins 1.0.0 plugin/MCP schemas; not native host discovery |
| Hash-locked optional install | Passed locally | Windows/Python 3.12 wheel closure, 48 distributions |
| Repository hygiene, diff and wrappers | Passed before publication | UTF-8/public source structure, synchronized ten canonical wrappers; bounded hygiene, not a complete secret scanner |
| Consolidated independent review | Approved after fixes | Bounded correctness/security/config review; no remaining material findings |

Final GitHub CI runs the entire final core suite on Windows/Linux and
Python 3.11/3.12, optional document QA, and the new Windows/Python 3.12 SDK/Chromium
job. Consult the actual commit's checks; the local results above do not claim
remote CI completion in advance.

## Findings corrected before publication

- Added a separate WebSocket route block; HTTP route interception alone is
  insufficient. The single-page adapter also disables unsupported WebRTC and
  WebTransport APIs. This is not an OS-level network firewall.
- Rejected generic sequential/parallel starts for reserved Gmail-only scopes.
- Verify one prepared Google session before the durable send claim, and reuse
  that session for the sole POST. Failed preflight creates no immutable attempt;
  post-claim uncertainty never retries.
- Deterministic DNS failure precedes session intent creation. Setup failures
  release unstarted resources before removing the intent; uncertain setup retains
  it. Failed disposal retains handles and cannot become a false cleanup success.

## Explicitly unverified

Live Desktop OAuth, OS vault access, Gmail sending/delivery/bounce monitoring,
real employer logins/forms, ten live independent sessions, native Codex/Claude
marketplace installation and host-specific permission UI remain unverified.
The Chromium smoke uses a fictional HTTPS page with intercepted local HTML,
not a public employer site. Test PDFs are explicitly fictional byte fixtures;
existing document-render integration remains the separate rendering check.

Source publication and private install-package generation do not deploy a
hosted service or list these plugins in the universal public directory. Google
Cloud/OAuth setup is user-owned. No 100/hour or token/cost saving is inferred.
