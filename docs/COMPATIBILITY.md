# Agent and browser compatibility

Reviewed official documentation on 21 October 2026:

- [Codex skill discovery](https://learn.chatgpt.com/docs/build-skills)
- [Codex hook lifecycle and trust](https://learn.chatgpt.com/docs/hooks)
- [Claude Code skills](https://code.claude.com/docs/en/skills)
- [Claude Code hook reference](https://code.claude.com/docs/en/hooks)

Codex reads AGENTS.md and repository `.agents/skills`. Claude Code uses CLAUDE.md and project `.claude/skills`; adapters point to the shared skill bodies, so content has one source. No `allowed-tools` blanket grant or provider credentials are shipped.

The development environment reported Codex CLI 0.137.0 with hooks enabled, but native hook callbacks were not exercised. Current documentation may describe a newer runtime. Native Claude Code execution was not tested. Grokbot is not a verified product/runtime identifier in this release: use the master prompt and manual invocation only until its actual documentation, version and available tools are inspected. No Grokbot hook JSON is invented.

Browser/computer tooling is supplied by the user's agent host. Inspect the available tool's documentation and the destination's rules. A Playwright project-launched browser, an in-app browser and an existing personal session are distinct. This kit neither connects a session nor installs a browser. Do not attach via arbitrary debug ports or browser profile databases. A separate session requires user login directly.

Host-specific confirmation, permission and trust rules apply in addition to the workflow. No skill file, checked-in config, local approval record or reviewer can override those rules or the platform's terms. Unsupported native hooks leave manual application handling in place.

Portable support means the text workflow and local Python tools can be used with a suitable agent. It does not mean every host has the same browser, subagents, hooks, rendering or enforcement capabilities.
