# 🚀 RELEASE_NOTES.md — Version 1.0.0 (Initial Production Release)

> **Release Version:** 1.0.0  
> **Release Date:** 2026-11-01  
> **Target Platform:** Windows 10 / Windows 11 (64-bit)  
> **Architecture Governance:** Autovemtech Multi-CLI Fleet (Hook 31)

---

## 🌟 Major Highlights & New Features

### 1. Hardware-Adaptive Multi-Subsystem Telemetry
* Full discovery across 5 subsystems: CPU, GPU (iGPU + dGPU), RAM, Storage (NVMe/SSD/HDD), and Power/Thermal.
* Built-in asynchronous worker pool enforcing strict 3.0s timeout envelopes against WMI/CIM providers.
* Automated sanitization of user personal data, GUIDs, and drive serial numbers.

### 2. Deterministic Rules Engine with Zero-Snake-Oil Enforcement
* Mathematical rules engine mapping telemetry strictly against Microsoft Windows Internals documentation.
* Complete prohibition of snake-oil practices (disabling pagefile, aggressive RAM cleaners, and defragmenting SSDs).
* Classification into Risk Tiers: Tier 0 (Report-only), Tier 1 (Low-risk reversible), Tier 2 (Confirm each), and Tier 3 (Forbidden).

### 3. OpenCode Go API (`glm-5.3-flash`) Integration
* High-speed, multimodal LLM client providing contextual Arabic explanations and priority rankings (1-10).
* Hardened schema validation: any hallucinated `action_id` outside the candidate list is dropped.
* Zero-downtime graceful degradation: operates locally if API key is absent or network fails.

### 4. Elevated Helper & UAC Security Boundary
* Separation of concerns: FastAPI backend runs in standard user space (bound to `127.0.0.1` only).
* Administrative modifications executed via an elevated helper process triggered only upon explicit user confirmation.
* Direct system binary execution (`shell=False`) for `fsutil.exe`, `reg.exe`, and `powercfg.exe`.
* Automated Windows System Restore Point creation prior to any system modification.

### 5. Dual-Layer Rollback Engine
* 1-Click Rollback directly from the web interface.
* Headless standalone CLI rollback command: `python -m backend.cli_rollback --session latest` for emergency recovery.
* SQLite WAL state ledger tracking all optimization sessions and Before/After metrics diffs.

### 6. Modern Responsive RTL Web Interface
* Tailored for Arabic RTL reading flow with English technical terms preserved.
* Live streaming telemetry charts for CPU core utilization, RAM allocation, and disk throughput.
* Clean 6-tab navigation: Dashboard, Diagnostics, Recommendations, Apply, Before/After, and History.

---

## 🛠️ Verification & Quality Assurance Summary
* **Unit & Integration Tests:** 100% green coverage on rules engine, allowlist dispatch, and state ledger.
* **Security Audit:** Rejection of localhost DNS rebinding, prompt-injection defense verified, and session token enforcement.
* **Sandbox Testing:** Validated against synthetic hardware profiles (Dell G3 laptop, misconfigured desktop, SSD-only, and thermal-missing systems).
