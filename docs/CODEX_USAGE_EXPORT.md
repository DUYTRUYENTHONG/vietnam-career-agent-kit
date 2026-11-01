# Prepare Codex CLI usage observations

Status: **Experimental offline export normalization**. No native desktop session
reader, model invocation, background watcher, database migration or application
action. The existing [performance tracker](PERFORMANCE_TRACKER.md) remains the
separate opt-in storage/reporting step.

## Questions this answers

- What input, cached-input, output and reasoning token counts did a selected
  fresh-thread CLI export actually report for each completed/failed agent turn?
- Which measurements are missing, rather than an observed zero?
- Can the observations be prepared without copying prompts, reasoning, command
  text, tool outputs or error messages into the metrics evidence?
- Can the existing append-only importer reject replayed or changed identities?

## Supported source and bounds

[Official OpenAI documentation](https://learn.chatgpt.com/docs/non-interactive-mode#make-output-machine-readable)
describes `codex exec --json`, its JSONL event stream and `turn.completed.usage`.
This normalizer consumes an **already captured** export. It does not run Codex,
read desktop rollouts, search user directories or require an API key.

Select one complete fresh-thread export: one leading `thread.started`, paired
`turn.started` and `turn.completed`/`turn.failed` events, with no overlapping or
unfinished turn. Supported nonterminal events are `item.started`, `item.updated`,
`item.completed` and `error`; their content is omitted. An error message is not
used to invent token counts or override a reported terminal status. Malformed
JSON, duplicate keys, unknown event/usage shapes and cumulative counters stop
preparation before any output directory is created.

Limits: 10 MB UTF-8 input, 1 MB per line, 20,000 lines and 1,000 terminal turns.
These are local defensive limits, not Codex service limits. A missing usage
object/field becomes `null`; an explicit zero remains zero. Cached input and
reasoning are subsets of input/output, never added to totals again.

## Prepare, inspect, then record

Use an explicit **new private directory**, inside your existing selected
workspace if you intend to use `performance-record` afterward:

```sh
python scripts/normalize_codex_usage.py --input ../private/exports/codex-run.jsonl --output-dir ../private/reports/performance/codex-run --task-id tailor-run --workload-id fictional-jd-group --phase generation --observed-utc 2026-01-02T03:04:05Z
```

`--observed-utc` is the caller's observation/capture time, not an inferred
per-turn timestamp. `--model-id` and `--effort` are optional **caller-reported**
metadata. Supply them only when your host evidence establishes that exact model
for all selected turns; omit them for mixed/unknown routing. Effort requires a
known model. No alias resolution or provider authentication is performed.

The result lists one `.observation.json` and sanitized `.source.json` per turn,
plus a final `Manifest.json`. The proof retains raw-export SHA256 and hashed
thread identity, ordinal, terminal type, allowlisted usage and the provenance of
caller metadata. It does not retain the raw export or raw thread ID. Keep the
original export privately if an audit needs it. A hash does not authenticate the
export's producer. Duration and charge are always unknown: neither timestamps,
filesystem modification time nor API price tables supply those measurements.

Inspect the completed manifest and sidecars, then explicitly record selected
observations using the existing command:

```sh
python scripts/kit.py --data-dir ../private performance-record --file ../private/reports/performance/codex-run/turn-0001.observation.json
python scripts/kit.py --data-dir ../private performance-report
```

Normalization never opens/creates a workflow database, confirms a candidate fact
or records an application. In particular, it is usable without initializing a
second tracker in a legacy workspace. The normal performance importer still
requires its supported portable workspace and does not migrate a legacy ledger.
Every prepared observation has `accepted: false`; terminal completion is not
quality acceptance, a verified CV or a successful job application.

## Replays, failures and compatibility

Event identity binds the hashed thread plus turn ordinal, not file whitespace,
an output-directory name or a newly invented run ID. Re-recording the same
observation is idempotent. Changed bytes/provenance under an existing identity
are blocked by the existing importer, rather than double-counted. Do not rekey
an event to evade that check.

Concatenated exports and interleaved threads are unsupported. Resumed exports
may reuse a thread with restarted ordinal numbering: do **not** use this
normalizer for `codex exec resume` or reconstruct counter deltas across exports.
No native-host compatibility is implied by recognizing a copied JSON shape.
The normalizer refuses any existing output directory. A write failure can leave
an incomplete new directory; without its final manifest, inspect it rather than
recording/retrying it automatically. Never overwrite earlier evidence.

## QA acceptance

Fictional regressions exercise real normalization, CLI execution and subsequent
performance import/reporting, including replay identity, missing versus zero,
failed turns, subset bounds, malformed/incomplete streams, duplicate keys, input
limits, privacy omission and existing-output preservation. They call no models
or network services. Live CLI export/version acceptance, desktop telemetry,
execution-time capture and per-provider billing remain separate gates.

```sh
python -m unittest tests.test_codex_usage tests.test_performance -v
python -m unittest discover -s tests -v
python scripts/check_repository.py
```
