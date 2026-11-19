# CV review cycle acceptance

Observed locally on Windows with the provisioned Python 3.12 runtime:

- `python -m unittest discover -s tests -v`: 570 tests passed in the working
  checkout, including pre-existing unrelated uncommitted experiment files.
- An isolated export of the staged source: all eight `tests.test_review_cycle`
  behavioral tests passed. No unrelated experiment files were in this export.
- `python scripts/check_repository.py`: passed in the working checkout and
  isolated staged export (390 UTF-8 source files in the latter). The isolated
  export needed temporary local Git metadata for the checker's file inventory.
- `python scripts/generate_adapters.py --check`: no drift in the isolated export.
- `python scripts/demo_slice1.py`: fictional local preparation/handoff passed.
- Staged whitespace and source review passed. The commit contains no candidate
  data, actual review labels, model weights, runtime output or account material.

The focused tests cover comparison/export compatibility, rubric/identity/JD
binding, source-context confounds, statement citations, score bounds, malformed
JSON, missing/invalid prediction penalties, CLI no-overwrite/public-root refusal,
and unchanged ledger/input bytes. The source checker is bounded, not a complete
privacy or secret audit. Code review was a consolidated author review, not an
independent peer approval.

Compatibility: **Verified** for the bounded local Python diagnostics tested
above. **Instruction-only** for the host grade/tailor/regrade workflow.
Actual learned-grader accuracy, independent real labels, model training,
cross-candidate generalization and hiring improvement remain **unverified**.
GitHub CI is a separate exact-commit gate; local passing checks do not claim that
it has completed or that this feature has merged.
