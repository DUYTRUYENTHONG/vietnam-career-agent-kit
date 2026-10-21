# Portable core architecture

## Capability map and build order

| Module | Responsibility | Depends on |
|---|---|---|
| contracts | Versioned validated inputs, outcomes, localization and policy | Standard library |
| ledger | External workspace, immutable evidence and transactional SQLite | contracts |
| preparation | Profile confirmation, JD normalization, fit and drafts | ledger |
| documents | DOCX/PDF rendering and reviewed artifact hashes | preparation |
| discovery | Permission-declared source imports/connectors and coverage | contracts, ledger |
| execution | Exact campaign authorization, browser boundary and attempt recovery | documents, discovery, ledger |
| adapters | Runtime-specific entrypoints using the same tools | preparation, execution |

Build order follows the vertical slices in roadmap.md. This is one system, not a merger of reference orchestrators.

## Slice 1 implementation contract

`core/ledger.py` retains the existing tested Kit implementation; `scripts/kit.py` remains the compatible executable/import entrypoint. `core/contracts.py` validates strict versioned inputs. `core/workflow.py` adds the preparation flow using the same `workflow.sqlite3`, not another database. New tables are additive and keep existing jobs/approvals/events. A higher unsupported schema version is blocked; repeated initialization preserves state.

SQLite is authoritative for candidate/profile confirmation, imported source metadata, job documents, assessments and drafts. Imported CV bytes live in content-addressed private evidence files; Markdown and reports are derived artifacts, not competing editable trackers. Every assessment/draft binds current profile, source and JD fingerprints. Resume reports staleness explicitly. Each workspace selects one candidate. No global candidate configuration exists.

The host reasons and proposes structured profile/JD/matrix/selection files. Deterministic code validates them; it cannot authenticate a human or prove a semantic claim. Slice 1 only renders exact confirmed source quotes into drafts, with internal source mapping kept separate. No freeform agent-written experience bullet is accepted as new evidence. Profile confirmation is local bookkeeping after actual user review, not a signature.

UTF-8 TXT/Markdown CV import is implemented first. PDF/DOCX extraction/rendering is a later explicit capability; absent support returns manual_required. English/Vietnamese summary labels and Markdown headings are selected explicitly. City aliases normalize for comparison while exact wording remains stored. Compensation fields never convert or infer gross/net, period, currency or bonuses.

## Boundaries

- Core setup/import/assessment/draft/report commands are local. They do not browse, call models, upload or submit.
- Maintainer instructions are AGENTS.md/CLAUDE.md. Job-seeker workflow is prompts/MASTER_PROMPT.md and canonical skills/policy, activated only by a career request.
- Source connectors declare operations separately. A registry entry is not an implemented connector or permission. Manual structured JD import is the working first connector.
- Runtime wrappers read shared skills and call the same CLI. They grant no permissions and install no active hooks/global settings. Generic CLI execution is distinct from native runtime/browser verification.
- Existing local package approval checking remains available. Full finite campaign authorization and attempt-before-submit execution are later capabilities. APPROVED_BATCH is unavailable until those paths and local portal recovery tests exist.
- External computer tools outside this CLI are not sandboxed by core checks. Missing/failed host hooks never grant permission.

## Verification

Run `python -m unittest discover -s tests -v`, `python scripts/check_repository.py` and `python scripts/demo_slice1.py --data-dir ../career-demo-private`. The demo uses only checked-in fictional inputs and records a clearly labelled fictional confirmation. Integration tests execute the real CLI without model calls. CI covers Linux/Windows and Python 3.11/3.12; no external accounts are accessed.
