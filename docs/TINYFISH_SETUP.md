# TinyFish setup for public job research

This kit's experimental TinyFish integration reads **1-10 selected public URLs**
per Fetch batch. It uses Python's standard library. You do not need the TinyFish
SDK, CLI, Chrome extension, MCP server or a second model API for this adapter.
TinyFish Agent/cloud-browser application submission is not integrated.

## 1. Create a key and load it privately

Use your own [TinyFish API key dashboard](https://agent.tinyfish.ai/api-keys).
Review its current account limits and pricing before live use. Set any desired
provider-side spending cap; the kit's reservations are local estimates.

In the terminal that will launch the kit, use one of these hidden-input examples.
Do not paste a key into chat, a command argument, a plan or Git.

**PowerShell:**

```powershell
$tinyfishSecret = Read-Host 'TinyFish API key' -AsSecureString
$env:TINYFISH_API_KEY = [System.Net.NetworkCredential]::new('', $tinyfishSecret).Password
Remove-Variable tinyfishSecret
python scripts/kit.py provider-doctor
```

**Bash:**

```bash
read -r -s -p 'TinyFish API key: ' TINYFISH_API_KEY
printf '\n'
export TINYFISH_API_KEY
python scripts/kit.py provider-doctor
```

The diagnostic checks presence locally and never prints or validates the key.
The adapter reads the environment; it **does not auto-load `.env` files**. An
already-running agent may not inherit a newly set variable: launch it from this
environment or use its documented secret mechanism without disclosing the key.

## 2. Prove the offline preview first

From the clone, even without a key:

```sh
python scripts/kit.py tinyfish-fetch --plan examples/fictional/research-plan.json
```

Expected: `outcome: ok`, `network_calls: 0`, `planned_requests: 1`,
`application_authority: false` and an exact plan fingerprint. This fictional
`.test` plan is only a contract example; it cannot be used with the live service.

## 3. Prepare your finite public plan

Copy that JSON into your selected external private workspace and edit it there.
Keep its versioned structure; review these fields:

| Field | Your input |
|---|---|
| `plan_id`, `provider_account` | Local descriptive ID and non-secret account alias |
| `expires_utc` | Finite future UTC expiry, chosen for this pass |
| `roles`, `locations` | Job-search criteria without candidate identity |
| `sources` | Exact reviewed public hosts, source IDs, permission evidence and expiry |
| `urls` | 1-10 distinct public HTTPS pages on those hosts |
| `limits` | Finite requests/pages/runtime and reservation estimate; at least one request and enough pages/reservation for the batch |
| `freshness` | ResearchPlan freshness values; see the limitation below |

Source permission is separate from provider access. A manually written allow
record cannot authorize a prohibited source. Do not include CVs, contacts,
answers, account cookies, private URLs or filesystem paths. The adapter does not
log in, navigate application forms or carry out natural-language Agent goals.

```sh
python scripts/kit.py tinyfish-fetch --plan ../my-career-private/public-plan.json
```

Inspect the selected URLs, limits and returned fingerprint before live dispatch.
Any edit changes the fingerprint. Do not use the example plan's old fingerprint.

## 4. Dispatch once, inspect evidence, then normalize

Initialize a new selected workspace first; for an existing one, back it up and
review the explicit schema-6 migration before `init`. Replace the placeholders
with actual values from your reviewed plan and outputs:

```sh
python scripts/kit.py --data-dir ../my-career-private tinyfish-fetch --plan ../my-career-private/public-plan.json --live --approve-plan REVIEWED_FINGERPRINT
python scripts/kit.py --data-dir ../my-career-private research-report --fingerprint REVIEWED_FINGERPRINT
python scripts/kit.py --data-dir ../my-career-private research-status --fingerprint REVIEWED_FINGERPRINT
```

The first command stores intent before one Fetch POST. Completed pages become
private evidence IDs; they are **not** jobs or applications yet. Review the full
JD, liveness and eligibility, then use source-referenced normalization and
`import-research-jd` as described in [FAST_WEB.md](FAST_WEB.md).

Partial/uncertain responses retain valid evidence. Reconcile the existing task
instead of posting again or changing the plan to evade it. Status/report read
saved TinyFish state; this adapter has no remote polling or cancellation API.
A local stop does not prove the provider stopped. Provider errors and manual
handoffs are not completed pages or submitted applications.

## Current adapter boundaries

- `TINYFISH_API_KEY` authenticates the fixed Fetch endpoint with `X-API-Key`.
- The request sends `urls` and `format: markdown`. It does not forward the
  ResearchPlan's provider freshness field as Fetch `ttl`; source freshness must
  be checked before use. It does not request Search, Agent, Browser or Vault.
- Changed final URLs, empty output or malformed pages require review. Research
  success is not proof of an open vacancy or permission to submit.
- One provider batch may process URLs concurrently; it does not allocate ten
  authenticated application sessions. Use [isolated host lanes](PARALLEL_APPLICATIONS.md)
  for the separate request/receipt execution engine.
- Local fake-transport tests pass independently of credentials. Live account,
  billing and throughput verification remain separate; no 100x result is claimed.

Clear the key from this shell when finished: PowerShell
`Remove-Item Env:TINYFISH_API_KEY`, or Bash `unset TINYFISH_API_KEY`.

Official references checked for this guide: [authentication](https://docs.tinyfish.ai/authentication),
[Fetch contract](https://docs.tinyfish.ai/fetch-api/reference), and
[TinyFish cookbook](https://github.com/tinyfish-io/tinyfish-cookbook). The cookbook
is upstream learning material, not an installer or application authorization.
