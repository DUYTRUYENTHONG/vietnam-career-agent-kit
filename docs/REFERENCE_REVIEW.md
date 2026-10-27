# Community references and attribution

## Context Engineering collection, 27 October 2026

Reviewed selected files at `9ff0c99108b36d3b886defd825d8ac1f47dba374` from
`muratcankoylan/Agent-Skills-for-Context-Engineering` as untrusted data, cloned
outside the kit. Exact file hashes, inspected scope and dependency observations
are in [the source record](../adapters/context-engineering.source.json).
Root MIT; the self-managed-context harness reference attributes its source
implementation to CC BY-NC 4.0 material, which is not copied or ported here.
No upstream scripts, plugins, researcher loop or installation were executed.
Original guide adaptations cover selective retrieval and durable checkpoints;
no new canonical skill, second ledger, model API or runtime control is added.
Six fictional manual continuation cases are documented in
[the targeted review](CONTEXT_ENGINEERING_REVIEW.md). Compatibility is
Instruction-only; KV sharing, live-message rewriting and performance claims
remain unverified. Repository gates are reported separately in the PR.

## Awesome Copilot browser and context patterns, 27 October 2026

Cloned `github/awesome-copilot` at
`d106008300bd4c8396e9c3c085c7c8e3ed976d48` for targeted static review.
Thirty-five pinned Git-blob hashes, inventory counts, licenses, dependencies and
adopt/defer/exclude decisions are recorded in
[`adapters/awesome-copilot.source.json`](../adapters/awesome-copilot.source.json).
Root MIT copyright GitHub, Inc.; the GEM team plugin declares Apache-2.0 and is
not copied. No upstream code, skill text, assets, hooks or installers were run or
redistributed. Original observed-UI guidance extends the existing browser skill;
the skill-management guide retains ten canonical owners and progressive loading.
Eight fictional instruction cases received a separate manual review. Native
Codex/Copilot-canvas support and measured speed/cost improvements are unverified.
See [the review](AWESOME_COPILOT_REVIEW.md) and [management guide](SKILL_MANAGEMENT.md).

## Live Resume writing guidance, 26 October 2026

Reviewed `guilhermeborgesbastos/live-resume` at
`07c0680129ecf0226d802d23233fe7d1bea9121f` (MIT, 2020 Guilherme Borges Bastos).
Eight exact Git-blob hashes and dependency/exclusion decisions are recorded in
[the source record](../adapters/live-resume.source.json). Its only discovered
skill creates bilingual portfolio post cards, not CVs or emails. Original
evidence-first guidance is integrated into the existing tailoring skill and
email prompt; no upstream text, code, website, Humanizer dependency, installer
or candidate content is copied or run. Five fictional instruction-level cases
passed manual review. Native host/model compliance and measured quality/latency
improvements remain unverified. See [adoption and cases](LIVE_RESUME_REVIEW.md).

## Local MCP email/browser plugins, 26 October 2026

Original implementation; no upstream source, sample code or skills copied.
Reviewed official Google Desktop OAuth/PKCE and Gmail messages.send documentation,
Playwright authentication/BrowserContext routing, OpenAI portable plugin packaging,
and the MCP Python SDK maintenance release notes. Concrete source links are in
[LOCAL_PLUGINS.md](LOCAL_PLUGINS.md). The initially evaluated SDK1.26.0 was replaced
with maintenance1.30.0 after the upstream release review; the retained stdio API
supports the tested 2025-era initialization/tools protocol, not an untested 2026
protocol claim.

Adopted optional package versions: MCP1.30.0 MIT, google-auth-oauthlib1.5.0
Apache-2.0, keyring25.7.0 MIT and Playwright1.58.0 Apache-2.0. Exact PyPI metadata
URLs/hashes and all 48 resolved distribution versions/license declarations live
in `adapters/local-plugins.source.json`; wheel hashes in
`requirements-plugins.lock`. This Windows/Python3.12 closure is separate from the
core and document/browser profiles. No binaries are redistributed. Acceptance is
scoped to [fictional local QA](LOCAL_PLUGINS_QA.md), not live account/provider or
native plugin installation. No account access or credentials follow from this review.

## TinyFish Browser runtime, 26 October 2026

Reviewed cookbook revision `78b7c3336289f0f3e1a3696801945de8489ab097`
(MIT), official Browser REST documentation and official Playwright CDP reference.
Exact source URLs, fetched-byte hashes and byte sizes are recorded in
`adapters/tinyfish-browser.source.json`. No upstream code was copied or executed.
The implementation is original MIT kit code. The optional Playwright 1.58.0,
pyee 13.0.0, greenlet 3.1.1 and typing_extensions 4.16.0 wheel closure was generated
from exact PyPI release metadata into requirements-browser.lock; versions,
dependencies, hashes and license metadata are in dependency-lock.json. No package
was installed by this change's tests. Live Browser API calls are paid and require
separate scoped provider disclosure; fictional transport/page tests are the
current acceptance boundary. See [setup and limitations](TINYFISH_BROWSER.md).

## Wording v2 and monotonic traces, 22 October 2026

Original stdlib implementation; no third-party code, templates, SDKs, model
services or licenses added. Existing document lock and process/PDFium boundaries
are reused unchanged. The [official Python 3.12 time API](https://docs.python.org/3.12/library/time.html#time.perf_counter_ns)
was checked for nanosecond duration measurement. This is an API reference, not a
vendored dependency or a claim that wall-clock timestamps measure elapsed time.
No external skill update, download, installer or hook was adopted in this slice.

Static review performed 21 October 2026. These exact commits were inspected as untrusted source material. No installer, lifecycle script, updater, browser, hook or reference program was executed. No candidate data was provided. This kit uses design ideas with original implementation; it does not vendor those repositories or their candidate examples.

| Reference | Reviewed commit | Root license | Useful idea |
|---|---|---|---|
| [saizongmm/job-apply-assistant](https://github.com/saizongmm/job-apply-assistant) | fbce87dc99bc1ac09df4148b9677d5db9fb63d0e | MIT | Deduplication, source-backed tailoring, separate Opened/Applied states |
| [career-ops-hq/career-ops](https://github.com/career-ops-hq/career-ops) | c87e0f05a5bf3b0e7bff1f6c87fd0865191e7da7 | MIT | Private user-data contract, evidence reports and lifecycle tracking |
| [MadsLorentzen/ai-job-search](https://github.com/MadsLorentzen/ai-job-search) | 4339153f8f5e4bb69eaee2a50af713815409e8e7 | MIT | Market-aware discovery, factual drafting and separate review |
| [ARPeeketi/claude-resume-kit](https://github.com/ARPeeketi/claude-resume-kit) | 69930e9de21d5595f9b8c9427adc9c51a9fcbc0e | MIT | Experience inventory and explicit writing/rendering checks |

## Important boundaries found

**job-apply-assistant:** requirements contain ranged openpyxl/python-docx dependencies. Its `open_jobs.py` opens workbook URLs in installed browsers and has a Windows cmd/start fallback. URL handling and logged-in-session assumptions are not adopted. Its SKILL describes manual application, not unattended submission. No account-safety claim from that reference is adopted.

**career-ops:** root package lifecycle includes a Playwright Chromium download. Apply mode and `apply-scope.mjs` use an owned project-launched Playwright browser and prohibit attachment-style options, remote debugging and personal profiles. Its update system can fetch and bootstrap upstream executable code. Model/integration paths can target OpenAI/configurable bases, OpenRouter, Google, Ollama, Notion, Gmail/OAuth and Apify, plus job boards/ATS. Those providers, plugins and updater are not enabled here. Its PDF context disables JS/remote resource requests but permits local file resources; that is not an OS sandbox.

**ai-job-search:** Danish portal examples remain, with four Danish skills disabled by default and LinkedIn/Freehire enabled in the reviewed revision. It does not ship automatic hooks in the tracked inventory/settings. LinkedIn/Freehire CLI runtime dependencies are empty; the Danish CLIs have dependencies, so the entire project is not dependency-free. Installer/update and portal code can invoke Bun, fetch public pages or Git remotes. None is executed or relabeled as Vietnam authorization.

**claude-resume-kit:** includes Claude skills, Python helper and LaTeX classes. Bundled cv/resume classes carry additional Trey Hunner attribution/preservation notices beyond the root MIT license. No class/template code is copied here. Research instructions may cause agent-host network access even without a direct HTTP client.

## Intentional adaptations

One original Python private ledger replaces four competing orchestrators. Canonical shared skill text has Codex/Claude adapters. Browser actions are provided by the current host and evaluated independently; this is not a modification claiming existing-session support in career-ops. Vietnam locations, exact compensation bases and destination permission gates are explicit. No author biographies, salaries, exclusions or example candidates were imported.

The audit covers primary manifests, browser/render/update paths, declared integrations and tracked hook/settings inventories. It is not an exhaustive vulnerability audit, signed provenance check, transitive dependency review or permanent authorization to install. New revisions/dependencies/templates require review. Preserve the original license notices if copying code later.

## Product-slice reinspection

On 21 October 2026 the pinned files below were retrieved through GitHub's contents API and dependency/browser/license-relevant lines were inspected again. The web reader could not open pinned tree URLs; GitHub CLI supplied read-only public source. No reference code was executed, installed or copied. Hashes describe retrieved file bytes.

| Repository | Exact inspected file | SHA-256 |
|---|---|---|
| job-apply-assistant | LICENSE | 694af8d1e98e12b1fc55fe67676631f5916f5bb8f1260fb730dc77cd862d6e38 |
| job-apply-assistant | requirements.txt | 0cdc43560951cd68bc3151b7ee3dbef7825ee560be8d81cb16f718b7fcb437fb |
| job-apply-assistant | skills/job-apply-assistant/scripts/open_jobs.py | eef1d05ce377e31772aa7e583bb47c3dd9da44bd4eab953ef0def63e08835456 |
| career-ops | LICENSE | 51989d2589b2aa87ca6cbb253391bcb476a21cbafdc71eea4410548538510870 |
| career-ops | package.json | 32febbd01b690af8980931bde4bc3415ffa8b3d71fe72e30a701ddbe19256e50 |
| career-ops | apply-scope.mjs | 6ace71ca7e9c1fc8b1e4d9f617035d7c6b4b17a41f14f7fae1e3dc59e892e53f |
| ai-job-search | LICENSE | accbf0accb87b7b905dd7ee0c7013075f0453637acf354ddae6fc0e4d8282e8e |
| ai-job-search | .agents/skills/linkedin-search/SKILL.md | f7d0a742b12c57340e3d5c23b7c154e153f7e64ce37a168b73e0196de0c41e30 |
| ai-job-search | README.md | 0e295c5f268bc7b6bc6f218b6b1fe3a826c8b5b70564a9499f8ab74237d1f5e4 |
| claude-resume-kit | LICENSE | d6031b6830e5aa1b04dc536c575d443c62bf3cf56d2a7ccd492f0077279d8019 |
| claude-resume-kit | resume_builder/templates/cv.cls | 30bf0ca5b3d0b7185d6ee42be20c146dd3853e4212d73176acdf5d7e6b0db42c |
| claude-resume-kit | resume_builder/templates/resume.cls | 721ed8d5e80fcc54d829eba481b8b37b7d2e18574758828eed8b94551879e69e |

Retained ideas are provenance/deduplication, one private tracker, separate critique and rendering checks. Ranged dependencies, Playwright install lifecycle, browser-attachment refusal, market-specific defaults and class notices support using original bounded modules rather than combining orchestrators. This is not a full-source/transitive security certificate. THIRD_PARTY_NOTICES.md records that no reference code/assets are bundled.

## Company Skill Library routing reference

Used the installed `company-skill-library:company-task-routing` skill, package
`0.1.0+codex.20260914012433`, on 21 October 2026. Exact package file hashes:

| Package-relative file | SHA-256 |
|---|---|
| skills/company-task-routing/SKILL.md | a62b162ac4a911b3c832aaadf35bb4bf625a13a978e141f0a9961782b88dd7b9 |
| scripts/route.mjs | 76419c99b8022f7fad96f48457f92db882b205a83877afbabf81e1ebd66059ff |

The installed pure router was run with the actual host inventory and existing
owner: planning/complex/tool routes were ready; unavailable preferred simple and
routine model IDs blocked. No dispatch or paid model call was performed by it.
The package declares Node 22+ and no npm dependencies. Its installed artifact
does not include a root license or Git commit identifier; these remain unknown,
so no source code, catalog or skill text is redistributed or installed by this
kit. The portable Python planner is an original implementation of the requested
deterministic policy, with explicit caller policy/skill candidates instead of
copying the company capability catalog. It adds no runtime dependency.

On 22 October the installed router was run again with the existing owner and
actual inventory: tests routed directly to tools, architecture planning selected
gpt-6-astra/high, and simple coding blocked on unavailable gpt-5.6-luna/low. These
are routing plans only; no model dispatch, paid model call or estimated saving.

## Public ATS discovery documentation, 22 October 2026

Reviewed the official Greenhouse Job Board API, Lever Postings API and
SmartRecruiters public Posting API documentation for bounded read-side discovery.
Exact links and limitations are in DISCOVERY_ACCELERATION.md. This is a dated
documentation review, not a pinned dependency adoption, connector implementation,
employer test or permission certificate. No source code/examples were copied,
installed or executed, so no new third-party runtime/license dependency is added.

## Firecrawl v2 public research contract, 22 October 2026

Official API documentation was reviewed for search, scrape and asynchronous batch
start/status/errors/cancel. HTTP contract version: v2; no SDK dependency or copied
server/SDK code. Official docs source revision:
`7688a89978d354c8458ee2f77ce047a4f246797f` at
https://github.com/firecrawl/firecrawl-docs/tree/7688a89978d354c8458ee2f77ce047a4f246797f .

| Reviewed path | SHA-256 of exact retrieved bytes |
|---|---|
| api-reference/v2-openapi.json | 849076a3180d41c457e9d774ad773fef4f84d02b609f4e522adb36873860b3d5 |
| features/batch-scrape.mdx | 73216998c1c1cda6ad1839e852be2c5e24150df197e9a5030c3a5dacc90a2e78 |

Live official endpoint pages: [search](https://docs.firecrawl.dev/api-reference/endpoint/search),
[scrape](https://docs.firecrawl.dev/api-reference/endpoint/scrape),
[batch start](https://docs.firecrawl.dev/api-reference/endpoint/batch-scrape),
[status](https://docs.firecrawl.dev/api-reference/endpoint/batch-scrape-get),
[errors](https://docs.firecrawl.dev/api-reference/endpoint/batch-scrape-get-errors),
[cancel](https://docs.firecrawl.dev/api-reference/endpoint/batch-scrape-delete).
The batch guide documents asynchronous IDs, 24h result availability after
completion and the full-account default unless maxConcurrency is explicitly set.
Our adapter sets one per-domain batch worker and validates continuation origins.
The repository license endpoint returned 404; no docs/server/SDK source is copied,
redistributed, installed or relicensed. Hosted terms and account capability are
not established by reading the spec. Tests use original fictional fake transport;
live provider/account verification has not run. TinyFish APIs are not implemented
or certified by this review.

## TinyFish ten-URL Fetch review

Official reference: https://github.com/tinyfish-io/tinyfish-cookbook at revision `78b7c3336289f0f3e1a3696801945de8489ab097` (MIT). Read-only checkout; no reference hooks, installers, SDKs or code copied. Original standard-library adapter implements the documented Fetch JSON request: POST https://api.fetch.tinyfish.ai with urls and format=markdown.

Reviewed source SHA256:
- README.md: `8b3a8a642e18054c048276e77dfa0dd1a011339f4187fbb9c66a24b8e0f7a3f1`
- skills/tinyskill/SKILL.md: `9d976035919f78865eaa17fdb00f67305159f4ab52c83007a3f799774bf572b6`

Fetch supports up to ten URLs per batch. Server scheduling is provider-controlled. Agent and direct Browser execution were deliberately excluded from this increment. Only fictional injected transport is tested; no account quota, price, live latency or employer application support is certified.

## Setup documentation source check — 26 October 2026

The new setup guides describe the existing original adapter and CLI. Rechecked
the official [TinyFish Fetch contract](https://docs.tinyfish.ai/fetch-api/reference)
and [authentication](https://docs.tinyfish.ai/authentication),
[OpenAI skill discovery](https://learn.chatgpt.com/docs/build-skills),
[Claude Code skills](https://code.claude.com/docs/en/skills) and
[hooks](https://code.claude.com/docs/en/hooks). These establish upstream interfaces,
not kit-native acceptance. No upstream code, SDK, installer or hook was adopted;
the pinned cookbook review above remains the implementation reference. The guide
explicitly records the adapter's narrower Fetch request, absent `.env` loading,
unforwarded freshness field and separate host-browser requirements. Grokbot/Muse
native integration remains unverified and is not inferred from these sources.

## BrowserAct session and authorization review, 26 October 2026

Reviewed https://github.com/browser-act/skills at `11c057b03f92101642cadc9f840564574120d184` as untrusted source text. Entry skill version2.0.2. No upstream installers, runtime `get-skills`, hooks, executable code or profile tools were run. No source/skill text or binary is copied.

| Exact inspected path | SHA-256 of Git blob bytes |
|---|---|
| LICENSE | ea8eaae0fd525d840d432430af5133224cb363703cc0e3b265988d34c7601906 |
| browser-act/SKILL.md | b0a3a22320d22610bb2b0dac085514c57c8f3dbfc1249b717af6ecd714913372 |
| docs/commands.md | b0517aff6f007afe795a22d554a4036d2797b3603d3504af9aed314cdf8bc617 |
| docs/concurrency.md | b12aaba78f8f89bb9772e5715dafbd32a7cd84fba68783a6709886ceb525f6cb |
| docs/agent-design.md | 6683490b4581de619dcc6b600dc2bb9b43d43be4f579bdf660b65bdd270266d2 |
| docs/installation.md | f6f0e06f52efd7384ce8481e69560269ab9cd7ba233fda4a3a1631142c66931a |
| docs/remote-assist.md | cec0c1208364cd2aaecab988f74a8fe53e8d8231fd276ea6e5c8268dc9e8eb46 |
| docs/skills.md | 0671c02f8803fbad36a5c3453d4f22a6008c6b1d590d27db89cfe6af80e63fef |

The repository is MIT (2026 BrowserAct). [Pinned CLI1.4.5 metadata](https://pypi.org/project/browser-act-cli/1.4.5/) declares Python==3.12.*, many ranged dependencies and platform-specific compiled wheels; it declares no license/license-expression. Full dependency and wheel hashes are retained in [the source record](../adapters/browser-act.source.json), not installed as kit dependencies. A static skill review is not a binary audit or license grant for those artifacts.

Adopted through original code: deterministic owned session names, compact-state planning and the existing exact-action/standing authorization checks. Confirmation gates in the upstream agent-design guide are conversation-level guidance, not CLI hard-blocks. Service authentication is separate from candidate/host authority. Same-browser sessions share cookies; upstream non-correlation, local-only and speed claims are not certified. Runtime instruction updates, profile/cookie import, network captures, remote-access links, proxies, CAPTCHA services and diagnostic log uploads are not adopted.

Acceptance: offline planner and fictional authorization/receipt-recovery tests only; fill/upload/submit returns manual_required. CLI installation, native browser driving, real-employer throughput and binary/transitive security remain unverified. See [integration review](BROWSERACT.md).
