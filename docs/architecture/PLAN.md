# 🏗️ PLAN.md — Windows Hardware Diagnostics & Optimization Web Tool Architecture

> **Author:** Claude Code (Master Orchestrator & Principal Windows Systems Architect)  
> **Status:** Consolidated & Approved by Claude Code & Codex CLI (v1.1)  
> **Target Path:** `F:\AI PROJECTS\HardwareOptimizer\`

---

## 1. Executive Summary & Architectural Goals

The **Windows Hardware Diagnostics & Optimization Web Tool** is an evidence-based, hardware-adaptive performance management suite for Windows 10/11. It discovers system capabilities across 5 subsystems (CPU, GPU, RAM, Storage, Power/Thermal), evaluates current configurations against verified performance baselines, queries `glm-5.3-flash` (via OpenCode Go API) for intelligent Arabic prioritization, and executes reversible optimizations through an elevated safety boundary.

---

## 2. High-Level Architecture & Trust Boundaries

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           LOCAL BROWSER (UI)                                │
│       React 18 + Vite + TypeScript + Tailwind CSS (RTL Arabic First)         │
│  - Live Telemetry Charts (CPU/GPU/RAM/Disk)                                 │
│  - Diagnostics Cards & Bottleneck Evidence                                  │
│  - Recommendations (Diff, Risk Tier, GLM Arabic Analysis)                   │
│  - Session Token Header Injection (`X-Session-Token: <token>`)              │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │ HTTP / WebSocket (127.0.0.1 ONLY)
                                       │ Strict CORS & CSRF Token Validation
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                    FASTAPI BACKEND (Non-Elevated / User Space)              │
│  - Host: 127.0.0.1 (Strict rejection of 0.0.0.0 / DNS rebinding)            │
│  - Startup: Generates Cryptographically Secure Session Token                │
│  - Telemetry Engine: psutil + CIM/WMI Read-Only Bridge                      │
│  - Deterministic Rules Engine: Evaluates inventory -> Candidate Actions     │
│  - OpenCode Go LLM Client: Formats candidates -> GLM-5.3-Flash -> Explains  │
│  - SQLite Session & Metrics Database: Pre/Post benchmarks & rollback logs   │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │ One-way IPC Pipe / Process Spawn
                                       │ Triggered ONLY on explicit "Apply"
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                 ELEVATED HELPER PROCESS (UAC Admin Boundary)                │
│  - Executed via `runas` with UAC prompt only when applying Tier 1/2 changes │
│  - Accepts ONLY validated `action_id`s from strict hardcoded Allowlist      │
│  - Pre-execution Hook: Creates System Restore Point & JSON State Backup     │
│  - Reversible Execution: Implements atomic Apply and 1-Click Rollback       │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Technology Stack Selection

### Backend
* **Runtime:** Python 3.12 (Native Windows execution).
* **Framework:** FastAPI + Uvicorn (async high-throughput REST & SSE/WebSocket).
* **Data Validation:** Pydantic v2 (Strict schema enforcement for inventory, candidates, and LLM responses).
* **System Telemetry:** `psutil` (real-time CPU/RAM/Disk stats) + PowerShell CIM Bridge (`Get-CimInstance`).
* **Storage:** SQLite 3 (WAL mode) for session history, metrics snapshots, and rollback states.
* **LLM Client:** `httpx` asynchronous client communicating with OpenCode Go OpenAI-compatible endpoint.

### Frontend
* **Build Tool:** Vite 5 (instant HMR and fast production bundling).
* **Framework:** React 18 + TypeScript (Strict null checks).
* **Styling & RTL:** Tailwind CSS with native RTL direction (`dir="rtl"`), supporting Dark and Light modes.
* **Visualization:** Chart.js / Recharts for real-time telemetry streaming (CPU cores, GPU memory, disk latency).
* **Icons:** `lucide-react`.

### Packaging & Execution
* **Launch Script:** `start.ps1` and `start.bat`:
  1. Activates virtual environment (`venv`).
  2. Spawns FastAPI backend bound strictly to `127.0.0.1:<PORT>`.
  3. Generates session token and launches default browser to `http://127.0.0.1:<PORT>/?token=<token>`.

---

## 4. Subsystem Telemetry & Deterministic Rules Engine

### The Separation of Concerns Mandate
The LLM **never** decides *what* can be modified on the system.
1. **Collector Layer:** Queries CIM/WMI/PowerShell, extracts raw telemetry, and sanitizes identifiers.
2. **Rules Engine (Deterministic Python):** Tests raw metrics against the `HARDWARE_KB.md` rules and outputs a list of `CandidateAction` objects matching valid `action_id`s.
3. **LLM Explainer (`glm-5.3-flash`):** Receives sanitized inventory and candidates. Returns formatted Arabic explanations, impact justifications, and priority rankings.
4. **Safety Filter:** Discards any output from the LLM containing unknown `action_id`s or commands.

---

## 5. Security & Threat Modeling

| Threat Vector | Attack Scenario | Architectural Defense |
| :--- | :--- | :--- |
| **DNS Rebinding & Localhost Hijacking** | Malicious website in user's browser attempts to call `http://127.0.0.1:8000/api/apply`. | 1. FastAPI binds strictly to `127.0.0.1` (never `0.0.0.0`).<br>2. Validates `Host` header (`localhost` or `127.0.0.1` only).<br>3. Every state-altering API request requires `X-Session-Token` generated at boot and stored in memory. |
| **Prompt Injection / Jailbreak via LLM** | Adversarial telemetry or hijacked LLM response outputs malicious PowerShell strings. | 1. LLM output schema allows **ONLY** `action_id` (string from Enum), `priority` (int), and `rationale_arabic` (string).<br>2. No shell code, PowerShell strings, or script blocks are ever accepted or executed from LLM output. |
| **Privilege Escalation** | Compromised web process executing arbitrary administrative commands. | 1. Web backend runs entirely in **standard user context** (non-admin).<br>2. Administrative operations isolated to `elevated_helper.py` triggered via UAC only when user clicks "Apply".<br>3. Helper validates arguments against the compiled allowlist before executing. |
| **Accidental System Brick** | Bad configuration leads to boot failure or device instability. | 1. Tier 3 strictly prohibited.<br>2. Automatic System Restore Point before any Tier 1/Tier 2 apply.<br>3. Prior state serialized to `sessions/<id>/state_backup.json` for 1-click rollback. |

---

## 6. API Contracts & Pydantic Schemas

### 6.1 Telemetry Live Endpoint: `GET /api/telemetry/live`
```json
{
  "timestamp": 1793527000,
  "cpu": {
    "total_percent": 14.2,
    "per_core": [12.0, 18.5, 9.1, 15.2, 11.0, 19.3],
    "frequency_mhz": 2592
  },
  "ram": {
    "total_bytes": 16963534848,
    "available_bytes": 1403952000,
    "used_percent": 91.7
  },
  "gpu": [
    {
      "name": "NVIDIA GeForce GTX 1650",
      "vram_used_bytes": 1288490188,
      "vram_total_bytes": 4293918720,
      "utilization_percent": 22
    }
  ],
  "disk_io": {
    "read_bytes_sec": 1048576,
    "write_bytes_sec": 524288
  }
}
```

### 6.2 Recommendations Endpoint: `POST /api/recommendations/analyze`
* Input: Triggered after full scan.
* Output:
```json
{
  "session_id": "sess_20261101_1308",
  "health_scores": {
    "overall": 78,
    "cpu": 85,
    "gpu": 80,
    "ram": 75,
    "storage": 82,
    "power": 70
  },
  "recommendations": [
    {
      "action_id": "STORAGE_ENABLE_TRIM",
      "subsystem": "Storage",
      "tier": 1,
      "title_ar": "تفعيل بروتوكول TRIM لأقراص NVMe/SSD",
      "current_value": "Disabled",
      "proposed_value": "Enabled",
      "priority": 1,
      "rationale_ar": "يساعد تفعيل بروتوكول TRIM على استعادة كتل الذاكرة غير المستخدمة في قرص ADATA NVMe، مما يطيل عمر خلايا NAND ويحافظ على سرعة الكتابة القصوى.",
      "rollback_summary_ar": "يمكن التراجع بإعادة تعيين قيمة DisableDeleteNotify إلى 1.",
      "requires_admin": true,
      "requires_reboot": false
    }
  ]
}
```

---

## 7. Elevated Helper Architecture & IPC

```python
# Pseudo-code architecture for elevated_helper.py
class ElevatedActionHandler:
    ALLOWLIST = {
        "STORAGE_ENABLE_TRIM": {
            "apply": ["fsutil", "behavior", "set", "DisableDeleteNotify", "0"],
            "rollback": ["fsutil", "behavior", "set", "DisableDeleteNotify", "1"]
        },
        "GPU_ENABLE_HAGS": {
            "apply": ["reg", "add", r"HKLM\SYSTEM\CurrentControlSet\Control\GraphicsDrivers", "/v", "HwSchMode", "/t", "REG_DWORD", "/d", "2", "/f"],
            "rollback": ["reg", "add", r"HKLM\SYSTEM\CurrentControlSet\Control\GraphicsDrivers", "/v", "HwSchMode", "/t", "REG_DWORD", "/d", "1", "/f"]
        }
    }
```

The helper verifies the hash of the action request file, executes the predefined command list via direct executable path without string shell interpolation, and writes execution evidence to `sessions/<id>/audit.jsonl`.
