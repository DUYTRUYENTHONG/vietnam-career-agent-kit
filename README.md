# Vietnam Career Agent Kit

An open-source, local-first workflow for finding relevant jobs in Vietnam, tailoring truthful CVs and preparing supervised applications with an AI coding agent.

Clone it, give your agent the master prompt and provide your own approved CV. The agent can research permitted sources, assess requirements, draft an application package and help with a permitted application flow. The kit does not guarantee employment, ATS acceptance, interview rates or protection from account restrictions. It is not an unattended mass-application bot.

## Start in five minutes

Requires Git, Python 3.11+ and your existing agent. Core tools have no third-party Python dependencies and make no network calls.

```sh
git clone https://github.com/DUYTRUYENTHONG/vietnam-career-agent-kit.git
cd vietnam-career-agent-kit
python scripts/kit.py doctor
python scripts/kit.py --data-dir ../vietnam-job-search-private init
python -m unittest discover -s tests -v
```

On Windows, use your real Python executable or `py -3`; a Store alias may not run Python. Keep the private data directory outside the cloned repository. No installer, browser session, account login, API key or hook is created by cloning.

Open the checkout in Codex, Claude Code or another capable agent and paste:

> Read AGENTS.md and prompts/MASTER_PROMPT.md. Run the capability inspection first. My private data directory is ../vietnam-job-search-private. Ask only for missing facts and preferences. Help me discover suitable Vietnam jobs, assess them against my approved CV and prepare the strongest application one job at a time. Use computer control only where the destination permits the exact action. Show the exact package and answers before any disclosure. Begin in preparation-only mode.

Then provide your CV in the agent's authorized context or place it in your private directory. Do not paste candidate information into GitHub issues. The full [master prompt](prompts/MASTER_PROMPT.md) covers intake, discovery, tailoring, review, disclosure and submission.

## What is included

| Component | Purpose |
|---|---|
| Six shared skills | Candidate evidence, Vietnam job fit, tailoring/rendering, independent review, supervised browser work and application tracking |
| Codex and Claude entrypoints | Shared instructions with host-specific discovery adapters; no blanket permission grants |
| Private SQLite CLI | Local job tracking, package validation, artifact hashes and explicit approval records |
| Optional hook examples | Session reminders, conservative browser-action blocking, approval invalidation after edits and stop summaries |
| Fictional fixtures and tests | Exercise gaps, changed files/destinations, policy restrictions and storage behavior without live applications |
| Document guidance | Editable DOCX and text PDF workflow with render/inspect gates and optional pinned libraries |
| Source review | Pinned audits of four community references, license notes and intentional adaptations |

## Agent compatibility

| Host | Entry path | Status |
|---|---|---|
| Codex | AGENTS.md and `.agents/skills/` | Supported instruction structure; native hook schema must match the installed runtime |
| Claude Code | CLAUDE.md and `.claude/skills/` adapters | Documented structure; native execution not exercised in this release |
| Grokbot / other agents | Read AGENTS.md and paste the master prompt | Portable instruction path only; product identity, native skills/hooks and browser APIs unverified |

The kit uses the agent you already selected. It adds no paid AI API and makes no claim that cloud-model processing stays on your machine. Browser/computer control must be supplied by your host; there is no bundled authenticated browser or generic auto-submit CLI. See [compatibility](docs/COMPATIBILITY.md) and [tools](docs/TOOLS.md).

## A normal application cycle

1. Import only authorized CVs/evidence; record exact claims and resolve conflicts.
2. Confirm role track, seniority, Vietnam locations, work model, salary basis, availability, language, exclusions and prior applications. Ask only for missing fields.
3. Discover a bounded shortlist using permitted public/employer sources. Verify live JDs, exact locations and recipients; ignore stale search snippets as proof of activity.
4. Map required/preferred duties to evidence. Recommend strong fit, plausible fit, stretch or blocked-by-explicit-requirement with reasons.
5. Tailor one package: JD snapshot, evidence matrix, CV, optional cover letter, screening answers, critique, change log and hash manifest.
6. Review the exact package. Do not fill or upload personal data before specific disclosure approval. Autosaving fields and uploads can transmit before Submit.
7. Use a supported browser only for permitted actions. Default to manual final submission. Record observed confirmation separately from the candidate's reported submission.

Unknown salary, work authorization, language proficiency or start dates stay unknown. Remote does not establish eligibility to work from Vietnam. Overlapping jobs do not add extra years. Technical model scores are not commercial uplift.

## Platform modes

| Destination | Default |
|---|---|
| LinkedIn | Manual handoff; no automated logged-in reading/filling/submission without applicable authorization |
| Indeed | Manual unless an approved site-provided method permits the exact action |
| ITviec | Manual until intended assisted actions are clearly permitted |
| Employer/ATS | Check destination-specific terms and redirects; unknown scope stays manual |

Candidate approval cannot override platform restrictions. Do not bypass CAPTCHA, MFA, rate limits, access controls or browser warnings. Do not copy cookies, attach through arbitrary debug ports or use private APIs from traffic. [Policy register](templates/platform-register.json) starts with manual modes and contains no permanent authorization.

## Private data and approvals

`--data-dir` is required for storage commands and must resolve outside the framework checkout. Use one canonical private ledger. Templates contain fictional data; they are not permission to disclose anything.

An approval record binds company, job, exact destination, answers, consent and current artifact bytes. Changed content makes the approval stale. The record is local bookkeeping, not a cryptographic signature, authenticated user identity or global browser sandbox. Only record it after a real explicit candidate response; never manufacture confirmation text. Native host confirmation rules still apply. See [data contract](docs/DATA_CONTRACT.md).

## Optional hooks

Nothing is enabled by default. Read [hook setup and limits](docs/HOOKS.md), inspect `hooks/guard.py`, run the fictional tests and adapt the inactive examples to the installed host and exact local paths. Review/trust them through that host's supported flow. Never bypass hook trust.

The starter PreToolUse guard conservatively blocks recognizable browser/computer controls and transmission tools because generic clicks cannot establish recipient or effect. It is useful for preparation-only sessions. It does not turn approvals into live automation or catch every shell/MCP/hosted path. Missing, failing or unsupported hooks leave application handling manual.

## Development and release checks

```sh
python -m unittest discover -s tests -v
python scripts/check_repository.py
```

CI runs fictional local checks on Linux and Windows. It never searches accounts or submits applications. Keep changes small, add behavioral checks for new gates and run the public-data check before pushing. Never force-add private files. Pin/review updates to reference code or document dependencies rather than running unreviewed installers.

## References and license

Original implementation under the [MIT license](LICENSE). Design references: [job-apply-assistant](https://github.com/saizongmm/job-apply-assistant), [career-ops](https://github.com/career-ops-hq/career-ops), [ai-job-search](https://github.com/MadsLorentzen/ai-job-search) and [claude-resume-kit](https://github.com/ARPeeketi/claude-resume-kit). No reference repository code or candidate biography is bundled. Read the [pinned audit and attribution](docs/REFERENCE_REVIEW.md) before borrowing more.

This release supplies a reusable workflow and local guards. Employment outcomes, platform access, native host integration and live application success must be established in each user's environment.
