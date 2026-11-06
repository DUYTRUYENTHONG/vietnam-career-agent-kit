# External pilot fact coverage

For caller-declared employer/project connections across partitions, use the
separate [split connectivity diagnostic](TRAINING_SPLIT_AUDIT.md). Neither check
certifies independent evaluation or authorizes training.

Use this diagnostic before preparing a revised external `candidate_fact` pilot.
A completed run can contain older fact wording or omit a finalized project's
facts. Counting rows or finding a fact ID does not establish current coverage.

```powershell
python scripts/audit_training_coverage.py --expected ../private/selected-facts.json --train ../private/train.jsonl --evaluation ../private/evaluation.jsonl --aliases ../private/fact-aliases.json
```

The command reads only the explicit files and prints one JSON report to stdout.
Keep inputs and report private. It opens no ledger, reads no source directory,
uses no network/model, writes no file and changes no approval. Shell redirection,
if used, is the caller's separate output-file operation. Do not put a personal
report in Git; fact IDs themselves may reveal professional context.

## Input contract 1.0

`--expected` is a JSON array of explicitly selected facts, for example:

```json
[{"id":"F1","text":"Built a SQL reporting prototype."}]
```

Each training/evaluation JSONL row has exactly three ordered `messages` with
roles `system`, `user`, `assistant` and string content. User content is JSON
containing `candidate_fact` with nonempty string `id` and `text`; extra context
fields are allowed. Assistant content is not interpreted or approved.

This external pilot shape is distinct from the canonical reviewed
`cv-bullet-wording` export. For canonical exports, use existing `check-export` and
local-training validation, which reconstruct current source/review bindings.
This diagnostic neither replaces nor relaxes those checks.

Optional `--aliases` is a JSON object mapping old observed IDs to current
expected IDs, such as `{"old-F1":"F1"}`. Identity mappings need no alias. No
prefix stripping, fuzzy match or automatic alias is performed. Targets must be
distinct expected IDs; sources cannot themselves be expected IDs. Chains,
many-to-one aliases, duplicate expected IDs and malformed messages fail.

Limits: 1–10,000 expected facts; a nonempty training set; at most 10,000 combined
training/evaluation rows; at most 20 MB combined CLI input bytes. Blank JSONL
lines are ignored. LF separates records; embedded Unicode paragraph/line
separators remain part of a JSON string. Invalid/unreadable input returns a sanitized `needs_input`
JSON and exit 1 without quoting the private payload or path.

## Report contract 1.0 and interpretation

Valid audit execution returns exit 0 with `status: review_required`, including:

- `absent_from_training`, `absent_from_both`, `evaluation_only`: sorted expected IDs.
- `text_differences`: an observed text variant differs from the expected text.
- `multiple_text_variants`: an ID has conflicting observed wording variants.
- `unexpected_ids`: observed IDs outside the explicitly selected expected set.
- `train_evaluation_fact_overlap`: shared IDs after explicit alias projection.
- Row/unique-fact counts, canonical JSON input digests and exact input-file SHA256s.

Only NFC Unicode and whitespace normalization precede text comparison. A
difference is a review item, not proof of factual error. An equal string is not
source verification. Shared candidate facts across different held-out employers
are not automatically employer leakage; check group/provenance independence
separately. Additional historical facts may be legitimate, so unexpected IDs
are not automatically deleted.

Reports omit fact/assistant text and raw messages. This is not de-identification:
IDs and hashes still belong in the candidate's private workspace. Coverage does
not prove source validity, factual approval, label quality, suitable role fit,
independent evaluation or model quality. `training_authorized` and
`training_performed` remain false. No CV, dataset or model is promoted or repaired.

Compatibility: local Python 3.11+ standard-library CLI; no native MCP tool or
host hook is added. Regression tests use fictional inputs, check read-only
behavior, explicit aliasing, missing/evaluation-only facts, conflicting wording,
sanitized failures and row limits. Public CI makes no paid model calls.

## Vietnamese quick guide

Lệnh chỉ đối chiếu ID và nội dung giữa danh sách dữ kiện đã chọn với tập dữ liệu
thử nghiệm. Không tự suy luận hai ID là cùng một dữ kiện. Dữ kiện bị thiếu hoặc
khác cách diễn đạt cần được rà soát; kết quả không phải là phê duyệt huấn luyện,
xác minh kinh nghiệm hay bằng chứng mô hình tốt hơn. Giữ báo cáo và dữ liệu cá
nhân bên ngoài kho mã công khai.
