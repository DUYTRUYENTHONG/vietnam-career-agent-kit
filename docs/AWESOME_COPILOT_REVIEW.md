# Awesome Copilot: browser and skill-management review

Reviewed 27 October 2026 at
[`d106008300bd4c8396e9c3c085c7c8e3ed976d48`](https://github.com/github/awesome-copilot/tree/d106008300bd4c8396e9c3c085c7c8e3ed976d48).
The source was cloned separately for static review. No upstream installer, hook,
SDK, extension or browser program was run. Exact Git-blob SHA-256 values for
35 selected files are in [the source record](../adapters/awesome-copilot.source.json).
This is a targeted adoption review, not an exhaustive security certification.

The pinned tree contains 462 skills, 222 agent definitions, 108 plugin manifests,
8 hook manifests and 51 cookbook Markdown files. These are repository inventory
counts, not installed or verified capabilities. Keep the kit's ten canonical
skills rather than importing the whole collection.

## What we can use

| Upstream resource | Useful part | Kit decision |
|---|---|---|
| `playwright-explore-website`, `playwright-generate-test`, `playwright-tester` | Inspect actual UI before selecting locators or writing tests | Adapt the observation-first pattern into the existing browser skill; keep host-specific tool names and models out |
| `webapp-testing` and helper | Semantic controls, bounded waits, screenshots and cleanup | Adapt guidance for fictional local QA; do not auto-install Playwright or run arbitrary helpers |
| `playwright-automation-fill-in-form` | Separate filling from final submission | Reference only; fixed demo values, path and destination are not candidate facts |
| `gem-browser-tester` | Observe/act/verify, task-bounded checks and concise outcomes | Adapt concepts only; preserve application receipts, ordered actions and required evidence rather than its generic retry/parallel rules |
| `context-map`, `what-context-needed`, context instructions | Identify only relevant files and unknowns | Use [progressive skill loading](SKILL_MANAGEMENT.md); no mandatory extra user file-transfer/review round for routine work |
| `ai-team-orchestration` | Stable owners, proportionate review and compact recovery | Keep existing owner/router; optional QA at a meaningful gate, no second orchestrator |
| `testing-automation`, `frontend-web-dev`, `context-engineering` plugins | Convenient Copilot bundles of related resources | Source candidates only; adapt selected items rather than installing the bundles in Codex |
| SDK multiple-session/error recipes | Separate conversation state, cleanup and finite waits | Reference concepts only; no SDK dependency or new model calls |

The adaptation is original guidance in
[`browser-application/references/observed-ui.md`](../.agents/skills/browser-application/references/observed-ui.md).
It supplements the current request/receipt protocol, not its validators or
authorization model. Compatibility is **Instruction-only**: native compliance,
real-employer performance and latency gains remain unverified.

## The real Chromium plugin is not a Codex bridge

[`chromium-control-canvas`](https://github.com/github/awesome-copilot/tree/d106008300bd4c8396e9c3c085c7c8e3ed976d48/extensions/chromium-control-canvas)
does implement a headful Chromium window with navigate/snapshot/click/type and
screenshot actions. It uses the Copilot canvas/UI-extension experiment and a
loopback control panel; the reviewed source does not supply a Codex MCP adapter.

Important implementation details:

- The plugin manifest is version 1.0.2; its extension package is 1.0.0. Dependencies
  declare `@github/copilot-sdk: latest` and `playwright: ^1.60.0`; the inspected lock
  resolves those packages to 1.0.1 and 1.60.0. Nothing was installed or independently
  runtime-tested, and no full transitive audit is claimed.
- Default sessions share one persistent profile. The implementation refuses a
  second live owned persistent window. It is not ten isolated job lanes.
- It offers optional attachment to an existing Chrome debugging endpoint. That is
  not adopted: the kit requires an explicitly supported, owned session boundary.
- Its sample host blocklist is not the kit's exact destination/action/consent/file
  authority. Automatic page recovery must not replay a pending application action.
- Its snapshot implementation stamps DOM references on visible controls. Those
  implementation-specific references cannot be reused as Codex host element IDs.

**Decision: defer the runtime port.** Keep the existing local-browser and
TinyFish Browser adapters. A future port needs a bounded specification, pinned
dependencies, isolated context ownership, current authority checks, durable
attempt-before-submit, uncertainty recovery, private receipt capture, native host
acceptance and measured fictional throughput. Source availability alone proves
none of these integration gates. No personal profiles, debugging port or canvas
experiment was enabled in this review.

## Defaults excluded from adoption

- Cookbook examples use `PermissionHandler.approve_all` and example model IDs.
  Do not import them into application execution. Independent conversations are
  not independent browser sessions; the kit retains exact scope and actual host
  model availability.
- `webapp-testing` says Playwright may be installed automatically. The kit does
  not install software from a skill invocation or silently add another provider.
- `tool-guardian` is a Bash/Copilot-payload pattern scanner, with bypass/allowlist
  settings. It is not a replacement for exact application authorization or a
  tested native Codex hook. No settings were copied or activated.
- `session-auto-commit` stages and pushes session changes. Do not adopt it for a
  project that must keep private candidate material outside public Git. Use the
  kit's explicit staged-diff, QA and descriptive-commit workflow.
- `context-matic` introduces an external documentation/MCP integration; it is not
  needed for the local core. Review its service and permissions separately if a
  concrete dependency gap appears.

## License and provenance

The root license is MIT, copyright GitHub, Inc. Selected resources were inspected
as data; no upstream code, skill text, images or demo personal information is
redistributed. Preserve notices if copying any content in a future change.
Package-level metadata can differ: `plugins/gem-team/plugin.json` declares
Apache-2.0 and an external source repository. Do not assume root MIT covers every
bundle or its dependencies. Its team bundle is not installed or copied here.

Reproduce the source review without installation:

```sh
git clone --depth 1 https://github.com/github/awesome-copilot.git ../awesome-copilot-review
git -C ../awesome-copilot-review rev-parse HEAD
# Compare with the pinned revision above; a newer HEAD is a new review candidate.
```

Hash the selected immutable blobs using `git show REV:path`, not a potentially
newline-converted checkout. Never run the reference's installation commands just
to inspect it. New revisions do not inherit this adoption decision.

## Fictional instruction review

These are bounded manual decision cases, not automated browser acceptance tests.
The revised guidance was checked in a separate review pass against each case:

| Case | Required decision | Review result |
|---|---|---|
| A dynamic mock form replaces an input after a dropdown changes | Observe again and derive a fresh target | Pass: observation-scoped references, no stale reuse |
| Ten tabs share one authenticated browser context | Serialize that session; do not claim ten independent lanes | Pass: ownership and isolation remain separate from tab count |
| A reviewed PDF is replaced by different bytes under the same name | Stop affected upload on changed hash | Pass: frozen-document and current-action checks retained |
| Submit times out after the durable attempt | Verify read-only; no automated second submit | Pass: uncertainty is preserved |
| Exact current approval and fields remain unchanged | Continue without another redundant approval request | Pass: existing authority reused; new terms remain separate |
| A completed owned tab and an unrelated user tab are open | Commit receipt, close only owned completed tab | Pass: cleanup does not close the user's tab |
| Copilot canvas/SDK is absent in the current host | Report unsupported; use an existing permitted bridge or handoff | Pass: no silent install or compatibility claim |
| An SDK example approves every permission | Exclude the handler; preserve the kit's scoped authority | Pass: example permissions are not user approval |

Repository gates and actual results are recorded in the change's PR. This review
does not claim 100 applications/hour, cheaper model usage, human impersonation,
anti-bot evasion or a new live browser connection.
