# Contributing

Read GOAL.md, AGENTS.md, docs/architecture.md and the current slice in docs/roadmap.md. Product development never requires a real CV or live application. Use examples/fictional and local test portals. Keep private workspaces, screenshots, account data and approvals out of issues, fixtures and commits.

Core needs Python 3.11+ and the standard library. No model/API credential or pip install is required:

```sh
python -m unittest discover -s tests -v
python scripts/generate_adapters.py --check
python scripts/check_repository.py
python scripts/demo_slice1.py
```

Use a short `codex/` branch and focused commits. Add behavioral tests for changed invariants, especially provenance, isolation, stale approvals and interruption recovery. Do not write tests that merely assert your implementation's wording. Use failing regressions for discovered defects; do not remove or skip failing checks to publish. Native compatibility needs a named interface/version/OS and actual test evidence; mocked local success cannot certify a real portal.

core/contracts.py and the document/manifest operation validators are the runtime input authority; schemas/contracts.schema.json and schemas/documents-approval.schema.json supply editor shapes. Update code/schema/docs together when changing a contract and version any incompatible change. SQLite is canonical; JSON/Markdown exports are derived. Keep migrations additive and test existing data preservation. Stop on newer unsupported schema versions rather than overwriting state.

The optional tests are separate: explicitly provision requirements-documents.lock, LibreOffice Writer and DejaVu Sans, set CAREER_KIT_SOFFICE to the trusted absolute executable path, then run python -m unittest discover -s tests_optional -v. CAREER_KIT_QA_DIR optionally exports only those fictional test artifacts to a new directory for visual review. Never point CI at real candidate files. Standard-library tests use clearly identified converter test doubles; passing them does not certify native rendering. Inspect every emitted page separately after layout changes.

Canonical skills live under .agents/skills. Run `python scripts/generate_adapters.py --dry-run`, review the proposed repository-owned files, then run it without flags to update wrappers/inactive examples. `--check` must pass before publishing. Do not copy a host's settings into another runtime or overwrite global/user settings. Any future installer must preview changes, back up user-owned configuration and provide a scoped uninstall.

For dependencies/reference material, record exact versions/commits, license, network/install effects and attribution. Do not execute unreviewed installers. Optional live-provider tests require separate configuration and a stated budget; deterministic CI remains free of model calls and real employers.

PRs should explain the concrete problem/result, contract changes, actual checks and unresolved limits. Inspect the staged diff and run the bounded public-source checker; the checker is not complete secret/privacy detection. Report security issues through SECURITY.md rather than publishing candidate data.
