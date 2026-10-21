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
