# 📖 SOP.md — Standard Operating Procedure: Windows Hardware Diagnostics & Optimizer

> **Standard Operating Procedure (SOP)**  
> Operational governance for running diagnostics, applying optimizations, executing rollbacks, and handling emergencies.

---

## 1. Prerequisites & Environment Setup

1. **Operating System:** Windows 10 (Build 19041+) or Windows 11 (64-bit).
2. **Runtime:** Python 3.12+ 64-bit and Node.js 20+ (for frontend bundle).
3. **API Configuration:**
   - Copy `.env.example` to `.env`:
     ```bash
     cp .env.example .env
     ```
   - Provide your valid `OPENCODE_GO_API_KEY`.
   - Default endpoints and models are pre-calibrated:
     ```env
     OPENCODE_GO_BASE_URL=https://opencode.ai/inference/go/openai/v1
     OPENCODE_GO_MODEL=glm-5.3-flash
     HOST=127.0.0.1
     PORT=8000
     ```

---

## 2. Standard Startup & Web UI Access

1. **Launch:** Run the one-click startup script:
   ```cmd
   start.bat
   ```
   *Or via PowerShell:*
   ```powershell
   .\start.ps1
   ```
2. **Execution Flow:**
   - The script initializes the Python virtual environment (`.venv`), installs dependencies if missing, compiles the frontend bundle, and binds FastAPI strictly to `127.0.0.1:8000`.
   - An ephemeral session token is generated.
   - The default web browser automatically launches to `http://127.0.0.1:8000/?token=<SESSION_TOKEN>`.
   - **Binding Safety:** The server will refuse connection attempts from remote IP addresses or unbound domain names.

---

## 3. Routine Diagnostics & Review (Read-Only)

1. **Step 1 — Dashboard Overview:**
   - Review live telemetry (CPU Core loads, GPU VRAM usage, Physical RAM consumption, and Disk I/O).
   - Inspect Subsystem Health Scores (0 to 100).
2. **Step 2 — Diagnostics Tab:**
   - View hardware inventory detected across CPU, GPU, RAM, Storage, and Power.
   - Examine identified bottlenecks with specific technical evidence (e.g., "Pagefile located on spinning HDD ST1000LM035 instead of NVMe SSD").
3. **Step 3 — Recommendations Tab:**
   - Review actionable optimizations ranked by impact and safety tier.
   - Read the AI-generated Arabic explanation (`glm-5.3-flash`) explaining *why* this optimization was recommended for your specific device.
   - Inspect the explicit Diff (Current Configuration $\rightarrow$ Proposed Configuration).

---

## 4. The Optimization Workflow (Apply Protocol)

> [!IMPORTANT]  
> All optimizations require deliberate user opt-in. Zero changes occur automatically.

1. **Selection:**
   - Select individual optimization checkboxes, or click **"Select Recommended Tier 1 (Safe)"**.
   - Note that Tier 2 optimizations (e.g., HAGS, service changes requiring reboot) must be checked individually.
2. **Apply Trigger:**
   - Click the **"مراجعة وتطبيق التحسينات (Review & Apply)"** button.
   - A modal displays the summary of changes, estimated duration, and safety checkpoints.
3. **Automated Safety Gate (Prior to Execution):**
   - The system triggers an automated **Windows System Restore Point**:
     `Checkpoint-Computer -Description "HardwareOptimizer_PreApply_<SessionID>" -RestorePointType "MODIFY_SETTINGS"`
   - A JSON snapshot of the original settings is saved to `sessions/<session_id>/state_backup.json`.
4. **Elevation (UAC):**
   - If any selected action requires administrative privileges, the system triggers the Windows UAC dialog for `elevated_helper.exe`.
   - Accept the prompt to complete the action.
5. **Post-Apply Verification:**
   - The UI re-scans active telemetry and displays the **Before / After** comparison metrics (idle CPU/RAM, latency).

---

## 5. Rollback Protocols

### Method A: One-Click Web UI Rollback (Standard)
1. Navigate to the **"سجل الجلسات والتراجع (History & Rollback)"** tab.
2. Locate the relevant optimization session.
3. Click **"تراجع عن هذه الجلسة (Rollback Session)"** or choose granular rollback for specific actions.
4. The system executes the inverse commands from the session's `state_backup.json` and verifies restoration.

### Method B: Emergency CLI Rollback (Headless)
If the web UI is inaccessible, run the emergency rollback command directly in PowerShell or Command Prompt:
```cmd
python -m optimizer rollback --session latest
```
*Or target a specific session:*
```cmd
python -m optimizer rollback --session sess_20261101_1308
```

---

## 6. Emergency Recovery & Disaster Protocol

### Scenario 1: Windows Fails to Boot or Freezes After Reboot
1. Power cycle the PC. During boot, trigger the **Windows Recovery Environment (WinRE)** (Hold Shift while clicking Restart, or interrupt boot twice).
2. Select: **Troubleshoot (استكشاف الأخطاء وإصلاحها)** $\rightarrow$ **Advanced Options (خيارات متقدمة)** $\rightarrow$ **System Restore (استعادة النظام)**.
3. Select the restore point labeled:
   `HardwareOptimizer_PreApply_<SessionID>`.
4. Confirm restoration. Windows will revert registry hives and driver configurations to the exact millisecond prior to optimization.

### Scenario 2: OpenCode Go API Downtime / Timeout
- If `opencode.ai` experiences network interruption or rate limits (HTTP 429/500/503), the web tool initiates **Graceful Degradation**:
  - The deterministic rules engine continues to function at 100% fidelity.
  - The recommendations list displays local pre-compiled Arabic explanations.
  - The UI presents a subtle banner: `"تم تشغيل الوضع المحلي للتحسينات (API غير متصل مؤقتاً)"`. Zero disruption to core diagnostic or apply capabilities.
