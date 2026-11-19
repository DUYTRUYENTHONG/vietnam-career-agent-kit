# Cross-check CV evaluation models

Consumer: existing user-selected evaluation host. Use the fixed CV/JD/source and
six-dimension rubric from the recorded review task. This prompt does not select
another model, authorize a provider or create human reference labels.

1. Prepare judge inputs with `cv_eval_crosscheck.py` from current authorized
   review captures. Feed each judge only the system/user messages, never the
   reference assistant response. Keep example IDs as external routing metadata.
2. Capture two bounded grader passes against the same input hash and rubric.
   Default to the existing host. Distinct model/runtime choices require user
   selection; two passes or reviewer personas of the same model are consistency
   checks, not independent models. Record unknown when identity is unavailable.
3. Return the existing six editorial dimensions, each with an integer0..3,
   exact statement citations and a brief source-based rationale. Do not grade
   length as quality or infer factual support from polished phrasing.
4. Cross-check captured outputs. Retain every supplied reference case. Missing,
   malformed and wrong-citation predictions remain failures; do not drop them
   to improve agreement. Agreement is not factual correctness or hiring success.
5. Escalate conflicts and missing outputs for human adjudication. Never select
   the higher grade, average away a factuality conflict, fabricate a deciding
   reviewer or automatically call more models to resolve a tie.
6. Keep development corrections separate from the reserved final test. Only
   actual independent human review can supply human labels. Model judgments
   remain proposals until resolved; use current reviewed exporters separately
   for any later training. Do not train and validate the writer solely with its
   own grader. No model promotion or application authority follows from scores.
