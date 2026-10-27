# Main integration and community-clone QA

As of **27 October 2026**, the 13 pending feature PRs below are merged into the
default `main` branch. A normal clone includes the CV-first starter, ten canonical
skills, prompts, optional transports and anonymous case-study tracker. No feature
branch or preview-tag switch is required.

## Merge gate and order

- Checked the dependency chain, exact PR heads, conflicts, unresolved review
  threads, requested changes and completed test results before merging.
- Consolidated maintainer review covered finite authorization, profile/artifact
  binding, durable attempts, uncertain-send recovery, isolated sessions, deadlines,
  provider/cache boundaries, evidence-only wording and public-source packaging.
  Existing regressions exercise these failure paths. This is not a new independent
  peer review or certification of live providers.
- Retargeted each next PR to `main`, then used a merge commit with exact-head
  matching. No squash, rebase, forced push, protection bypass or source rewrite.
- Predicted every merge tree before the write and verified it again afterward:
  each merged tree exactly matched that PR's tested source head.
- PR #16 had already merged into its parent branch and is preserved through #15;
  it was not an additional pending PR.

| Dependency order | Tested source head | Merge into main | Current head QA |
|---|---|---|---|
| [#7](https://github.com/DUYTRUYENTHONG/vietnam-career-agent-kit/pull/7) | `a8fa126` | [cc3cfc9](https://github.com/DUYTRUYENTHONG/vietnam-career-agent-kit/commit/cc3cfc9535747e6dbb2350a5ce6457ffce686f0b) | 5 passed |
| [#8](https://github.com/DUYTRUYENTHONG/vietnam-career-agent-kit/pull/8) | `434df3a` | [ed36ac3](https://github.com/DUYTRUYENTHONG/vietnam-career-agent-kit/commit/ed36ac3de09c707f998b58b60b346f1a919a74e7) | 5 passed |
| [#9](https://github.com/DUYTRUYENTHONG/vietnam-career-agent-kit/pull/9) | `35e707b` | [9d89f4f](https://github.com/DUYTRUYENTHONG/vietnam-career-agent-kit/commit/9d89f4fdb3ddc1ed5032bb89919131a4451324be) | 5 passed |
| [#10](https://github.com/DUYTRUYENTHONG/vietnam-career-agent-kit/pull/10) | `de22691` | [983e91b](https://github.com/DUYTRUYENTHONG/vietnam-career-agent-kit/commit/983e91bc8a5c76b1e5b48294b6fc9d377490c69b) | 5 passed |
| [#11](https://github.com/DUYTRUYENTHONG/vietnam-career-agent-kit/pull/11) | `5d5e4f3` | [2b94137](https://github.com/DUYTRUYENTHONG/vietnam-career-agent-kit/commit/2b941376cd287309d81503a82cb01fd4d62c8a39) | 5 passed |
| [#12](https://github.com/DUYTRUYENTHONG/vietnam-career-agent-kit/pull/12) | `90fd3ad` | [71206a9](https://github.com/DUYTRUYENTHONG/vietnam-career-agent-kit/commit/71206a93a1ad7a616e916b7843d32481e5e82621) | 5 passed |
| [#13](https://github.com/DUYTRUYENTHONG/vietnam-career-agent-kit/pull/13) | `e2e5027` | [76c0677](https://github.com/DUYTRUYENTHONG/vietnam-career-agent-kit/commit/76c06775df6d9a5cbd0eb0182a4cd3b57875a239) | 5 passed |
| [#14](https://github.com/DUYTRUYENTHONG/vietnam-career-agent-kit/pull/14) | `643d0f9` | [a178f2b](https://github.com/DUYTRUYENTHONG/vietnam-career-agent-kit/commit/a178f2bd01363f495aa34477c424e16084d8322a) | 5 passed |
| [#15](https://github.com/DUYTRUYENTHONG/vietnam-career-agent-kit/pull/15) | `9c8ce2f` | [5bb382b](https://github.com/DUYTRUYENTHONG/vietnam-career-agent-kit/commit/5bb382bdadfd5a41ae9bdc9361d024fa5861aadd) | 5 passed |
| [#17](https://github.com/DUYTRUYENTHONG/vietnam-career-agent-kit/pull/17) | `6de45a7` | [7ff6169](https://github.com/DUYTRUYENTHONG/vietnam-career-agent-kit/commit/7ff616986663e09c8dda3efdf91ba3848f067f11) | 5 passed |
| [#18](https://github.com/DUYTRUYENTHONG/vietnam-career-agent-kit/pull/18) | `8a3e844` | [675d797](https://github.com/DUYTRUYENTHONG/vietnam-career-agent-kit/commit/675d797d5442c544a0ee50df85516801e4e22f90) | 6 passed |
| [#19](https://github.com/DUYTRUYENTHONG/vietnam-career-agent-kit/pull/19) | `f3aa860` | [8430ff2](https://github.com/DUYTRUYENTHONG/vietnam-career-agent-kit/commit/8430ff27b09c8b4df791c143ab78da96b25a6897) | 6 passed |
| [#20](https://github.com/DUYTRUYENTHONG/vietnam-career-agent-kit/pull/20) | `e8925ee` | [7e7cd39](https://github.com/DUYTRUYENTHONG/vietnam-career-agent-kit/commit/7e7cd391e100992e678f96b2181ea3ccddb8550f) | 6 passed |

PR #18's cancelled document job was rerun successfully before its merge. All
current test jobs for each source head passed at merge time. Superseded push runs
for intermediate merge commits may be cancelled to avoid redundant CI; they are
separate from the completed PR-head tests and final-main checks.

## Integration and fresh-clone acceptance

The integrated source at `7e7cd391e100992e678f96b2181ea3ccddb8550f` has tree
`64b8f23c2cf5666c4159b408f9c3b09e1c2b3983`, identical to the tested immutable
`community-v0.2.0` source. The community release passed 277 standard tests and
all six Windows/Linux, Python 3.11/3.12, document and local-plugin CI jobs.
See [the measured release evidence](COMMUNITY_RELEASE_QA.md).

A new, single-branch clone from the actual GitHub `main` passed on Windows with
Python 3.12.14:

- Generic `doctor`, repository hygiene, generated-wrapper synchronization and
  disposable fictional preparation demo.
- `start-campaign` against a fictional Markdown CV in a new external workspace:
  target 100, `execution_authorized:false`, no candidate profile, approval, job
  or confirmed submission created.
- No model API, credentials, paid provider, candidate account or real application.

The final documentation follow-up changes clone/fork instructions to `main` and
adds this evidence record; executable source remains unchanged. Its own CI and
subsequent default-branch CI are available in [GitHub Actions](https://github.com/DUYTRUYENTHONG/vietnam-career-agent-kit/actions).
Completed source-head tests do not predict a pending run's result.

## Community distribution and limits

Use [CV-first setup](COMMUNITY_START.md) and [the starter prompt](../prompts/COMMUNITY_START.md).
Fork `main` for the latest source, or use the unchanged pinned release/ZIP when a
reproducible snapshot is preferred. Keep LICENSE, AUTHORS and THIRD_PARTY_NOTICES.

The default is 100 new Strong/Plausible-fit confirmed submissions, not job offers
or an hourly guarantee. Source integration does not certify live employer forms,
OAuth, paid providers, native host discovery or ten simultaneous sessions. Actual
host tools and scoped permissions are still required. Personal workspaces remain
outside the public clone and are not altered by merging this source.
