# System models: who does what, where data goes

Use [Start here](START_HERE.md) for runnable onboarding. These diagrams describe
the current implementation and its boundaries. GitHub renders Mermaid; the
[standalone SVG overview](diagrams/system-overview.svg) also works without Mermaid.

## 1. Components and data ownership

```mermaid
flowchart TB
  U[Candidate: facts, scope and direct sign-in] --> A[User's tool-enabled AI agent]
  S[Ten shared skills and prompts] -. Instructions .-> A
  H[Optional reviewed host hooks] -. Host-specific checks .-> A
  A --> K[CLI or local stdio MCP]
  K --> C[Portable core: validate, prepare and coordinate]
  C <--> W[Private workspace: evidence, PDFs, manifests and receipts]
  C <--> DB[One canonical workflow.sqlite3]
  C --> E[Local Gmail adapter: ordered send stream]
  C --> B[Local Chromium adapter: isolated form lanes]
  C --> T[Experimental TinyFish Browser adapter]
  E --> G[Gmail API: one reviewed PDF and exact message]
  B --> J[Permitted employer HTTPS form]
  T --> P[TinyFish cloud session and employer form]
  R[Optional public research adapters] --> Q[Public job pages]
  A --> R
  R --> W
```

The clone contains reusable code and fictional examples. Candidate records stay
outside it. The public-research path excludes CVs, contacts and account cookies.
Email sends the reviewed package to Google/the destination; cloud browser use
has a separate provider disclosure boundary. Local browser execution does not
make the employer's form local. See [architecture](architecture.md).

## 2. Agent roles and model routing

```mermaid
flowchart LR
  C[Coordinator: one campaign owner] --> R[Research role: public sources]
  R --> T[Tailoring role: selected evidence and JD]
  T --> V[Review role: wording and final pages]
  V --> C
  C --> D[Deterministic route-task plan]
  D --> H[Supported host dispatch callback]
  H --> M[Actual available model and effort]
  C --> L[Transport lanes: exact issued actions]
  L --> C
  C --> DB[Canonical tracker]
```

These are responsibilities, not automatically spawned agents. One agent can do
them in sequence. The routing policy returns a plan; supported host dispatch
must apply and verify a real available model override. Tests, hashes, rendering
and tracker calculations use tools directly. Parallel research can return compact
source references; it never independently approves a package or writes the ledger.
See [skills and role table](AGENT_SETUP.md#3-load-the-skill-for-the-current-stage)
and [model routing](MODEL_ROUTING.md).

## 3. Login and one Gmail application

```mermaid
sequenceDiagram
  actor U as User
  participant A as User's agent
  participant P as Local email MCP
  participant G as Google OAuth / Gmail
  participant V as OS credential vault
  participant C as Core / private ledger
  A->>P: email_connect
  P->>G: Desktop OAuth with PKCE and loopback
  U->>G: Sign in directly and grant requested scopes
  G-->>P: Verified identity and tokens
  P->>V: Store token in supported OS vault
  Note over A,C: Prepare/review exact CV and establish finite authority separately
  A->>P: email_start(manifest_fingerprint)
  P->>C: Validate current package and scope
  A->>P: email_send_next(run_id)
  P->>G: Verify one prepared authenticated session
  P->>C: Commit immutable attempt before possible sending
  P->>G: One messages.send POST, exact MIME/PDF
  alt Valid API acknowledgement
    G-->>P: Message ID and thread ID
    P->>C: Save canonical send receipt and count
  else Timeout, lost response or process interruption
    P->>C: Preserve uncertain attempt without automatic replay
  end
  A->>P: campaign_tracker
  P-->>A: Recorded outcomes
```

Signing in proves account access. It does not approve employers, messages, terms
or CV bytes. OAuth tokens are not returned to the model. Gmail's acknowledgement
establishes sending, not delivery or absence of a later bounce. The adapter has
no inbox-reading scope. [Email setup and exact inputs](LOCAL_PLUGINS.md).

## 4. Concurrent browsing, ordered actions per job

```mermaid
flowchart TB
  M[Exact reviewed manifest and form mappings] --> C[Single coordinator]
  C --> L1[Lane 1: isolated session and job binding]
  C --> L2[Lane 2: isolated session and job binding]
  C --> LN[Lanes 3 to 10: independent sessions]
  L1 --> O[Inspect, fill, upload, review, submit, verify]
  L2 --> O
  LN --> O
  O --> R[Coordinator checks matching receipts]
  R --> DB[Save outcome in canonical ledger]
  DB --> X[Confirmed owned session: eligible cleanup]
  O --> H[New terms, unknown fields or challenge: handoff affected job]
  O --> U[Uncertain outcome: quarantine, no automatic replay]
```

The action order applies independently inside every lane; a job never skips
review to race another job. Default local browser concurrency is three, with a
maximum of ten. Prove one lane before increasing it. Different tabs alone do not
establish isolation. Gmail remains an ordered mutation stream.

Local Chromium supports mapped single-page, same-origin HTTPS forms. TinyFish
Browser is an experimental REST/CDP transport with separate cloud scope; live
provider compatibility remains unverified. TinyFish Fetch is public research,
not an application lane. BrowserAct currently supplies an offline planner, not
form execution. See [parallel execution](PARALLEL_APPLICATIONS.md).

## 5. Outcome and recovery model

```mermaid
stateDiagram-v2
  [*] --> Prepared
  Prepared --> Reviewed: Facts and every document page checked
  Reviewed --> Scoped: Exact finite authority validated
  Scoped --> AttemptRecorded: Durable claim before possible final action
  AttemptRecorded --> Confirmed: Matching observed receipt
  AttemptRecorded --> Uncertain: Timeout or ambiguous result
  AttemptRecorded --> Rejected: Explicit observed rejection
  Confirmed --> Cleanup: Owned window only, after saving receipt
  Uncertain --> ManualReconciliation: Read-only inspection
  Rejected --> ManualReconciliation: Preserve rejection evidence
```

These are explanatory labels, not literal database enums. There is deliberately
no automatic path from uncertain back to send. Recorded attempts survive process
restart; in-memory browser logins do not. Cleanup failure does not erase a saved
confirmation. Use [execution recovery](execution.md), [plugin QA](LOCAL_PLUGINS_QA.md)
and [throughput semantics](THROUGHPUT.md) for exact interfaces and evidence limits.

## Reading order

| Need | Guide |
|---|---|
| Clone/fork and first use | [Start here](START_HERE.md) |
| Skills, hooks and runtime support | [Agent setup](AGENT_SETUP.md) |
| OAuth and local browser plugins | [Local plugins](LOCAL_PLUGINS.md) |
| Source/privacy and core contracts | [Architecture](architecture.md) |
| Current verified versus experimental scope | [Compatibility](compatibility.md) |

Made by **DUYTRUYENTHONG**, MIT licensed, shared freely with the community.

Diagrams use [Mermaid's documented Markdown-based syntax](https://mermaid.js.org/config/usage.html).
The SVG is an original editable source asset with embedded accessibility text.
