# Portable core architecture

## Community starter and source distribution

`core/starter.py`, exposed as `start-campaign`, records a private CV path/hash,
nullable intake fields and a default 100-application goal note. It reuses normal
workspace initialization, never imports/confirms candidate facts or acquires
browser/model tools, and refuses to overwrite a different or edited packet.
There is no database migration or new execution authority. `--target` changes
the total goal only; finite execution caps remain separately validated.

`scripts/package_community.py` archives one committed Git tree and scans the
archive before writing an external ZIP/digest manifest. It excludes untracked
workspaces and Git metadata. The anonymized public campaign snapshot is a
documentation case study, never imported into a candidate ledger or counted by
the engine. See [setup and release scope](COMMUNITY_START.md).

New user? [Clone/fork walkthrough](START_HERE.md) · [System models and diagrams](SYSTEM_MODELS.md).

## Optional local plugin transports

`core/performance.py` adds opt-in immutable caller-reported observations in
independently versioned tables of the existing workspace database. Application
schema stays unchanged. `core/career_memory.py` retrieves current confirmed fact
quotes through ephemeral local FTS5; `core/learning.py` exports exact independently
reviewed wording with provenance and job/output-group evaluation splits.
`adapters/career_mcp.py` exposes those same functions as an opt-in stdio server.
There is no second model API, fact promotion, automatic training or new authority.
See [career memory](CAREER_MEMORY.md) and [performance](PERFORMANCE_TRACKER.md).

`adapters/plugin_server.py` exposes separate stdio MCP email and browser servers.
`scripts/plugin_config.py` writes configured install packages only in an explicitly
selected external workspace; no global configuration or hook is installed.
The server opens an existing workspace and has no candidate/approval creation API.

`adapters/email_execution.py` binds the reserved `gmail-api-local` bridge to
the existing finite manifest and execution tables. A verified, prepared Google
session precedes an atomic unique attempt claim; one POST then returns an API
acknowledgement or uncertainty. Canonical tracker/counts see the same immutable
submission snapshots. `sending` survives crashes without replay. Browser starts
cannot reinterpret this transport. No new database/schema version is introduced.
`gmail_client.py` uses scoped Desktop OAuth, OS-vault credentials and a fixed API
endpoint. The identity lookup and send share the same session; no inbox access.

`adapters/local_browser.py` supplies an owned local session bridge over existing
parallel lanes and `PlaywrightForms`. It reuses current form/answer/consent/PDF
verification rather than creating another form engine. Per-job contexts/logins
stay in memory. HTTP redirects/off-origin requests and WebSockets are blocked;
unsupported WebRTC/WebTransport APIs are disabled. These checks are not an OS
network sandbox. Setup/cleanup failures retain unresolved handles and intents.
See [setup, limits and source references](LOCAL_PLUGINS.md).

The optional [TinyFish Browser runtime](TINYFISH_BROWSER.md) supplies a narrow
concrete cloud bridge, separate from public Fetch. Receipt writes remain
coordinator-owned; workers can read fresh authority guards. Finite action waits
quarantine stalls without retry. `dispatch_task` connects deterministic routing
to an explicit host callback; native model dispatch remains host-supplied.

Opt-in [CV content v2](CV_CONTENT_V2.md) adds `core/tailoring.py` as a Documents
mixin using existing canonical drafts and source/profile/JD/assessment hashes.
No new DB/schema or model API is introduced. Reviewed actual wording drives one
ordered line model for Markdown/DOCX/PDF; v1 exact selection remains unchanged.
See [parallel applications](PARALLEL_APPLICATIONS.md) for implemented opt-in concurrency
and [quality-and-speed slice plan](QUALITY_FAST_PLAN.md) for pending evidence reuse and form plans. `core/metrics.py` records local monotonic stages
only; unobservable host usage is explicitly unavailable.

## Capability map and build order

| Module | Responsibility | Depends on |
|---|---|---|
| contracts | Versioned validated inputs, outcomes, localization and policy | Standard library |
| ledger | External workspace, immutable evidence and transactional SQLite | contracts |
| preparation | Profile confirmation, JD normalization, fit and drafts | ledger |
| documents | DOCX/PDF rendering and reviewed artifact hashes | preparation |
| discovery | Permission-declared source imports/connectors and coverage | contracts, ledger |
| execution | Exact campaign authorization, browser boundary and attempt recovery | documents, discovery, ledger |
| adapters | Runtime-specific entrypoints using the same tools | preparation, execution |

Build order follows the vertical slices in roadmap.md. This is one system, not a merger of reference orchestrators.

## Slice 1 implementation contract

`core/ledger.py` retains the existing tested Kit implementation; `scripts/kit.py` remains the compatible executable/import entrypoint. `core/contracts.py` validates strict versioned inputs. `core/workflow.py` adds the preparation flow using the same `workflow.sqlite3`, not another database. New tables are additive and keep existing jobs/approvals/events. A higher unsupported schema version is blocked; repeated initialization preserves state.

SQLite is authoritative for candidate/profile confirmation, imported source metadata, job documents, assessments and drafts. Imported CV bytes live in content-addressed private evidence files; Markdown and reports are derived artifacts, not competing editable trackers. Every assessment/draft binds current profile, source and JD fingerprints. Resume reports staleness explicitly. Each workspace selects one candidate. No global candidate configuration exists.

`duplicate-candidates` is a read-only, same-employer ledger preflight before
tailoring. It exposes alternate-ID URL/title/city hints and recorded prior
attempt states without reading artifacts, merging records or granting clearance.
It uses existing schema 1–4 tables. See [contract and limits](DUPLICATE_CANDIDATES.md).

The host reasons and proposes structured profile/JD/matrix/selection files. Deterministic code validates them; it cannot authenticate a human or prove a semantic claim. Slice 1 only renders exact confirmed source quotes into drafts, with internal source mapping kept separate. No freeform agent-written experience bullet is accepted as new evidence. Profile confirmation is local bookkeeping after actual user review, not a signature.

UTF-8 TXT/Markdown CV import is implemented. PDF/DOCX input extraction remains pending. Slice 2 adds optional output rendering with absent tools returning manual_required. English/Vietnamese labels and document headings are selected explicitly. City aliases normalize for comparison while exact wording remains stored. Compensation fields never convert or infer gross/net, period, currency or bonuses.

## Slice 2 documents and manifests

core/rendering.py is an optional library/subprocess boundary: build DOCX, use a trusted local LibreOffice executable with an isolated profile to convert that file, compare text/embedded fonts, then rasterize every page under a PDFium lock. core/documents.py binds canonical selected facts, source/draft/profile/JD hashes, files and page hashes into a document set. Reviews accept only an exact fingerprint, all ordered pages and explicit content/layout/glyph/language checks. Rendering and review are distinct operations.

Schema 2 adds document_sets, document_reviews, campaign_manifests and campaign_approvals transactionally; it preserves existing canonical data. core/manifests.py validates finite plans, constructs exact review copies and records/checks/revokes expiring approval. It reuses current-render/source validation rather than implementing another evidence model. An explicit intent checks job, destination, operation and document/answer/consent hashes. New overlapping scopes revoke previous relevant approvals. resume reports document/manifest status without treating approval as submission.

These core paths are shared by scripts/kit.py. core/execution.py adds a durable host-mediated executor with additive schema 3. An explicitly reviewed bridge/runtime scope enables requests; preparation-only approvals stay disabled. One active coordinator, one pending action and a unique immutable attempt before submit prevent engine retries. The agent host supplies supported browser actions and observed receipts; the CLI cannot constrain arbitrary external tools. See execution.md for the protocol and trust boundary.

## Boundaries

`adapters/browser_act.py` is an offline planner for already-issued requests. It
reuses canonical action checks and returns owned session/state argument arrays,
never a browser process or application receipt. Write translation remains
unimplemented. See [BrowserAct scope and source audit](BROWSERACT.md).

Optional public network research is isolated under `adapters/providers/` and
explicit new CLI commands. Schema 5 adds private research tables to the same
database; ordinary commands make no provider calls. See [ADR](ADR-FAST-WEB.md)
and [setup/recovery/limits](FAST_WEB.md). Providers are separate from job sources;
research tasks and captured pages never count as applications or approval.

`core/dispatch.py` composes standing derivation/start/first request with explicit
partial-commit and nonreplay results. `core/cleanup.py` derives closure requests
only from saved confirmed bindings and verifies evidence before recording host
cleanup receipts. It does not drive a browser, infer ownership or alter counts.

Schema 4 adds opt-in standing delegation in `core/authorization.py`. An approved
profile/recipient/answer/consent scope derives exact reviewed manifests;
immutable child allocations share one cap. `Campaign.check_manifest` rechecks
the parent before the executor can disclose, including issued-action preflight.
Read-only receipt recovery remains available after revocation.
See [scope and trust boundaries](STANDING_AUTHORIZATION.md).

Selected-job document/handoff checks use a shared targeted checkpoint rather than
full-workspace resume. Frequent `tracker` output is a separate read-only ledger
projection with explicit nonvalidation semantics. `advance-execution` combines
receipt acknowledgement and one successor request without merging their durable
transactions. See [measured architecture decision](PERFORMANCE.md).

Every manifest entry still validates its current profile, JD, draft, rendered
bytes and review. Source/runtime/expiry are checked again after long passes.
Nothing is cached across browser actions. New immutable attempts retain assessed
fit classification. `throughput` projects qualifying confirmation records over
an explicit rolling window without reading artifact files; it cannot authorize
an action. See [KPI semantics](THROUGHPUT.md).

- Core setup/import/assessment/draft/report commands are local. They do not browse, call models, upload or submit.
- Maintainer instructions are AGENTS.md/CLAUDE.md. Job-seeker workflow is prompts/MASTER_PROMPT.md and canonical skills/policy, activated only by a career request.
- Source connectors declare operations separately. A registry entry is not an implemented connector or permission. Manual structured JD import is the working first connector.
- Runtime wrappers read shared skills and call the same CLI. They grant no permissions and install no active hooks/global settings. Generic CLI execution is distinct from native runtime/browser verification.
- Existing legacy package approval checking remains available. Slice 2 adds exact finite campaign approval validation. The execution engine now supports APPROVED_BATCH with durable attempts and read-only recovery; native employer integrations remain unverified.
- External computer tools outside this CLI are not sandboxed by core checks. Missing/failed host hooks never grant permission.

## Verification

Optional deterministic host planning uses `route-task` and
[MODEL_ROUTING.md](MODEL_ROUTING.md). It is independent of candidate state and
does not introduce a second model API, dispatcher service or native model switch.

Run `python -m unittest discover -s tests -v`, `python scripts/check_repository.py` and `python scripts/demo_slice1.py --data-dir ../career-demo-private`. The demo uses only checked-in fictional inputs and records a clearly labelled fictional confirmation. Integration tests execute the real CLI without model calls. CI covers Linux/Windows and Python 3.11/3.12; no external accounts are accessed.

## Experimental bulk discovery

`discover-greenhouse` performs fixed-origin, bounded read-only public GETs with up to three workers; normalization uses stable post identities and fingerprints. It does not access candidate workspaces, write the ledger or submit. See [contract, review and limits](BULK_DISCOVERY.md). Submission execution retains its single-writer and fresh-action checks.


## Parallel execution update

Schema 6 adds opt-in independent application lanes and public TinyFish Fetch batches. See [PARALLEL_APPLICATIONS.md](PARALLEL_APPLICATIONS.md) for commands, host requirements and measured-versus-unverified limits. Earlier sequential-only/TinyFish-unsupported descriptions apply to previous increments. [TinyFish Browser](TINYFISH_BROWSER.md) now has an opt-in experimental guest-form adapter; Agent-goal submissions remain unsupported.
