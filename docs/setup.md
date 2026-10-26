# Setup, measured walkthrough and recovery

For the guided path, use [agent setup](AGENT_SETUP.md), optional
[TinyFish setup](TINYFISH_SETUP.md) and the [setup-and-goal prompt](../prompts/SETUP_AND_GOAL.md).

## Local setup

Clone the repository and use an existing Python 3.11+ interpreter. Core preparation requires no package installer or privileged step and no third-party runtime/test packages. Optional Slice 2 rendering has a separate explicit setup in documents-and-approval.md; no model API is added. Agent subscriptions/search/browser services are separate and optional.

```sh
python scripts/kit.py doctor --runtime generic
python scripts/demo_slice1.py --data-dir ../career-demo-private
python scripts/kit.py --data-dir ../career-demo-private resume
python scripts/kit.py --data-dir ../career-demo-private report --format md --output reports/checkpoint.md
```

This four-command persistent walkthrough uses fictional data only. The demo directory must be new and empty. Run `python scripts/demo_slice1.py` for an automatically removed temporary workspace. `--candidate b` runs the Vietnamese example in a separate new directory. No browser, model or employer request occurs.

## Individual job-seeker commands

Global `--data-dir` precedes the command. This example starts with fictional inputs so it can be reproduced safely; real sources require actual user review.

```sh
python scripts/kit.py --data-dir ../career-private init --language en
python scripts/kit.py --data-dir ../career-private import-cv --source-id CV1 --file examples/fictional/cv-a.md
python scripts/kit.py --data-dir ../career-private import-profile --file examples/fictional/profile-a.json
python scripts/kit.py --data-dir ../career-private profile
```

Profile import normally returns `needs_input` (exit 2) with the exact fingerprint and conflicts. Inspect every extracted fact/preference. After an actual explicit confirmation, save a file **inside that private directory** containing `CONFIRM PROFILE <current fingerprint>` and run:

```sh
python scripts/kit.py --data-dir ../career-private confirm-profile --fingerprint CURRENT_FINGERPRINT --confirmation ../career-private/profile-review.txt
python scripts/kit.py --data-dir ../career-private import-jd --file examples/fictional/job.json
python scripts/kit.py --data-dir ../career-private assess --job-id 1 --matrix examples/fictional/matrix.json
python scripts/kit.py --data-dir ../career-private prepare --job-id 1 --plan examples/fictional/plan.json
python scripts/kit.py --data-dir ../career-private handoff --job-id 1
```

Replace CURRENT_FINGERPRINT with the inspected value and use the actual returned job ID. Never generate a real person's confirmation merely to make a command pass. The demo's automatic confirmation is explicitly fictional. `handoff` returns `manual_required`/exit 2: it lists current draft documents and remaining verification, not a sent application. The job URL is a source, not an inferred final recipient. Markdown may require conversion/review before an employer accepts it.

Imports accept only explicitly supplied paths. TXT/Markdown evidence is normalized to UTF-8/LF before content-addressed storage/hash; the snapshot hash names those normalized bytes, not the original file's encoding/BOM/line endings. Source IDs cannot be reassigned to different content. Import a revision under a new source ID and re-review affected facts.

## Measured evidence

Windows local environment: Python 3.12.14; Codex CLI inventory 0.137.0; Claude Code inventory 2.1.205. No paid model calls/native host callback tests were run. Real CLI subprocess tests execute from another working directory. Two complete fictional flows prove separate identities, facts, languages, cities, roles and tracker/artifact paths. The newline/hash regression specifically exercises Windows CRLF input. Release evidence records the exact final test count and CI run rather than asserting a universal setup time.

## Upgrade and uninstall

Commit or back up your own toolkit changes before updating the public checkout. Private directories remain outside it. Review the new changelog and run tests first; do not run reference installers or auto-trust hooks. `init` performs additive migrations through schema 6 and preserves existing rows/approvals. Newer unknown schema versions are blocked. Back up your private directory before upgrading a production workspace; the repository never upgrades or overwrites it on clone/pull. Older clients reject schema 6. Old preparation-only approvals do not gain execution authority; see execution.md for the separately reviewed host scope.

Wrapper generation affects only repository-owned .claude skill pointers and inactive examples. Preview with `python scripts/generate_adapters.py --dry-run`; verify with `--check`. No global settings or active hooks are installed. If you manually enabled examples, remove only those reviewed entries from your project configuration, preserving other settings and a backup. There is no automatically granted hook trust to revoke.

Uninstall by removing the chosen clone through your normal file manager after preserving wanted local changes. This is separate from candidate retention: do not delete private workspaces, evidence or submitted snapshots unless the user explicitly requests it. No service, daemon, scheduled task, telemetry endpoint or provider key needs cleanup.
