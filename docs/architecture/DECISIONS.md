# 📋 DECISIONS.md — Architectural Decision Records (ADRs)

> **Project:** Windows Hardware Diagnostics & Optimization Web Tool (`HardwareOptimizer`)  
> **Governance:** FLEET_WORKFLOW §3 (Consensus Ratification)

---

### ADR-001: Async 3.0s Timeout Envelopes for WMI/CIM Collectors
* **Context:** Hardware queries on Windows can block indefinitely if ACPI or storage drivers are unresponsive.
* **Decision:** All telemetry collection functions must be wrapped in `asyncio.wait_for(..., timeout=3.0)`.
* **Consequences:** Eliminates UI freezing. If a metric fails or times out, the system returns a graceful fallback status (`"unavailable"`).

---

### ADR-002: Shell-Free Binary Execution in Elevated Helper
* **Context:** Running scripts via `cmd.exe /c` or PowerShell script interpretation allows argument injection risks.
* **Decision:** The elevated helper must execute compiled system binaries directly via `subprocess.run(args, shell=False)` targeting exact paths (`C:\Windows\System32\fsutil.exe`, `C:\Windows\System32\reg.exe`).
* **Consequences:** Zero shell interpolation. Only hardcoded, static argument lists from the verified allowlist are permitted.

---

### ADR-003: Single-Origin Pre-Bundled Frontend Serving
* **Context:** Multi-port development setups (port 5173 for Vite and 8000 for FastAPI) expose cross-origin attack vectors on localhost.
* **Decision:** The Vite React frontend is pre-bundled into `dist/` and served directly by FastAPI as static files on `127.0.0.1:<PORT>`.
* **Consequences:** CORS headers are locked down to same-origin. Localhost attacks from external browser tabs are completely blocked.

---

### ADR-004: Dual-Layer Reboot-Resilient Rollback Engine
* **Context:** Tier 2 settings (such as HAGS) require a system reboot. If an issue occurs post-reboot, in-memory state is lost.
* **Decision:** Maintain immutable state snapshots in SQLite (WAL mode) and `sessions/<session_id>/state_backup.json`, accompanied by a headless CLI command `python -m optimizer rollback --session <id>`.
* **Consequences:** Rollback is 100% reliable even from Windows Safe Mode or without running the web browser.

---

### ADR-005: Deterministic Rules Engine with Strict Schema Filtering
* **Context:** Relying on LLMs to generate system commands creates catastrophic safety risks.
* **Decision:** The deterministic Python rules engine generates all candidates from `HARDWARE_KB.md`. The LLM (`glm-5.3-flash`) only receives candidates, prioritizes them, and generates Arabic explanations. Any output from the LLM containing an unknown `action_id` is automatically discarded.
* **Consequences:** Zero arbitrary code execution from AI models. 100% predictable system modifications.

---

### ADR-006: Mandatory System Restore Point Before Tier 1/2 Apply
* **Context:** Users must have an operating system level safety net before hardware/driver configurations change.
* **Decision:** An automated Windows System Restore Point must be generated via `Checkpoint-Computer` prior to applying any changes.
* **Consequences:** Provides disaster recovery through Windows Recovery Environment (WinRE) if hardware becomes unresponsive.
