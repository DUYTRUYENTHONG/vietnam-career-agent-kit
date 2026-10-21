# Slice 1 implementation evidence

Reviewed 21 October 2026. This is the first implementation iteration, not certification of the full first usable release described in GOAL.md. Exact manifests, document rendering and live application execution remain later roadmap gates.

## Working path

The generic Python CLI diagnoses the environment, creates an external one-candidate SQLite workspace, imports explicit UTF-8 TXT/Markdown evidence, validates a versioned profile, requires confirmation of its exact fingerprint, imports/deduplicates a structured JD, validates a requirement-by-requirement evidence matrix, produces a quote-preserving Markdown draft and source map, records review_required state, exports a checkpoint, and resumes without inferring submission.

The manual handoff includes the current CV separately from private review artifacts, identifies the source URL, leaves the unverified application destination unknown and lists remaining checks. It does not approve or submit anything. Existing legacy hash/approval records remain compatible local bookkeeping.

## Measured local checks

Windows, Python 3.12.14; Codex CLI inventory 0.137.0 and Claude Code inventory 2.1.205. Host executable inventory does not prove native agent integration. No third-party runtime/test packages or paid model calls are required.

```sh
python -m unittest discover -s tests -v
python scripts/generate_adapters.py --check
python scripts/check_repository.py
python scripts/demo_slice1.py
python scripts/demo_slice1.py --candidate b
```

The local unittest run passed **41 tests**. Adapter synchronization found no drift. The bounded repository checker validates UTF-8/JSON, ten restricted skill frontmatters/shared wrappers and flags selected private-artifact/credential patterns; it is not an exhaustive privacy or secret scanner. The official PyYAML-dependent skill validator was not run. The fictional demo exercises both isolated users and languages without contacting example.test or employers.

Tests cover exact source linkage, unsupported and pending facts, explicit conflict groups, long Vietnamese names, distinct salary bases, duplicate/closed/unverified jobs, inert malicious JD text, changed evidence/JDs/draft bytes, preserved legacy rows/approvals during additive upgrade, newer-schema rejection, protected report paths, terminal/uncertain duplicate prevention, missing capabilities and structured CLI errors. Original standalone hook protocol tests remain. Hooks are inactive and native callback enforcement is unverified.

## Consolidated review

The final review corrected null-industry handling, protected report exports from overwriting canonical/private evidence files, blocked preparation/handoff for submitted or uncertain jobs, separated private source maps from attachment documents, and limited generic runtime verification to the recorded Python/OS matrix. Tests reproduced the new issues before the corresponding fixes where behavior changed.

No personal candidate information, credentials, application screenshots, private campaign records or downloaded reference code is included. Four reference projects were inspected as pinned, untrusted source text; inspected files, hashes and license implications are in REFERENCE_REVIEW.md. No reference installers or hooks were executed.

## Deliberate limits and next slice

The draft selects/orders confirmed exact quotes; it does not certify semantic truth, human identity or a claimed qualification. A complete user review is still required. PDF/DOCX input/output, one permitted network discovery connector, authenticated runtime integration, browser adapters, expiry-bound batch approval and attempt-before-submit recovery are unimplemented. Rendering failures, browser interruptions and live-provider behavior are not claimed tested in Slice 1.

Next: define the reviewed document content model, render Unicode DOCX/PDF with a fully locked optional dependency set, inspect every rendered page, and create exact expiring campaign manifests. Keep those checks in the shared core before enabling any browser execution.

The [successful GitHub CI run](https://github.com/DUYTRUYENTHONG/vietnam-career-agent-kit/actions/runs/39554806475) tested implementation commit a44beb0f803a1572c1f67d7935982d8913a0cc88 on all four Linux/Windows and Python 3.11/3.12 combinations. Every job passed the 41-test fictional suite, source check, wrapper drift check, capability report and disposable demo. These results certify the local CLI scope only, not native agent/browser integration.
