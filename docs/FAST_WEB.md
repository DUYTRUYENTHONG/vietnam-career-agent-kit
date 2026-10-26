# Optional Fast Web Pipeline — Firecrawl research slice

This experimental opt-in layer implements public search, selected scrape, async
batch start/status/pagination/errors/cancel, private evidence and normal JD
import. It does not operate candidate accounts or submit applications. Ordinary
commands stay offline. No SDK, package installation, model call, hook activation
or global setting is needed. Python 3.11+ stdlib; hosted API contract **v2**.

## Run with a reviewed finite public plan

Start with `examples/fictional/research-plan.json`; its `.test` destinations are
fictional and cannot be used with a cloud service. Replace role/location terms,
exact source hosts, independent permission evidence, expiry, account alias and
limits deliberately. Do not copy candidate identity, CVs, cookies, answers,
private URLs or filesystem paths into a plan. Source permission is reviewed
separately; an allow record is not proof of legal permission. Manual-only source
IDs and known manual-only hosts cannot be relabelled as employer pages.

```sh
python scripts/kit.py provider-doctor
python scripts/kit.py discover --plan ../private/public-plan.json --dry-run
python scripts/kit.py --data-dir ../private init
python scripts/kit.py --data-dir ../private discover --plan ../private/public-plan.json --live --approve-plan REVIEWED_FINGERPRINT
python scripts/kit.py --data-dir ../private research-status --fingerprint PLAN_FINGERPRINT
python scripts/kit.py --data-dir ../private research-report --fingerprint PLAN_FINGERPRINT
python scripts/kit.py --data-dir ../private cancel-research --fingerprint PLAN_FINGERPRINT
python scripts/kit.py --data-dir ../private import-research-jd --evidence-id EVIDENCE_ID --file ../private/normalized-with-references.json
```

Set `FIRECRAWL_API_KEY` privately in the launching environment. Doctor only checks
presence, not validity, subscription, balance or actual account capabilities.
After reviewing the account limit, `FIRECRAWL_MAX_CONCURRENCY` may be set to 1–4;
default 1. Plans with more distinct extraction domains than the lower account/
plan bound must be split. Each batch contains only one domain and has provider
`maxConcurrency: 1`, even when its URL list is long. No full-account default is
used. Active domain/account reservations also span plans in the same workspace;
other workspaces/clients are outside this local bound. The CLI acknowledges a public-plan fingerprint; this local record cannot
authenticate a human or replace host/provider spending approval.

An empty `urls` list generates bounded English/Vietnamese search queries from
the supplied roles/locations and restricts results to reviewed source domains.
Search snippets remain leads. Select eligible URLs in a subsequent reviewed
plan; they are deduplicated before extraction. `--individual` selects individual
scrape for comparison. Default selected-URL mode starts per-domain batches and
returns IDs immediately; call status to collect available results. No submitted
request is counted as a completed page or job.

## Evidence and import

Main-content Markdown and necessary metadata only; no PDF parsing, HTML,
screenshots, remote actions, profiles or uploads. Public URL/query + provider
account + locale + options + parser version + unauthenticated scope form private
cache keys. Default search TTL 1h, page TTL 6h; plans may lower them. Provider
`maxAge` is explicit. Receipt time, local cache expiry, observed source date and
observed provider cache timestamp remain distinct. Missing dates remain null.
Evidence reused from cache keeps its original capture time and task provenance.

Captured pages have unknown job fields/liveness until normalized. Returned URLs
must match selected source/destination bindings. Empty/error/changed output is
quarantined. Immutable evidence JSON is stored privately; the host receives IDs
and relative artifact references, not a repeated corpus. All raw provider content
is untrusted; no returned instructions/code execute.

`import-research-jd` accepts `{ "job": <existing job contract>, "references":
<field-to-exact-source-quote map> }`. It binds the complete captured Markdown,
destination and current bytes; requires references for every non-null claim,
non-unverified liveness and every requirement; compares identity, city and
requirement wording. References and normalized fingerprints are retained in
SQLite. Quote presence **does not prove entailment**, a date interpretation or
eligibility. The host must review those meanings and preserve unknown salary,
experience, deadline and vacancy status. Existing fingerprint checks detect
changed normalized JDs before dependent preparation can be used. Selected
application destinations still need a fresh host inspection; research cache
never caches approval, artifact validation, form state or submission authority.

## Recovery and bounds

Before each dispatch: persist intent plus request/credit reservation in one
transaction, then leave the transaction and call the provider. Persist the remote
ID before further work. Repeating the same plan never launches the same task
again; another plan also cannot replace an unresolved identical in-flight task.
An intent left by a crash or a possibly accepted start without an ID remains
manual reconciliation. No invented idempotency header or paid automatic retry.

Status stores each available page before following a validated continuation.
Only the exact Firecrawl host, batch ID and numeric `skip`/`limit` parameters
are eligible. At most eight continuation reads per status invocation; the next
cursor survives interruption. Scraping/progress cursors defer to another explicit
status call rather than a busy poll. Partial failures retain completed evidence.
404 becomes uncertain remote-expired-or-missing, without a replacement batch or
release of its unresolved domain reservation. Repeated
pages cannot rewrite their original evidence bytes.

Request count and runtime are finite; new work stops at either limit. Credit
reservations are conservative **local estimates**, not a provider-enforced dollar
or credit cap. Search reserves two units per request and pages one each; actual
pricing/account usage may differ. Unknown usage is not zero: reservations are
not released based on missing usage. Set a provider-side account spending cap
before paid use; automatic top-ups are never enabled here. Actual cost/tokens
are null unless observed; latest reported batch credits are kept separately.

No automatic retries. Status/cancel failures persist Retry-After (or bounded
backoff) and open a circuit after three consecutive failures. Cancellation is
intent first, then one DELETE and GET reconciliation; an uncertain DELETE is
never automatically repeated. Local timeout or a pending request is not remote
termination. Read-only recovery/cancel can continue for existing IDs after plan
runtime/expiry, within the remaining request budget; it cannot create new work.

Diagnostics contain opaque IDs, fixed stage labels and numeric timing/counters,
not CV text, answers, keys, session URLs or personal paths. Monotonic durations
and UTC audit times are separate. Observable local stages are measured; host
reasoning, provider internal queueing, conversion, browser steps and human wait
stay null when not observed. A fixed 15s socket timeout is not a hard total-run
deadline for arbitrary network behaviour. Research uses no persistent browser.

## Compatibility and remaining increments

Deterministic fake-transport tests cover contracts, private storage and CLI only.
Live provider/account verification has not run; no credentials were configured.
No cloud service can reach the local `.test` corpus. A live smoke needs a
separately approved controlled public HTTPS fixture with fictional data and a
finite paid budget. No tunnel or real candidate upload is an acceptable shortcut.

TinyFish interactive research, SSE/task controls and a direct Browser bridge are
**Unsupported in this increment**. There is no second search stack. Direct cloud
applications require a later versioned disclosure scope covering provider account,
session/profile, destinations, data, recording and expiry, plus exact upload and
fresh action evidence. Current host-bound approvals never transfer to a cloud
provider. `perform(request) -> receipt` and the one-active-run/one-pending-action
executor are unchanged. Unsupported consent/challenges stay manual.

## Reproduce measurements

```sh
python scripts/benchmark_pipeline.py --jobs 100 --samples 7
python scripts/benchmark_web.py --samples 7
```

The separate web benchmark alternates individual and batch ordering, uses 12
identical EN/VI fictional pages, two duplicate inputs, closed/unknown records,
exact digest checks and identical source-referenced normalization/import. It
measures capture, first imported JD, full completion and warm cache separately;
reports median/range/sample count, work counts and fixture accuracy. The supplied
normalization is not an autonomous-extractor accuracy result. The interactive
fixture explicitly reports unsupported. Live host/TinyFish/browser timing,
provider queueing, billing and application throughput remain unmeasured. See
PERFORMANCE.md for the actual run, without treating mock capacity as applications.


## Parallel execution update

Schema 6 adds opt-in independent application lanes and public TinyFish Fetch batches. See [PARALLEL_APPLICATIONS.md](PARALLEL_APPLICATIONS.md) for commands, host requirements and measured-versus-unverified limits. Earlier sequential-only/TinyFish-unsupported descriptions apply to previous increments. [TinyFish Browser](TINYFISH_BROWSER.md) now has an opt-in experimental guest-form adapter; Agent-goal submissions remain unsupported.
