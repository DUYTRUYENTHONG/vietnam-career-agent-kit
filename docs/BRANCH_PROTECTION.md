# Main QA protection

The upstream `main` branch requires a pull request and passing automated QA
before merging. The source policy is
[branch-protection.main.json](../.github/branch-protection.main.json).
The GitHub server setting enforces it; committing this JSON alone does not.

## Required checks

All six current jobs in [ci.yml](../.github/workflows/ci.yml) are required:

| Check | Coverage |
|---|---|
| `fictional-tests (ubuntu-latest, 3.11)` | Standard tests, source hygiene, doctor, wrapper synchronization and fictional demo |
| `fictional-tests (ubuntu-latest, 3.12)` | Same checks with Python 3.12 |
| `fictional-tests (windows-latest, 3.11)` | Same checks on Windows with Python 3.11 |
| `fictional-tests (windows-latest, 3.12)` | Same checks on Windows with Python 3.12 |
| `document-integration` | Fictional DOCX/PDF rendering and approval integration |
| `local-plugin-integration` | MCP, credential boundaries and fictional Chromium form integration |

Each check is pinned to the observed GitHub Actions app ID `15368`. A matching
name from an unrelated status provider does not satisfy this policy. Branches
must be up to date with `main`, and review conversations must be resolved.
Use the app-pinned `checks` payload only: combining it with legacy `contexts`
causes the endpoint to reject the ambiguous configuration.

The rules also apply to administrators. Force pushes and branch deletion are
disabled. Merge commits remain supported so stacked PR history is preserved.

Human approvals are not a required gate: the configured approving-review count
is zero. PRs and automated QA are mandatory; this is not independent human review.
Stale approvals are dismissed when new commits arrive. No user/team/app bypass
allowance is configured. Authorized administrators can still edit repository
settings; this rule governs normal push and merge operations.

## Maintainer workflow

1. Create a short `codex/` branch from current `main` and make a focused change.
2. Run the applicable local checks in [CONTRIBUTING](../CONTRIBUTING.md).
3. Push the branch and open a PR targeting `main`.
4. Fix failures; do not skip tests, remove required checks or use `--admin`.
   If the base moves, update the branch and wait for the new required results.
5. Resolve review threads, verify all six check results on the current head and
   merge with exact-head matching. Record the actual CI state afterward.

A cancelled or missing required result is not a pass. Renaming a CI job or
changing its matrix must include a deliberate policy update; otherwise merges
will wait for the old required name. Keep the workflow and server rule aligned.

## Forks and verification

GitHub protection settings are not installed by cloning or forking. A fork owner
can inspect this policy, verify their actual workflow/app names, then apply it
with repository Administration permission:

```sh
gh api --method PUT repos/OWNER/REPO/branches/main/protection --input .github/branch-protection.main.json
gh api repos/OWNER/REPO/branches/main/protection
```

Inspect existing settings before applying: PUT updates protection and supplied
arrays replace values. Do not overwrite another repository's stronger controls.
Check the API readback for all six app-pinned names, strict status checks,
administrator enforcement, required PRs and resolved conversations, and disabled
force pushes/deletion. For a non-destructive merge-gate check, inspect a PR while
its required QA is pending: GitHub should report the merge state as `BLOCKED`.
Wait for every required result before merging. Do not push a failing commit to
`main` to test protection.

Reference: [GitHub's protected-branch API](https://docs.github.com/en/rest/branches/branch-protection#update-branch-protection).

## Earlier branch-specific policy

The [parallel-tinyfish policy and instructions](BRANCH_PROTECTION.parallel-tinyfish.md)
are retained as historical branch-specific guidance. This main policy does not
change that feature branch or apply a wildcard rule to every `codex/` branch.
