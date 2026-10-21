# Community references and attribution

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
