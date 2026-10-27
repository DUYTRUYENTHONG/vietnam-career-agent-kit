# Measured performance and evidence-backed career MCP

Requested 27 October 2026. Reuse the existing private workspace, canonical
application ledger, ten skills and optional MCP SDK. No extra model API, global
hook, public listener, automatic training job or new application authority.

## Acceptance contract

### 1. Per-model performance tracker

- Explicit versioned observations bind event/task/workload IDs, phase, exact
  reported model/effort, terminal status, acceptance, duration, token counters
  and optional observed monetary charge to a private source artifact/hash.
- Missing duration/tokens/cost remain null. A supplied export is caller-reported
  evidence, not independently authenticated provider telemetry. The current host
  need not expose usage. Do not infer tokens, prices, model identity or savings.
- Keep cached input and reasoning counts as subsets, never add them twice to
  input/output totals. Reject cumulative counters as individual-call usage.
- Persist opt-in immutable observations in the selected workflow database with
  an independently versioned feature table; preserve application schema/state.
  Reimporting an identical event is idempotent; changing its ID-bound bytes fails.
- Report by model, phase and workload with counts, accepted/failed observations,
  measured p50/p95, known token sums and missing-data coverage. Observed charges
  stay separated by currency. Parallel-call durations are not campaign wall time.
- CLI/MCP readers and JSON/Markdown/CSV exports use the same records. No raw CV,
  prompt, access token or private source contents enter public benchmark reports.

### 2. Evidence-backed retrieval and professional email MCP

- Add an opt-in local stdio career server beside existing email/browser servers;
  no login, permission creation, submission or training endpoint in this server.
- Retrieve only the selected candidate's current confirmed source-backed facts.
  Reject stale/tampered evidence and unresolved profiles. Atomic fact chunks keep
  quotes, source IDs, locators and profile fingerprint. A JD is requirements data,
  never new candidate evidence or instructions.
- First retrieval slice is explicitly experimental lexical BM25 using local
  SQLite FTS5, with bounded top-k/context and Unicode queries. It is not claimed
  as production hybrid/vector retrieval. Missing FTS5 yields a useful handoff.
- Evaluate precision/recall@k and reciprocal rank on held-out fictional queries;
  compare a simple lexical baseline and disclose empty/adversarial cases. A later
  optional dense adapter requires embedding comparison and separate acceptance.
- Return a cited context packet and professional English/Vietnamese email prompt
  that reuse the existing source-bound tailoring/review path and writing skill.
  Preparation is not sending, factual approval or proof of qualifications.

### 3. Reviewed training-data and evaluation export

- The user selected RAG plus reviewed dataset/evaluation export first, without a
  second model API. No model weights are trained or claimed to improve yet.
- Only explicitly reviewed, source-bound examples enter an export; generated
  drafts/positive application outcomes never automatically become true CV facts.
- Bind reviewer decision to exact content and current evidence. Reject unreviewed,
  rejected, stale, mismatched or cross-candidate examples and changed approvals.
- Keep export in the private workspace, with provenance and reproducible hashes.
  Separate training and held-out evaluation by job/group; report insufficient
  diversity honestly. Do not claim cross-candidate generalization from one CV.
- Feedback improves examples/retrieval only after review and evaluation. Actual
  hosted/local fine-tuning requires a separately configured model/compute path.

## Implementation order and release gates

1. Observation contract, persistence, aggregation and regression tests.
2. CLI reports and optional career-MCP integration using the same functions.
3. Confirmed-evidence retrieval, professional email context and retrieval eval.
4. Exact reviewed-example export, leakage/staleness tests and private examples.
5. Guides, progressive references in existing skills, changelog, source/version
   evidence, full fictional checks and the six required protected-main CI jobs.

Each coherent increment is reviewed and committed. No bypass of the newly
protected `main`. A passing local core test is not native host, live account,
production RAG, model-training or employer acceptance.

## Campaign targets stay private

The community default stays 100; a personal target such as 1,000 uses an explicit
private override. Historical adjacent/stretch roles are not relabeled as best
fit. Target count does not expand a standing grant's recipients, cap, expiry,
consents or host permissions. No manufactured authority or uncertain-submit replay.

## Primary implementation references

- [Official MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk):
  reuse the project's hash-locked MCP 1.30.0 optional dependency, not latest main.
- [SQLite FTS5](https://www.sqlite.org/fts5.html): tokenization and BM25 retrieval;
  lexical ranking alone does not establish semantic answer correctness.
- Existing source adoption, writing rules and licenses remain in
  [skill management](SKILL_MANAGEMENT.md), [writing guidance](../.agents/skills/application-tailoring/references/evidence-writing.md)
  and [local plugin QA](LOCAL_PLUGINS_QA.md).
