# Skill and feature update workflow

Apply this convention to every skill addition, skill revision and feature change.
Keep the implementation and its explanation in the same focused change.

1. Describe the concrete problem and resulting user behavior. Reuse an existing
   canonical skill when it already owns the capability; update its host wrappers
   through the generator when needed.
2. Update the relevant usage instructions and CHANGELOG.md. Change schemas,
   compatibility evidence and migration notes when the behavior requires them.
   Explain new inputs, output, failure behavior and material limitations. Record
   measured performance changes with the workload and comparison, not estimates.
3. For external skill/dependency adoption, record the exact source revision,
   file path, content hash, license/notices, dependencies and actual acceptance
   result in docs/REFERENCE_REVIEW.md and the relevant dependency record. Discovery
   is a candidate list; an upstream update does not inherit approval or test status.
4. Run the checks required by AGENTS.md and CONTRIBUTING.md. Add behavioral
   regressions when logic or an invariant changes. Review the staged diff and keep
   candidate information and runtime artifacts outside Git.
5. Commit a coherent change with a descriptive subject:
   `<type>(<scope>): <concrete result>`. Use feat, fix, perf, docs or chore as
   appropriate. Avoid subjects such as "update", "changes" or "fix stuff".
   For example: `perf(documents): validate only the selected job draft`.
6. Push the branch to the configured GitHub remote and use the PR template.
   Report the commit, PR link, actual checks and CI status. Keep failed or pending
   checks explicit; do not describe a pushed branch as merged or released. Follow
   the repository's review/merge rules before merging.

This is a standing convention applied during authorized work, not a scheduled
updater. It does not install new upstream skills or start campaigns automatically.
