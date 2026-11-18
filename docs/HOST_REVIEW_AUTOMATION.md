# Existing-host reviewer automation

Experimental standard-library coordinator for the three first-layer reviewer
roles. It makes no model API/network calls, installs no native agents and adds
no scheduler. A running user agent or trusted in-process host callback consumes
its frozen messages. Existing subscriptions/host usage retain their own limits;
the kit does not claim they are free or expose invented savings.

```sh
python scripts/cv_review_agents.py --root ../private start \
  --requests research/current-review-requests --cycle research/review-cycle-001
python scripts/cv_review_agents.py --root ../private advance \
  --cycle research/review-cycle-001
# Existing host performs the emitted review and saves the actual JSON reply:
python scripts/cv_review_agents.py --root ../private advance \
  --cycle research/review-cycle-001 --response research/evidence-reply.json
# Continue with each emitted role, at most three new handoffs.
```

`host_review_required` returns the exact bound request after an exclusive,
flushed handoff record is saved. `waiting_for_original_reply` returns role/hash
without replaying its messages. After an interruption, reconcile the original
call; do not automatically reissue it. An invalid semantic-review format or
citation stops the cycle and captures the rejected reply. Input JSON parse
errors preserve the pending handoff and caller's original file. No automatic
repair, provider switch or retry is implemented.
An exact replay of an already captured reply is an idempotent acknowledgement,
not another model invocation. It cannot reissue an outstanding next role;
conflicting replays cannot overwrite accepted replies.

The existing host must choose the **current** confirmed CV/JD and draft revision.
Source binding checks the selected artifacts, not an external claim that they
are the newest canonical profile. A job title or matching input fingerprint
alone is not a human approval. Dataset, browser and account operations are not
part of this coordinator.

On completion, one source-bound `advisory` bundle contains the captured model
responses and consolidated findings. Repeating advance returns that completion
without new host handoffs. If artifact writing was interrupted, matching saved
completion is checked rather than generating another model review. Malformed
partial artifacts or changed sources stop for reconciliation. A single-writer
lock is never automatically discarded. File checks enforce workflow integrity,
not authenticated model/human identities or protection from a malicious operator.

## Exact completed-review reuse

```sh
python scripts/cv_review_agents.py --root ../private start \
  --requests research/current-review-requests --cycle research/reuse-cycle-002 \
  --reuse-advisory research/previous-complete-advisory
```

Reuse requires the exact request manifest, prompts, draft/evidence inputs, all
three valid captured roles and matching advisory. Changed or incomplete results
fail. Reuse is recorded as cached roles and requires zero new host handoffs.
This is artifact reuse, not measured provider KV-cache hits or cost savings.

An optional trusted integration may call `core.reviewer_automation.run_with_host`
with its own `respond(request)` callback. The callback is supplied in code by
the host; no command, SDK, code or endpoint is loaded from candidate/JD data.
The loop makes at most three new callbacks and stops on errors. CLI handoffs and
callback control are tested with fictional inputs; native autonomous Codex model
dispatch is not installed or verified by those tests.

## Prompt audit and acceptance

Scope: canonical tailoring routing, HOST_REVIEW_AUTOMATION host instructions,
request/response consumer and cache/restart branches. Consumers use the already
selected host model, whose identity remains unknown if not exposed. No model
switch or new paid service is introduced. Source text remains data; inherited
human, disclosure and semantic-review constraints remain intact.

Counterexamples: restarting after a lost reply could repeat a model call;
reusing a review under the same job name could hide changed evidence/prompts;
three clean AI outputs could be mistaken for human approval. Implemented checks:
record-before-handoff, pending-without-replay, exact completed-cache validation,
source rechecks and permanently separate human-resolution/authority flags.
Fictional tests cover those cases, callback exceptions, locks and corrupted
responses. They do not establish model quality, native dispatch or hiring gain.
