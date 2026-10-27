# Vietnam Career Agent Kit

[Standing authorization](docs/STANDING_AUTHORIZATION.md) reuses one approved
recipient/answer/consent scope across later reviewed CVs and finite batches.
It shares one application cap, expiry and revocation; host-required confirmations
remain separate. Opt-in CLI support uses additive schema 4.

Bring your own AI agent and CV. Run an organized, evidence-based Vietnam job search with reusable tools and controlled application automation.

[Continue and close completed application tabs](prompts/AUTO_PROCEED.md) provides
a reusable campaign prompt: reuse confirmed answers and valid authority, save the
receipt, close the exact agent-created tab, verify absence and update the tracker.

[Tiếng Việt](README.vi.md) · [Product goal](GOAL.md) · [Architecture](docs/architecture.md) · [Compatibility](docs/compatibility.md) · [Roadmap](docs/roadmap.md)

**Working now:** a local preparation CLI: diagnose → private workspace → UTF-8 CV/profile import → exact profile confirmation → structured JD import → evidence matrix → tailored Markdown draft → tracker/report/manual handoff → resume. Ten shared skills and Claude wrappers support the workflow. Fictional examples cover two users, cities, roles and languages.

**Slice 2 adds:** optional source-bound DOCX → local LibreOffice PDF → page previews, explicit page review, and exact expiring approval manifests. [Rendering and approval setup](docs/documents-and-approval.md) explains dependencies, commands and limits. Plans without explicit execution scope remain preparation only.

**Execution engine:** an exact approved host-browser loop now supports sequential fill/upload/review/submit/verify, durable attempts, finite budgets and read-only recovery. See [execution setup and protocol](docs/execution.md). The agent supplies supported browser tools; the CLI does not acquire a browser.

**Faster local pipeline:** selected-job validation avoids all-job scans;
`advance-execution` combines receipt and successor; `tracker` exports a fast
catch-up table. [Measurements and architecture](docs/PERFORMANCE.md) distinguish
local gains from unmeasured live-browser time.

**Model efficiency:** [deterministic routing](docs/MODEL_ROUTING.md) uses tools for
tests/status/metrics and an explicit model policy for agent work. `route-task`
checks host inventory without calling a model or silently changing models.

**Throughput KPI:** [rolling confirmation reporting](docs/THROUGHPUT.md) measures
an explicit target such as 100 qualifying confirmations in 60 minutes. It counts
confirmed fit-reviewed records, not prepared files or attempted clicks. No live
100/hour performance claim has been verified.

**Campaign continuity:** [goals and checkpoints](docs/campaign-continuity.md)
guide successive finite batches, resume from one private ledger, and count only
confirmed new submissions toward a user-selected target. Persistent goals require
a supported host; this guidance does not add a scheduler or browser worker.

**Not yet implemented:** PDF/DOCX CV extraction, network job connectors, standalone unattended browser workers and verified employer-specific adapters. Do not infer these capabilities from a skill, approval record, hook example or provider name. [Slice gates](docs/roadmap.md) remain explicit.

## Try the working slice

Requires Git and a real Python 3.11+ interpreter. No pip install, API key, account login, browser driver or model call is needed for these commands.

```sh
git clone https://github.com/DUYTRUYENTHONG/vietnam-career-agent-kit.git
cd vietnam-career-agent-kit
python scripts/kit.py doctor --runtime generic
python scripts/demo_slice1.py --data-dir ../career-demo-private
python scripts/kit.py --data-dir ../career-demo-private resume
python scripts/kit.py --data-dir ../career-demo-private report --format md --output reports/checkpoint.md
```

Use a new empty demo directory. The demo imports fictional candidate A, records a clearly fictional profile confirmation, produces a source-bound Markdown CV and leaves a `review_required` tracker record. It never connects to `example.test` or submits an application. Use `--candidate b` with another empty directory for the Vietnamese operations example. Omit `--data-dir` for a disposable demonstration that cleans up its own temporary workspace.

On Windows, `py -3` or an absolute real interpreter path may be needed; the Store alias is not an interpreter. [Measured setup and recovery](docs/setup.md) includes the individual commands and outcomes.

## Use your own agent and CV

Open the clone in your chosen agent and paste:

> This is a job-seeker request. Read prompts/STARTUP.md and docs/job-seeker-policy.md. Diagnose my selected runtime, reuse or initialize one explicitly chosen external private workspace, and ask only for missing candidate facts/preferences. Start in PREPARE. Use only capabilities reported by the installed kit. Do not upload, enter personal data or submit without an exact permitted disclosure scope and my approval.

The agent may draft versioned inputs using [schemas/contracts.schema.json](schemas/contracts.schema.json) and examples. Import your authorized text CV with `import-cv`, then a source-backed profile with `import-profile`. That returns `needs_input` until you review and explicitly confirm its fingerprint. Generated prose is not evidence. Pending/rejected facts cannot enter the CV; exact quotes preserve qualifiers. The kit validates linkage and structure, not the truth of a human's claim or every semantic requirement.

Keep CVs, evidence, salary, answers, trackers and screenshots in the selected directory **outside this clone**. One workspace selects one candidate. SQLite is authoritative; Markdown/reports are derived. Local-first means user-controlled storage; content supplied to a cloud agent may be processed remotely by that provider. Never put candidate information in public issues or fixtures.

## Local commands and external disclosure

| Operation | Current behavior |
|---|---|
| `doctor`, `source-registry` | Read-only capability/registry output; no account connection |
| `init`, `import-cv`, `import-profile`, `confirm-profile` | Private local evidence/profile state |
| `import-jd`, `assess`, `prepare` | Private local job/matrix/draft state; no website operation |
| `render`, `review-documents`, `reject-documents` | Optional local DOCX/PDF/page generation and explicit review; no disclosure |
| `create-manifest`, `approve-manifest`, `check-manifest`, `revoke-manifest` | Exact finite authorization records and expiry/hash checks; execution requires an explicitly reviewed bridge/runtime scope |
| `create-authorization`, `approve-authorization`, `check-authorization`, `revoke-authorization`, `authorize-manifest` | Opt-in bounded standing delegation across reviewed batches; shared allocations and revocation, with host confirmations separate |
| `launch-execution` | Combine standing authorization, start and first request; reuse existing authority without another local prompt, never replay an existing run |
| `cleanup-execution`, `record-cleanup` | After saved confirmation, return exact tab cleanup instructions and record host-reported closure; preserve uncertain/user-owned tabs |
| `resume`, `status`, `report`, `handoff` | Local checkpoint or explicit manual handoff |
| `tracker` | Fast recorded-status table; does not validate artifacts, approvals or live vacancies |
| `route-task --packet task.json` | Read-only model/tool plan using explicit host capabilities; no workspace or model API required |
| `throughput --target 100 --window-minutes 60` | Rolling confirmation KPI; old records without frozen fit are separate, never inferred |
| Legacy `check-package`, `record-approval`, `check-approval`, `invalidate` | Content-bound local bookkeeping; no authenticated human identity, expiry-bound batch or browser grant |
| `start-execution`, `next-action`, `check-action`, `record-action`, `advance-execution` | Durable sequential engine; designated agent performs each request through supported browser tools |
| `execution-status`, `stop-execution`, `recover-execution` | Inspect/stop or reconcile an uncertain attempt read-only; no duplicate submit |

Structured operations return `schema_version`, `outcome`, `data`, `issues`, `message`. Outcomes: `ok`, `blocked`, `needs_input`, `manual_required`, `failed`, `submission_unknown`. Exit 0 means the local operation succeeded; exit 2 means inspect the outcome and next input. A manual handoff is not a submitted application. [Tool/data contract](docs/DATA_CONTRACT.md).

## Compatibility and sources

| Interface | Label | Actual scope |
|---|---|---|
| Generic local Python CLI | Verified on recorded test matrix | Deterministic commands/fictional tests; no native agent/browser certification |
| Codex desktop tool execution; CLI 0.137.0 inventory | Experimental | This development flow executes local tools; separate fictional browser fill/upload/submit smoke passed; engine bridge tested deterministically; native skill/hooks and real employer integration unverified |
| Claude Code 2.1.205 inventory | Instruction-only | Generated shared-skill wrappers; native agent execution/hooks not tested |
| Grok Bot / unidentified Grok runtime | Unsupported natively | Generic text/manual path only; no invented SDK, hooks or browser support |

[Compatibility evidence](docs/compatibility.md) lists versions, OS, documentation and limits. Coding CLIs and consumer chat websites differ. Ten wrappers do not create ten installed tools. `python scripts/generate_adapters.py --dry-run` previews repository-owned wrapper changes; `--check` detects drift. No global settings or active hooks are overwritten.

[connectors/registry.json](connectors/registry.json) declares discover/read/extract/fill/upload/submit/verify separately. Manual structured JD import works. Employer pages, feeds, universities and LinkedIn/Indeed/JobsGO/ITviec/TopCV/VietnamWorks/CareerViet are potential sources, not enabled connectors. Unknown permissions stay manual; snippets are leads, and only executed finite searches count as coverage.

[Faster discovery guidance](docs/DISCOVERY_ACCELERATION.md) covers public ATS
listings, coverage reuse and candidate-authorized adjacent role families. It is
instruction-only; the network connector remains pending.

## Costs, hooks and development

Core dependencies are standard library only, recorded in [dependency-lock.json](dependency-lock.json). [Optional document dependencies](requirements-documents.lock) have a complete Python closure with exact versions/wheel hashes and are not auto-installed. LibreOffice and fonts are separately provisioned, measured external dependencies. Existing agent subscriptions, model usage, search APIs and future browser services may cost separately. There is no compulsory second model API, maintainer cloud service or default telemetry.

Optional [hook examples](docs/HOOKS.md) are inactive. Their conservative helper blocks recognized control names in preparation sessions and marks prior approvals stale after recognized edits; it cannot sandbox arbitrary shell/MCP/host actions. No auto-trust, permission bypass, CAPTCHA, cookie extraction or stealth. Employment, interview, ATS and universal-coverage guarantees are outside the product promise.

```sh
python -m unittest discover -s tests -v
python scripts/generate_adapters.py --check
python scripts/check_repository.py
python scripts/demo_slice1.py
```

Read [CONTRIBUTING.md](CONTRIBUTING.md), [SECURITY.md](SECURITY.md), [CHANGELOG.md](CHANGELOG.md) and maintainer AGENTS.md. CI uses fictional data, no paid model calls and no real employer applications. [MIT](LICENSE) covers original code; [third-party notices](THIRD_PARTY_NOTICES.md) and the [pinned reference review](docs/REFERENCE_REVIEW.md) distinguish ideas from copied code. No reference candidate examples, installers or orchestrators are bundled.
