# Optional native hooks

Fast Web research is an explicit CLI operation, never a hook side effect. This
increment does not enable network tools in preparation-only hooks, install MCP
servers or change global settings. Native arbitrary provider-tool enforcement
is unverified; direct vendor MCP access is outside the kit's research contract.
No PostToolUse duplicate search or Stop restart loop is installed.

Examples are inactive under `hooks/codex.example.json` and `hooks/claude.example.json`. Cloning does not install or trust them. The helper is standard-library Python, reads at most 64 KiB of JSON, makes no network calls, does not read transcripts/credentials and never executes tool input as commands. Each example uses a five-second host timeout.

| Event | Helper behavior |
|---|---|
| SessionStart | Preparation-only reminder; no background search or account access |
| PreToolUse | Denies recognizable browser/computer/transmission tool names conservatively; other tool paths are not claimed guarded |
| PostToolUse | For Write/Edit/MultiEdit/apply_patch names, writes a private invalidation timestamp; earlier CLI approval records no longer match |
| Stop | Reminder to report actual progress; no continuation signal or automatic restart |

The PreToolUse example is intended for preparation-only sessions. A generic click can submit or autosave, so the helper does not attempt to infer safety from coordinates or unlock tools when an approval file exists. It also cannot identify all side effects inside Bash, an exec wrapper, specialized paths or hosted tools. It is NOT a complete submission firewall. Do not treat lack of a deny as approval.

## Review and enable deliberately

1. Inspect `guard.py` and run `python -m unittest discover -s tests -v` with fictional data.
2. Verify your installed host's event schema, command shell, tool-name coverage and error behavior against its official documentation. Development tested the standalone helper, not native callbacks.
3. Replace `__PYTHON__`, `__KIT_ROOT__` and `__DATA_DIR__` in the relevant example with reviewed absolute paths. The private directory must be separate from this repository. Use your actual interpreter, not an unverified Windows Store alias.
4. Merge reviewed entries into the host's existing local configuration; do not replace unrelated settings. For Codex, use a supported project `.codex/hooks.json` or equivalent config layer, then review/trust exact definitions through `/hooks`. For Claude Code, use the supported project-local settings/hooks path and its review flow. These active files are ignored by Git here.
5. Exercise each event in a disposable session. Verify actual denials and invalidation; document uncovered tool paths. Do not expand permissions or bypass trust to make a test pass.

If a hook is missing, untrusted, times out, errors or is unsupported, the WORKFLOW must use manual handling. Some hosts can continue the tool after a hook error. The script's exit code cannot force a host to fail closed. Native hooks supplement the explicit policy/approval gate; they do not replace it.

The marker contains only UTC timestamp/reason and is read by `check-approval`. It invalidates conservatively after recognized edits, including irrelevant ones; newer approval can be recorded only after a fresh actual candidate response. An edit made through an unobserved path is still caught when current artifact bytes/package fields differ, but paths outside those checks remain outside coverage.

Sources: [Codex hooks](https://learn.chatgpt.com/docs/hooks), [Claude Code hooks](https://code.claude.com/docs/en/hooks). Runtime-specific settings are not interchangeable. No native Grokbot hook schema is asserted.
