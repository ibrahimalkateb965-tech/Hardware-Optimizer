# 📋 TASKS.md — Task Breakdown & Fleet Assignment Matrix

> **Project:** Windows Hardware Diagnostics & Optimization Web Tool (`HardwareOptimizer`)  
> **Status:** APPROVED BY IBRAHIM (Gate 3 Cleared)  
> **Governance:** FLEET_WORKFLOW §4

---

## 1. Task Breakdown Matrix

| Task ID | Task Description | Assigned Role | Dependencies | Status | Acceptance Criteria |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **TASK-01** | **Core Backend Scaffolding & Security Foundation** | OpenCode CLI | None | Pending | FastAPI app, Pydantic v2 schemas, `.env` loader, ephemeral session token, strict 127.0.0.1 binding. |
| **TASK-02** | **Async Hardware Telemetry Collectors (WMI/CIM/psutil)** | OpenCode CLI | TASK-01 | Pending | 5 Subsystems collected; 3.0s async timeout envelopes; PII redaction; Sandbox fake adapter. |
| **TASK-03** | **Deterministic Rules Engine & Candidate Generator** | Antigravity IDE | TASK-01 | Pending | Pure function mapping inventory to `CandidateAction` allowlist; zero LLM dependency. |
| **TASK-04** | **OpenCode Go Client (`glm-5.3-flash`) & Arabic Explainer** | OpenCode CLI | TASK-01, TASK-03 | Pending | Async httpx client; structured JSON output validation; graceful local degradation on failure. |
| **TASK-05** | **Elevated Helper Daemon & Security Boundary** | OpenCode CLI | TASK-01 | Pending | UAC elevation; static allowlist dispatch; `shell=False` binary execution; Restore Point trigger. |
| **TASK-06** | **SQLite State Ledger & Dual Rollback Engine** | OpenCode CLI | TASK-05 | Pending | SQLite WAL session ledger; Before/After metrics diff; Web 1-click & headless CLI rollback. |
| **TASK-07** | **React Frontend (Vite + TypeScript + Tailwind RTL)** | Antigravity IDE | TASK-01, TASK-02, TASK-04 | Pending | 6 Pages (Dashboard, Diagnostics, Recommendations, Apply, Rollback, Before/After); RTL Arabic. |
| **TASK-08** | **Automated Test Suites & Security Verification** | Claude Code CLI | TASK-01 to TASK-07 | Pending | $\ge 80\%$ core coverage; 100% helper/allowlist coverage; prompt-injection tests; security audit. |
| **TASK-09** | **Packaging, One-Click Launchers & User Guide** | Antigravity IDE | TASK-07, TASK-08 | Pending | `start.bat`, `start.ps1`, `USER_GUIDE.md`, and `RELEASE_NOTES.md`. |

---

## 2. Detailed Task Specifications

### TASK-01: Core Backend Scaffolding & Security Foundation
* **Files:** `backend/main.py`, `backend/config.py`, `backend/security.py`, `backend/schemas.py`.
* **Criteria:**
  - Fast startup on `127.0.0.1:<PORT>`.
  - Rejects any connection where `Host` header does not match localhost.
  - Generates a 32-byte cryptographic session token at startup, requiring `X-Session-Token` for non-GET endpoints.

### TASK-02: Async Hardware Telemetry Collectors
* **Files:** `backend/collectors/base.py`, `backend/collectors/cpu.py`, `backend/collectors/gpu.py`, `backend/collectors/ram.py`, `backend/collectors/storage.py`, `backend/collectors/power.py`, `backend/collectors/sandbox.py`.
* **Criteria:**
  - Every query wrapped in `asyncio.wait_for(..., timeout=3.0)`.
  - Automated redaction of usernames, serial numbers, and MAC addresses.
  - Sandbox mode returns deterministic mock profiles for testing without Windows dependencies.

### TASK-03: Deterministic Rules Engine
* **Files:** `backend/rules/engine.py`, `backend/rules/definitions.py`.
* **Criteria:**
  - Evaluates inventory against rules defined in `HARDWARE_KB.md`.
  - Generates candidate list where every item has an `action_id` strictly present in the allowlist.

### TASK-04: OpenCode Go Client (`glm-5.3-flash`)
* **Files:** `backend/ai/client.py`, `backend/ai/prompts.py`.
* **Criteria:**
  - Calls `https://opencode.ai/inference/go/openai/v1/chat/completions`.
  - Model: `glm-5.3-flash`.
  - Drops any output item whose `action_id` was not in the candidate list.
  - Falls back to local pre-compiled explanations on network timeout or HTTP errors.

### TASK-05: Elevated Helper Daemon
* **Files:** `backend/helper/elevated_helper.py`, `backend/helper/allowlist.py`.
* **Criteria:**
  - Direct execution via `subprocess.run(args, shell=False)`.
  - Pre-execution triggers Windows System Restore Point.
  - Saves pre-execution state to `sessions/<session_id>/state_backup.json`.

### TASK-06: SQLite State Ledger & Rollback
* **Files:** `backend/db/ledger.py`, `backend/cli_rollback.py`.
* **Criteria:**
  - SQLite in WAL mode.
  - Headless CLI rollback: `python -m backend.cli_rollback --session <id>`.

### TASK-07: React Frontend Development
* **Files:** `frontend/` (Vite, React 18, TypeScript, Tailwind CSS, Lucide icons, Chart.js).
* **Criteria:**
  - Clean RTL Arabic interface with English technical terms.
  - Telemetry charts streaming real-time metrics.
  - Full flow: Scan $\rightarrow$ Diagnostics $\rightarrow$ Recommendations $\rightarrow$ Apply $\rightarrow$ Before/After $\rightarrow$ Rollback.

### TASK-08: Test Suite (Claude Code Sole Test Authority)
* **Files:** `tests/test_rules.py`, `tests/test_collectors.py`, `tests/test_helper.py`, `tests/test_ai_client.py`, `tests/test_security.py`.
* **Criteria:**
  - 100% green tests; coverage $\ge 80\%$.
  - Prompt injection attack payloads successfully rejected.

### TASK-09: Packaging & User Deliverables
* **Files:** `start.bat`, `start.ps1`, `USER_GUIDE.md`, `RELEASE_NOTES.md`.
* **Criteria:**
  - Single double-click execution on Windows.
  - Comprehensive documentation in Arabic.
