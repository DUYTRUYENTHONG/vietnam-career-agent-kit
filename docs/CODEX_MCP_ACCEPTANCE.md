# Codex native MCP inventory acceptance

On 6 November 2026, Windows Codex CLI **0.137.0** discovered both launcher modes
through the native `codex app-server` interface: one source-memory tool and all
20 portable-workspace tools. This closes inventory-discovery checks, not desktop
installation or complete host execution. The server used the existing dedicated
Python environment with MCP SDK **1.30.0**. No dependencies or global host
settings were changed.

## Observed check

1. Create an external fictional workspace containing one approved, hash-bound
   fact, its text source and an `applications.sqlite3` sentinel. Do not use a
   candidate workspace for this maintainer check.
2. Start `codex app-server --listen stdio://` with a process-only `-c` override
   registering `scripts/career_mcp.py --data-dir <fictional-directory>
   --source-memory` under `career_test`. Use the dedicated environment's absolute
   Python executable and correctly quoted absolute paths.
3. Send `initialize` with a client name/version, then `initialized`, followed by
   `mcpServerStatus/list` with `detail: "toolsAndAuthOnly"` and `limit: 100`.
4. Inspect only the `career_test` result. It advertised exactly
   `career_source_context`. Hash every fictional input again after shutdown.

The native inventory request succeeded, the process exited with code 0, and all
fictional inputs remained byte-identical. End-to-end process time was
**15,883.25 ms**, including startup, inventory and shutdown. This is not inference
latency or retrieval-call latency. No model turn, model API call, application,
training operation or private candidate disclosure occurred.

A second process used the repository's fictional demo workspace and omitted
`--source-memory`. Its selected entry advertised exactly 20 tools, including
`career_context`, `career_writing_brief`, `campaign_tracker` and
`performance_report`. End-to-end process time was **8,776.94 ms**. It exited 0,
left all fictional workspace files unchanged and made no model calls. These
two observations are different workloads, not a performance comparison.

The process also reported 11 other pre-existing configured servers. Therefore
this check does **not** establish an isolated host configuration; the override
did not remove existing registrations. Never publish their inventory or infer
their availability from this check. The acceptance result concerns only the
fictional `career_test` entry.

## Remaining gates

- Native tool invocation and matching returned evidence for both modes.
- Codex desktop registration/reconnection and Claude Code acceptance.
- macOS acceptance, actual model generation and semantic tailoring quality.

The installed CLI's generated JSON schema was used for request compatibility.
In this version, `ListMcpServerStatusParams` has no server-name filter; inspect
the selected returned entry without publishing unrelated server information.
Current documentation can describe newer fields, so generate schemas with the
actual installed version before building a client.

Raw local QA artifacts remain outside Git. Their existence does not authorize
connecting a real candidate workspace. Continue with the
[MCP setup guide](MCP_SERVER.md) and its explicit privacy boundaries.

Official protocol reference:
[Codex app-server](https://learn.chatgpt.com/docs/app-server).
