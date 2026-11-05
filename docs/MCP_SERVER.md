# Run the career MCP server from your fork

Connect your tool-enabled AI host to one private workspace for source-cited CV
and professional-email preparation. This is a source-checkout distribution,
not a hosted service or a published Python package. Python 3.11+ is required.
Docker, Gmail, Chromium and another model API are not required.

## 1. Install the minimal optional environment

Clone your fork, open its directory and create a dedicated environment. Keep
the standard-library core independent of these optional dependencies.

Windows PowerShell:

```powershell
python -m venv .venv-mcp
.venv-mcp/Scripts/python.exe -m pip install --require-hashes --only-binary=:all: -r requirements-mcp.lock
.venv-mcp/Scripts/python.exe scripts/check_career_mcp.py
```

Linux/macOS shell:

```sh
python3 -m venv .venv-mcp
.venv-mcp/bin/python -m pip install --require-hashes --only-binary=:all: -r requirements-mcp.lock
.venv-mcp/bin/python scripts/check_career_mcp.py
```

The check creates and removes disposable fictional data. It tests an actual
stdio handshake, 20-tool inventory, retrieval, a CV brief, policy resource and
invalid input. It does not install host settings or submit an application.
The SDK is pinned to **mcp 1.30.0**; do not silently substitute SDK v2.

## 2. Prepare your own workspace

Follow [CV-first setup](COMMUNITY_START.md) to initialize a private directory
outside the checkout, import checked evidence, confirm candidate facts and
record a job. For example, the intake command is:

```sh
python scripts/kit.py --data-dir ../my-career-private start-campaign --cv /path/to/my-cv.pdf
```

Intake does not extract or confirm CV claims. Complete those steps before asking
for a source-bound writing brief. Never use the fictional demo as your tracker.
If your older campaign has `applications.sqlite3` instead of `workflow.sqlite3`,
use the [source-memory bridge](SOURCE_MEMORY.md). This launcher refuses to
initialize or migrate a second tracker over it.

## 3. Check and preview the host configuration

Use your environment's Python command from step 1 in place of `python` below:

```sh
python scripts/career_mcp.py --data-dir ../my-career-private --check
python scripts/career_mcp.py --data-dir ../my-career-private --config json
python scripts/career_mcp.py --data-dir ../my-career-private --config codex
```

Both previews contain the actual absolute interpreter, checkout and workspace
paths, including correctly quoted spaces. `--python PATH` overrides only the
interpreter in a configuration preview. Review it, then add the selected entry
through your host's normal local MCP configuration. The previews never edit
global settings. Restart/reconnect the host as its documentation requires.

The host launches this command and owns its lifetime:

```sh
python scripts/career_mcp.py --data-dir ../my-career-private
```

In server mode stdout is reserved for MCP; setup errors are JSON on stderr.
`--check` prints its JSON on stdout and exits 2 for unavailable/mismatched SDKs
or rejected workspaces. A config preview alone does not verify your workspace
or prove native discovery in Codex, Claude Code or another host.

## 4. Use the existing tools

Ask the host to call `career_context` for relevant confirmed facts, then
`career_writing_brief` for a recorded job and `career_check_draft` for the
resulting source-bound draft. Use `campaign_tracker` and `performance_report`
to read existing progress and observed usage. Reviewed learning export and
career-growth tools reuse the same core; see [career memory](CAREER_MEMORY.md).

This server does not send email, control browsers, train models or grant
submission authority. It exposes local preparation operations, including
private sidecar/export writes; it is not a read-only sandbox. Stdio is a local
process boundary, not user authentication. Connect only a trusted host with
access to the selected private workspace. Any remote model used by that host
may receive returned facts: review your host/provider privacy choices first.

## Troubleshooting and evidence scope

- Missing SDK/version mismatch: use the environment from step 1, not another
  globally installed Python. Run `python -m pip check` in that environment.
- Missing/uninitialized workspace: finish intake explicitly; startup never
  creates a campaign or changes a database schema.
- Corrupt/unsupported database: preserve it and inspect/recover a backup.
  Do not delete it or reset historical counters to make preflight pass.
- Checkout moved or environment recreated: regenerate the previews; old
  absolute paths will be stale. Keep private data outside Git during upgrades.
- An existing full plugin setup remains supported; do not register both entries
  for the same workspace unintentionally. See [local plugins](LOCAL_PLUGINS.md).

Local Windows Python 3.12 acceptance covers the clean minimal dependency profile
and real SDK protocol. CI targets Windows/Linux Python 3.11/3.12. macOS and
native host discovery remain unverified until separately exercised. A passing
handshake does not establish semantic CV quality or improved hiring outcomes.

## Hướng dẫn ngắn bằng tiếng Việt

Fork/clone kit, tạo `.venv-mcp`, cài `requirements-mcp.lock` rồi chạy
`scripts/check_career_mcp.py` như bước 1. Chuẩn bị workspace riêng ngoài Git
theo [hướng dẫn bắt đầu](COMMUNITY_START.md), xác nhận dữ kiện CV và nhập JD.
Chạy `--check`, tạo bản cấu hình `--config json` hoặc `--config codex`, kiểm tra
đường dẫn rồi tự thêm vào AI host. Không cần Docker hay API mô hình thứ hai.
MCP hỗ trợ truy xuất bằng chứng và chuẩn bị CV/email; gửi hồ sơ, quyền tiết lộ
dữ liệu và huấn luyện vẫn là các bước riêng. Không đưa CV hoặc tracker cá nhân
lên fork công khai.
