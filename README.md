# Vietnam Career Agent Kit

Bring your own AI agent and CV. Run an organized, evidence-based Vietnam job search with reusable tools and controlled application automation.

[Tiếng Việt](README.vi.md) · [Product goal](GOAL.md) · [Architecture](docs/architecture.md) · [Compatibility](docs/compatibility.md) · [Roadmap](docs/roadmap.md)

**Working now:** a local preparation CLI: diagnose → private workspace → UTF-8 CV/profile import → exact profile confirmation → structured JD import → evidence matrix → tailored Markdown draft → tracker/report/manual handoff → resume. Ten shared skills and Claude wrappers support the workflow. Fictional examples cover two users, cities, roles and languages.

**Not yet implemented:** PDF/DOCX extraction/rendering, network job connectors, native browser execution and finite approved-batch submission. The legacy package hash checker is local bookkeeping, not a batch executor. Do not infer these capabilities from a skill, hook example or provider name. [Slice gates](docs/roadmap.md) remain explicit.

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
| `resume`, `status`, `report`, `handoff` | Local checkpoint or explicit manual handoff |
| Legacy `check-package`, `record-approval`, `check-approval`, `invalidate` | Content-bound local bookkeeping; no authenticated human identity, expiry-bound batch or browser grant |
| Fill/upload/submit | No live execution command in this slice; host/site/user permission and future tested execution guards required |

Structured operations return `schema_version`, `outcome`, `data`, `issues`, `message`. Outcomes: `ok`, `blocked`, `needs_input`, `manual_required`, `failed`, `submission_unknown`. Exit 0 means the local operation succeeded; exit 2 means inspect the outcome and next input. A manual handoff is not a submitted application. [Tool/data contract](docs/DATA_CONTRACT.md).

## Compatibility and sources

| Interface | Label | Actual scope |
|---|---|---|
| Generic local Python CLI | Verified on recorded test matrix | Deterministic commands/fictional tests; no native agent/browser certification |
| Codex desktop tool execution; CLI 0.137.0 inventory | Experimental | This development flow executes local tools; native project-skill/hook callbacks not integration-tested |
| Claude Code 2.1.205 inventory | Instruction-only | Generated shared-skill wrappers; native agent execution/hooks not tested |
| Grok Bot / unidentified Grok runtime | Unsupported natively | Generic text/manual path only; no invented SDK, hooks or browser support |

[Compatibility evidence](docs/compatibility.md) lists versions, OS, documentation and limits. Coding CLIs and consumer chat websites differ. Ten wrappers do not create ten installed tools. `python scripts/generate_adapters.py --dry-run` previews repository-owned wrapper changes; `--check` detects drift. No global settings or active hooks are overwritten.

[connectors/registry.json](connectors/registry.json) declares discover/read/extract/fill/upload/submit/verify separately. Manual structured JD import works. Employer pages, feeds, universities and LinkedIn/Indeed/JobsGO/ITviec/TopCV/VietnamWorks/CareerViet are potential sources, not enabled connectors. Unknown permissions stay manual; snippets are leads, and only executed finite searches count as coverage.

## Costs, hooks and development

Core dependencies are standard library only, recorded in [dependency-lock.json](dependency-lock.json). Optional document pins are not a complete transitive renderer lock and are not auto-installed. Existing agent subscriptions, model usage, search APIs and future browser/render services may cost separately. There is no compulsory second model API, maintainer cloud service or default telemetry.

Optional [hook examples](docs/HOOKS.md) are inactive. Their conservative helper blocks recognized control names in preparation sessions and marks prior approvals stale after recognized edits; it cannot sandbox arbitrary shell/MCP/host actions. No auto-trust, permission bypass, CAPTCHA, cookie extraction or stealth. Employment, interview, ATS and universal-coverage guarantees are outside the product promise.

```sh
python -m unittest discover -s tests -v
python scripts/generate_adapters.py --check
python scripts/check_repository.py
python scripts/demo_slice1.py
```

Read [CONTRIBUTING.md](CONTRIBUTING.md), [SECURITY.md](SECURITY.md), [CHANGELOG.md](CHANGELOG.md) and maintainer AGENTS.md. CI uses fictional data, no paid model calls and no real employer applications. [MIT](LICENSE) covers original code; [third-party notices](THIRD_PARTY_NOTICES.md) and the [pinned reference review](docs/REFERENCE_REVIEW.md) distinguish ideas from copied code. No reference candidate examples, installers or orchestrators are bundled.
