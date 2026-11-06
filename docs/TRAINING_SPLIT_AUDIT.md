# Explicit training-group connectivity

Before preparing an external pilot, declare which examples share an employer,
underlying project, exact source wording or another reviewed leakage boundary.
One shared project can bridge two employers even when their requirement IDs and
example IDs differ. Checking only pairwise ID overlap misses that connection.

```powershell
python scripts/audit_training_splits.py --groups ../private/split-groups.json
```

This separate standard-library diagnostic reads one explicit file and prints JSON.
It opens no ledger or source directory, writes no file, calls no model/network and
changes no approval, canonical export validator or trainer. Keep the input/report
private: row identifiers can reveal professional context. This is not a native
MCP tool, automatic export gate, split generator or independence certificate.

## Input contract 1.0

```json
{"schema_version":"1.0","rows":[
  {"id":"example-A","partition":"train","groups":["employer:one","project:alpha"]},
  {"id":"example-B","partition":"development","groups":["employer:two","project:alpha"]},
  {"id":"example-C","partition":"test","groups":["employer:two"]}
]}
```

Only the shown keys are accepted. Select 1–10,000 rows, with unique IDs and 1–64
distinct group labels per row. IDs and groups are nonempty NFC/whitespace-normalized
strings, at most 256 characters. Partitions are `train`, `development` or `test`.
The CLI accepts at most 20 MB. Invalid/unreadable/oversized input returns sanitized
`needs_input`, exit 1, without echoing source content or paths.

Group labels are opaque and caller-declared; prefixes are examples, not inferred
semantics. Use the same exact label for the same reviewed boundary. Include all
applicable groups, including aliases or paraphrases known to share a source.
The command does not read source text, infer employer IDs from requirement IDs,
normalize aliases or detect missing/incorrect group annotations. Different labels
for the same project can hide leakage. Never add groups merely to manufacture an
apparently independent split.

## Report contract 1.0

Valid execution returns exit 0 and `status: review_required`, including row and
component counts, sorted cross-partition components with row IDs/partitions,
canonical input SHA256 and exact input-file SHA256. It omits raw group labels.
The example above reports one component containing A, B and C: A bridges B through
the project, while B bridges C through the employer. Iterative union-find handles
long transitive chains without recursion.

Exit 0 means the diagnostic ran, not that evaluation is independent. Review every
reported connection and keep the entire connected component in one partition
when those declared boundaries are required. Zero conflicts says only that the
supplied groups do not cross partitions. `split_independence_verified`,
`training_authorized` and `training_performed` remain false. It does not detect
previous evaluation exposure, semantic leakage, factual errors or label quality.
Previously inspected evaluation cases do not become fresh holdouts by relabeling.

Use [fact coverage](TRAINING_COVERAGE.md) separately for omissions and wording
variants. Canonical exports retain their existing reviewed binding/group checks;
this external diagnostic never relaxes them. Resolve grouped partitions before
reviewed export and explicit training/run authority.

Compatibility: local Python 3.11+ CLI, standard library only. Fictional regressions
cover transitive bridges, disjoint-group limits, long chains, deterministic output,
validation, exact input binding and unchanged input files. Native host integration
and automatic semantic grouping are unsupported.

## Hướng dẫn ngắn

Khai báo nhóm nhà tuyển dụng/dự án dùng chung cho từng ví dụ. Lệnh tìm các nhóm
liên thông nằm ở nhiều tập dữ liệu; không tự suy luận nhóm, sửa dữ liệu hay phê
duyệt huấn luyện. Không có cảnh báo không đồng nghĩa với đánh giá độc lập. Giữ
dữ liệu và báo cáo bên ngoài Git.
