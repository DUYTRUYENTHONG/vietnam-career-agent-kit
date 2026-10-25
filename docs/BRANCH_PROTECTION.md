# Protecting the parallel execution branch

The maintainer requested protection of `codex/parallel-tinyfish`. The checked-in
[configuration](../.github/branch-protection.parallel-tinyfish.json) is a REST API
payload, not a workflow or an automatically installed rule. Cloning the kit does
not change any repository settings.

## Rules

| Rule | Setting and reason |
|---|---|
| Pull request | Required for updates to this branch; use a child branch for new work. |
| CI | All four Windows/Linux Python 3.11/3.12 test jobs and document integration must pass. |
| Check producer | GitHub Actions app `15368`, observed on the existing checks. |
| Current base | The PR branch must be up to date before merging. |
| Review threads | Conversations must be resolved. |
| Administrators | The same requirements apply to administrators. |
| Force-push and deletion | Both disabled. |
| Mandatory reviewers | Zero, so a solo maintainer can merge their own PR after checks. This is not independent human review. |
| Branch lock | Off; normal PR development remains possible. |

The JSON targets this branch only when applied to the endpoint below. It does not
protect `main`, merge the existing PR, configure all `codex/*` branches, install
hooks, or grant another account access. Keep actual checks and their names aligned
with [CI](../.github/workflows/ci.yml) before changing the policy.

## Apply after the current change is pushed

An administrator can run these commands from the repository root with an
authenticated GitHub CLI. Inspect existing rules first: a PUT replaces the
specified protection configuration. Obtain authority before changing another
repository's settings.

```powershell
gh api repos/DUYTRUYENTHONG/vietnam-career-agent-kit/branches/codex%2Fparallel-tinyfish/protection
gh api --method PUT repos/DUYTRUYENTHONG/vietnam-career-agent-kit/branches/codex%2Fparallel-tinyfish/protection --input .github/branch-protection.parallel-tinyfish.json
gh api repos/DUYTRUYENTHONG/vietnam-career-agent-kit/branches/codex%2Fparallel-tinyfish/protection
```

Verify the returned server state: strict checks, all five context names/app IDs,
PR requirements, administrator enforcement, resolved conversations, and disabled
force-push/deletion. A local JSON file or a successful test run does not prove
that protection is active. GitHub plan or token permissions may prevent applying
it; report the actual response without claiming success.

## Subsequent changes

```powershell
git switch -c codex/next-focused-change
# Make and verify a focused change using docs/change-workflow.md.
git push -u origin codex/next-focused-change
gh pr create --base codex/parallel-tinyfish --head codex/next-focused-change
```

Keep the existing stacked PR's destination unchanged unless a maintainer requests
a merge or retarget. Do not disable protection to make a routine push succeed.

Primary reference: [GitHub branch-protection REST API](https://docs.github.com/en/rest/branches/branch-protection#update-branch-protection).
