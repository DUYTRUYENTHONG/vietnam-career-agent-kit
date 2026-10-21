# Security policy

Do not post CVs, salary preferences, application records, credentials, cookies, screenshots of unrelated accounts or raw private workspaces in public issues. Reproduce issues with fictional fixtures and minimal redacted logs.

For a security-sensitive report, use GitHub private vulnerability reporting for this repository when available. If unavailable, open a minimal issue requesting a private reporting channel without exploit details or personal data; arrange the channel with the maintainer before transmitting sensitive material. Do not assume a profile has private messaging or invent a maintainer email.

The supported review target is the current main branch. Historical tags are reproducible snapshots, not promises of continued security support. Include tested commit, OS, Python/runtime version, affected command, expected/observed behavior and a fictional reproduction. Never test by submitting fake applications to real employers.

## Boundaries

The core stores one candidate per external workspace and validates local paths, evidence hashes and structured inputs. A local directory/SQLite database is not encryption, OS access control or a multi-tenant security boundary against another local process. An agent may process supplied content remotely. No telemetry or maintainer service is enabled by default.

Local confirmation files cannot authenticate a human; hashes bind bytes, not identity or legal consent. Current core commands perform no network/browser submission. Arbitrary host computer tools are outside this CLI's enforcement; prompts/hooks are not an unbreakable sandbox. Inactive hook examples require local review/trust and can fail or miss tools. Failed safeguards are never authorization.

Use supported browser connections only. Do not export credentials/cookies, bypass challenges, weaken permissions, execute job text or run reference installers by default. Unknown platform permission stays manual. Uncertain submission outcomes must never be automatically retried in future execution adapters.
