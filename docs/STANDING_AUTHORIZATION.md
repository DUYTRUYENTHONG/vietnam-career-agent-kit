# Standing campaign authorization

Delegate routine applications once within a named scope. After actual approval,
the agent can tailor and review later CVs and authorize new exact manifests
without another local approval proof for every batch. This is opt-in; no global
`always_approve` switch or approval-file generator is installed.

The scope binds one confirmed candidate/profile and coordinator, actual host
bridge, named employers, HTTPS directory prefixes, exact ordinary answer bank,
exact consent choices, allowed actions, a shared 1–100 application cap, expiry
within 30 days and per-run runtime up to 60 minutes. Changed profile, recipient,
answer, consent text or broader destination requires a fresh scoped decision.

## Configure once

Run compatible `init` to add schema 4. Create a JSON plan inside the private
workspace using [the input schema](../schemas/authorization.schema.json):

```json
{
  "schema_version": "1.0",
  "authorization_id": "fictional-campaign",
  "expires_utc": "2026-10-23T00:00:00+00:00",
  "submission_limit": 10,
  "bridge_id": "selected-supported-host-session",
  "runtime_minutes": 30,
  "targets": [{
    "employer": "Fictional Company",
    "destination_prefix": "https://careers.example.test/apply/",
    "operations": ["fill", "upload", "submit"],
    "answers": {
      "salary": {"value": "Negotiable", "source": "candidate_confirmed", "fact_ids": [], "kind": "ordinary"}
    },
    "consents": []
  }]
}
```

Replace the fictional recipient, date and answers with the actually reviewed
scope. Directory paths end in `/`; employer, scheme, host, port and query must
match. A query on the prefix is an exact query constraint. Use the named
employer's tenant path on an ATS. Wildcards, ambiguous separators and traversal
are rejected. A job-board origin does not grant every employer's permission.

```sh
python scripts/kit.py --data-dir ../career-private init
python scripts/kit.py --data-dir ../career-private create-authorization --plan ../career-private/standing-plan.json
# Show the exported scope and receive actual approval before recording
# APPROVE AUTHORIZATION FINGERPRINT in a private proof file.
python scripts/kit.py --data-dir ../career-private approve-authorization --fingerprint FINGERPRINT --confirmation ../career-private/standing-proof.txt
```

A broad chat phrase is intent to configure this workflow, not approval for
unidentified recipients, answers or consents. Local records cannot authenticate a
human. Never manufacture proof in place of actual user approval.

## Continue without repeated batch prompts

Prepare source-backed documents, inspect every rendered page and create exact
execution-enabled manifests as before. Standing authority only derives
`APPROVED_BATCH` scopes with current Strong/Plausible fit. The latest canonical
assessment is checked again for every derived action, even if an older reviewed
draft still carries a stronger label. Reviewed CV bytes may
change within the same confirmed profile; each manifest pins its actual files,
answers, consents, destination and runtime. Hashes and fit labels do not prove
semantic truth or live eligibility.

```sh
python scripts/kit.py --data-dir ../career-private authorize-manifest --fingerprint MANIFEST --authorization FINGERPRINT
python scripts/kit.py --data-dir ../career-private check-authorization --fingerprint FINGERPRINT
python scripts/kit.py --data-dir ../career-private start-execution --fingerprint MANIFEST --bridge-id selected-supported-host-session --runtime-minutes 30
```

Continue with next-action/check-action/advance-execution. No second local manifest
proof is needed when the standing constraints match. Each child reserves its
submission limit transactionally against the shared cap; repeated derivation is
idempotent. Cancelled, superseded and expired children do not refund reservations.
This conservative rule prevents recycling uncertain attempts. Allocations are
separate from confirmed applications in `tracker` and `throughput`. Zero-limit
ASSIST scopes cannot evade the cap; use separately approved ASSIST manifests.

```sh
python scripts/kit.py --data-dir ../career-private revoke-authorization --fingerprint FINGERPRINT --reason "Candidate stopped this scope"
```

Revocation, expiry, changed profile/owner or modified review copies block derived
actions, including an issued action's preflight. Previously issued submits can
still be reconciled read-only. No automatic renewal, second submit or rewritten
old exact approval occurs. Derived origin and quota reservations are immutable;
create a fresh manifest instead of converting a derived scope to exact approval.

## Host and source boundaries

Standing authority does not accept contracts or clear required action-time
confirmations. The operator must report challenges, binding terms and missing
specific disclosure consent as form blockers until genuinely resolved through
supported host tools. New required answers/consents and unknown platform
permission still stop that job. No credentials, assessments, private endpoints,
stealth driver, global settings or hook trust are supplied here.

Schema 4 adds `campaign_authorizations` and immutable `manifest_authorizations`
allocations to the same private database. Existing profiles, document reviews,
exact approvals, attempts and receipts are preserved. Older CLI versions reject
schema 4 for nonlegacy commands; use the compatible version. Core checks cannot
sandbox arbitrary tools or an old library called outside the CLI.

Tests use fictional inputs, converter doubles and source-bound host receipts.
They verify local CLI/state behavior, not native integration or employer
permission. No model API, dependency, scheduler or browser worker is added.
