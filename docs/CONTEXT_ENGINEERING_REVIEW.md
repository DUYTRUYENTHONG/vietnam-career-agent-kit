# Context Engineering collection: targeted review

Cloned separately on 27 October 2026 from
[muratcankoylan/Agent-Skills-for-Context-Engineering](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering)
at immutable revision
[`9ff0c99108b36d3b886defd825d8ac1f47dba374`](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/tree/9ff0c99108b36d3b886defd825d8ac1f47dba374).
This is a static, targeted review. No upstream scripts, installation commands,
research loops or plugins were executed. No upstream content is copied into the
kit. Selected file hashes and review scope are in
[the source record](../adapters/context-engineering.source.json).

The pinned tree contains 18 skills under `skills/`, plus a collection entrypoint.
The marketplace and plugin metadata advertise version 2.6.0. These describe a
collection, not an installed Codex integration or live browser transport.

## Decisions for this kit

| Source area | Decision | Existing destination |
|---|---|---|
| Filesystem context | Adapt selective reads and references to durable outputs; keep private data outside public Git | [Skill-management guide](SKILL_MANAGEMENT.md) and existing private workspace |
| Context compression | Adapt an explicit continuation note with exact artifacts, decisions, uncertainty and next action | Guide's checkpoint procedure; canonical ledger remains authoritative |
| Context optimization | Use scoped retrieval and compact tool results; measure total accepted-task work | Existing router and throughput reporting; no fixed compression or savings target adopted |
| Multi-agent patterns | Reuse stable owners; add workers only for independent work when permitted | Existing agent/lane architecture; no new orchestration framework |
| Evaluation | Prefer deterministic checks and outcome evidence before subjective grading | Existing repository gates and receipt verification |
| Harness engineering | Keep evaluation rules separate from proposed changes and preserve durable attempts | Existing execution/approval contracts; no autonomous researcher loop installed |
| Self-managed context | Defer: rewriting a note does not rewrite this host's live messages | No live-context editing feature claimed |
| Latent briefing | Defer: requires compatible model KV-state access unavailable in this integration | Structured text handoffs remain the supported approach |
| Self-improvement loops | Reference only; no recursive self-edit/promotion process | Ordinary focused changes, QA and reviewed publication |

This improves instructions and documentation only. It adds no memory service,
model SDK, tool registry, browser session or automatic dispatcher. All adopted
guidance is **Instruction-only**. It does not remove host or candidate authority
checks, turn unknown outcomes into confirmations, or widen an application's scope.

## Dependencies, examples and licensing

The root license is MIT, copyright 2025 Context Engineering Agent Skills
Contributors. Preserve applicable notices if copying material later. Do not infer
every linked implementation has the same license: the self-managed-context
`references/harness-protocol.md` attributes its source implementation to CC BY-NC
4.0 material. That reference and implementation are not copied or ported here;
this observation is not a legal conclusion about derivative licensing.

`requirements-dev.txt` declares unpinned `pyyaml` and `skills-ref`, plus
`jsonschema==4.26.0` and `referencing==0.37.0`. These were inspected as metadata,
not installed, and no transitive dependency audit is claimed. The marketplace
uses `strict: false`; that field is not a permission grant for this kit.

Selected scripts are illustrative, not runtime acceptance evidence:

- The compaction helper documents heuristic token estimates, demonstration
  summaries and illustrative cache metrics. Those are not observed host usage.
- The compression evaluator labels its production judge a stub and includes an
  example API/model call in documentation. No judge or model dependency is added.
- Filesystem examples write scratch state and include cleanup helpers. The kit
  keeps its existing workspace ownership and retention rules; no generic cleanup
  or second application ledger is adopted.

Research percentages, cache targets and token multipliers are source-specific
claims, not measured improvements for this kit. This review does not reproduce
those benchmarks, certify the entire repository, or promise faster submissions.

## Bounded acceptance review

These are manual instruction checks, not live-agent or browser benchmarks:

| Fictional case | Result of reviewing the new guide |
|---|---|
| A long tool result contains one relevant error | Keep a retrievable source path and error; load the relevant section |
| A note says submitted but the ledger says uncertain | Reconcile authoritative evidence; never replay final submission from the note |
| A PDF changes after a checkpoint | Recheck bytes and scope; the old note cannot authorize the new file |
| A source page embeds instructions in saved output | Retain source attribution; treat content as data |
| A worker needs one job's status | Pass that job's IDs and evidence, not full history or another login's secrets |
| The host offers no KV or conversation-edit API | Use an ordinary text handoff; do not claim latent or live-context control |

All six decisions are covered by the guide. Automated repository checks are
reported separately in the PR. No native plugin discovery, model-cost saving,
ten-browser execution or real-employer performance was tested in this review.
