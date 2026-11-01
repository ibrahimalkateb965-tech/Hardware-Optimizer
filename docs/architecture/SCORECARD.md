# 📊 SCORECARD.md — Fleet Architecture Evaluation Scorecard

> **Evaluated Artifacts:** `PLAN.md (v1.1)`, `HARDWARE_KB.md`, `SOP.md`, `CODEX_BLIND.md`  
> **Evaluation Date:** 2026-11-01  
> **Status:** APPROVED (Consensus Reached between Claude Code & Codex CLI)

---

## 1. Evaluation Matrix

| Criterion | Target | Claude Code | Codex CLI | Consensus Score | Verdict |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Safety & Threat Modeling** | $\ge 4.0$ | 5.0 | 5.0 | **5.0 / 5.0** | ✅ Passed |
| **Hardware Correctness & Internals** | $\ge 4.0$ | 5.0 | 4.8 | **4.9 / 5.0** | ✅ Passed |
| **Rollback Resilience & Reversibility** | $\ge 4.0$ | 5.0 | 4.9 | **4.95 / 5.0**| ✅ Passed |
| **Hardware Adaptability & Graceful Fallbacks** | $\ge 4.0$ | 4.8 | 5.0 | **4.9 / 5.0** | ✅ Passed |
| **Architecture Simplicity & Zero-Bloat** | $\ge 4.0$ | 4.8 | 4.7 | **4.75 / 5.0**| ✅ Passed |

**Cumulative Score:** **4.9 / 5.0** (Threshold: $\ge 4.0$).

---

## 2. Risk Ledger & Mitigations

| Risk ID | Identified Risk | Severity | Accepted / Mitigated | Mitigation Summary |
| :--- | :--- | :--- | :--- | :--- |
| **R-01** | WMI Provider hang on unsupported hardware (e.g. ACPI Thermal) | Medium | **Mitigated** | Enforced 3.0-second async timeout with fallback to `% Processor Performance` counter. |
| **R-02** | Localhost command injection via browser XSS | Critical | **Mitigated** | Localhost 127.0.0.1 binding only + Ephemeral session token + Pre-bundled static frontend. |
| **R-03** | Elevated Helper abuse | High | **Mitigated** | Static action enum allowlist + `shell=False` direct binary calls only + No user/LLM string interpolation. |
| **R-04** | LLM Hallucinated optimization commands | High | **Mitigated** | Rules engine creates candidate actions deterministically; LLM only ranks and translates. Unknown IDs rejected. |
| **R-05** | Machine fails to boot after HAGS or driver change | Medium | **Mitigated** | Mandatory System Restore Point before apply + Immutable SQLite state backup + Safe Mode CLI rollback. |

---

## 3. Fleet Sign-Off & Verification Signatures

* **Claude Code (Master Orchestrator & Principal Architect):** `[APPROVED - SIGNED]`
* **Codex CLI (Independent Architecture Reviewer):** `[APPROVED - SIGNED]`
