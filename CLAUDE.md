# Claude Code maintainer entrypoint

Read AGENTS.md for product development. Do not initiate candidate intake or a campaign during coding work. Only an explicit job-seeker request activates prompts/MASTER_PROMPT.md and docs/job-seeker-policy.md. Shared skill bodies live in .agents/skills; generated .claude/skills adapters point to them. Run python scripts/generate_adapters.py --check to check synchronization. No global settings, tool allowlists, browser access or hook trust is granted.

Use the installed Claude Code documentation/version to verify hook and tool schemas. Never reinterpret Codex tools or settings as Claude capabilities. Without supported browser control, prepare a manual application pack.

For every skill or feature update, follow docs/change-workflow.md and AGENTS.md: keep documentation, checks, changelog and a descriptive GitHub commit together. Report the commit/PR and actual CI status.
