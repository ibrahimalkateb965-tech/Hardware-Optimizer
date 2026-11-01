# 📚 HARDWARE_KB.md — Windows Hardware Diagnostics & Optimization Knowledge Base

> **Canonical Knowledge Base for Windows Hardware Optimization**  
> Strictly evidence-based, verified against official Microsoft Windows Internals, MSDN, and hardware vendor documentation.  
> **Zero Snake-Oil Policy**: Undocumented registry hacks, RAM flushers, and disabling critical safety subsystems (like pagefile or Windows Defender) are strictly prohibited.

---

## 1. Core Principles & Anti-Snake-Oil Manifesto

Modern operating systems (Windows 10/11) implement sophisticated kernel scheduling, virtual memory management, and power arbitration. Misguided optimizations degrade stability and longevity.

### 🚫 Rejected Myths & Forbidden Actions (Tier 3)
1. **Disabling the Pagefile (`pagefile.sys`):**
   * *Myth:* "I have 16GB/32GB RAM, so I don't need a pagefile and it saves SSD writes."
   * *Reality:* Windows memory manager uses the pagefile not just when RAM is exhausted, but to back modified pages, store crash dumps (BSOD diagnostics), and page out inactive working sets to keep active working sets in physical RAM. Disabling it triggers commit limit exhaustion, `STATUS_COMMITMENT_LIMIT`, and unpredictable app crashes (e.g., Photoshop, heavy IDEs, game engines).
   * *Rule:* Never disable the pagefile. Ensure it is system-managed or properly sized on the fastest SSD.
2. **Aggressive "RAM Cleaners / Memory Optimizers":**
   * *Myth:* "Emptying standby memory speeds up the PC."
   * *Reality:* Standby memory is cached data ready for instant reuse. Purging it forces the CPU to reload files from disk storage (causing disk spikes and latency micro-stutters). The Windows memory manager automatically repurposes standby memory when free pages are requested.
3. **Disabling Windows Security / Defender / SmartScreen / UAC:**
   * *Myth:* "Antivirus slows down gaming and coding."
   * *Reality:* Unacceptable risk boundary. High-performance developer systems require secure execution environments.
4. **Arbitrary Registry "TCP/IP or Registry Cleaners":**
   * *Myth:* Deleting old registry keys or tweaking arbitrary DWORDs accelerates performance.
   * *Reality:* Registry size has negligible impact on modern SSD/RAM access. Unverified tweaks cause system instability, broken updates, and boot loops.
5. **Defragmenting Solid-State Drives (SSDs / NVMe):**
   * *Reality:* SSDs have near-zero seek times. Running traditional defragmentation wears out NAND flash cells prematurely without performance gains. Only the `ReTrim` command is permitted.

---

## 2. Subsystem Diagnostics & Safe Optimizations Matrix

---

### 🖥️ Subsystem 1: Central Processing Unit (CPU)

#### Item 1.1: Balanced vs. High Performance Power Plan Alignment
* **Detection:**
  ```powershell
  powercfg /getactivescheme
  ```
* **Condition:**
  - On AC power: Desktop or plugged-in laptop needing sustained burst capability.
  - On Battery: Must enforce balanced or power-saver to prevent thermal throttling and battery wear.
* **Apply Command (Tier 1):**
  ```powershell
  # Switch to High Performance when plugged in
  powercfg /setactive 8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c
  ```
* **Rollback Command:**
  ```powershell
  # Restore Balanced (default)
  powercfg /setactive 381b4222-f694-41f0-9685-ff5bb260df2e
  ```
* **Risk Tier:** `Tier 1` (Low-risk, reversible instantly).
* **Expected Impact:** Eliminates CPU frequency ramp-up latency for bursty developer workloads and compilation.
* **Source:** [Microsoft Learn - Processor Power Management Options](https://learn.microsoft.com/en-us/windows-hardware/customize/power-settings/configure-processor-power-management-options)

#### Item 1.2: Startup Application Overhead Pruning
* **Detection:**
  ```powershell
  Get-CimInstance Win32_StartupCommand | Select-Object Name, Command, Location, User
  ```
* **Condition:** Systems with > 10 non-essential background startup agents (e.g., update checkers, third-party assistants) causing boot time inflation and idle CPU contention.
* **Apply Command (Tier 1):**
  ```powershell
  # Disable specific startup item via registry or Task Manager state
  # Requires explicit user selection of action_id
  Set-ItemProperty -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved\Run" -Name "<AppName>" -Value ([byte[]](0x03,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00))
  ```
* **Rollback Command:**
  ```powershell
  Set-ItemProperty -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved\Run" -Name "<AppName>" -Value ([byte[]](0x02,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00))
  ```
* **Risk Tier:** `Tier 1`.
* **Expected Impact:** 15–35% reduction in boot-to-idle duration; saves 300MB–1.2GB RAM and 2–8% background CPU cycles.
* **Source:** [Microsoft Docs - Manage Windows Startup Apps](https://support.microsoft.com/en-us/windows/change-which-apps-run-automatically-at-startup-in-windows-10-b9830de4-4001-7191-ce14-71e9d5d80715)

---

### 🎮 Subsystem 2: Graphics Processing Unit (GPU)

#### Item 2.1: Hardware-Accelerated GPU Scheduling (HAGS)
* **Detection:**
  ```powershell
  (Get-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Control\GraphicsDrivers" -Name "HwSchMode" -ErrorAction SilentlyContinue).HwSchMode
  ```
  *(Value: `2` = Enabled, `1` = Disabled, Missing = Not configured)*
* **Condition:** GPU hardware WDDM 2.7+ (e.g., NVIDIA Pascal GTX 10-series+, Turing GTX 16-series/RTX 20+, Ampere, Ada Lovelace, or AMD RDNA).
* **Apply Command (Tier 2 - Requires Reboot):**
  ```powershell
  Set-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Control\GraphicsDrivers" -Name "HwSchMode" -Value 2 -Type DWord
  ```
* **Rollback Command:**
  ```powershell
  Set-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Control\GraphicsDrivers" -Name "HwSchMode" -Value 1 -Type DWord
  ```
* **Risk Tier:** `Tier 2` (Requires reboot; must confirm user hardware support).
* **Expected Impact:** Offloads high-frequency scheduling tasks from CPU to dedicated GPU scheduling processor, reducing frame time jitter and input latency.
* **Source:** [Microsoft DirectX Developer Blog - Hardware-Accelerated GPU Scheduling](https://devblogs.microsoft.com/directx/hardware-accelerated-gpu-scheduling/)

#### Item 2.2: Application-Specific GPU Preference (Dual-GPU Laptops: iGPU vs dGPU)
* **Detection:**
  ```powershell
  Get-ItemProperty -Path "HKCU:\Software\Microsoft\DirectX\UserGpuPreferences"
  ```
* **Condition:** Laptop equipped with both an integrated GPU (Intel UHD) and discrete GPU (NVIDIA GTX 1650). Heavy IDEs (e.g., Android Studio, Unreal Engine, Blender) defaulting to iGPU.
* **Apply Command (Tier 1):**
  ```powershell
  # Set Discrete GPU preference (GpuPreference=2) for specific application
  Set-ItemProperty -Path "HKCU:\Software\Microsoft\DirectX\UserGpuPreferences" -Name "<AppFullPath>" -Value "GpuPreference=2;"
  ```
* **Rollback Command:**
  ```powershell
  Remove-ItemProperty -Path "HKCU:\Software\Microsoft\DirectX\UserGpuPreferences" -Name "<AppFullPath>"
  ```
* **Risk Tier:** `Tier 1`.
* **Expected Impact:** Massive rendering boost in CAD/3D and GPU-accelerated workloads; avoids discrete GPU power drain for lightweight productivity apps.
* **Source:** [Windows Display Driver Model - GPU Selection Architecture](https://learn.microsoft.com/en-us/windows-hardware/drivers/display/gpu-selection)

---

### 🧠 Subsystem 3: Physical Memory (RAM)

#### Item 3.1: Dual-Channel & Clock Speed Diagnostic
* **Detection:**
  ```powershell
  Get-CimInstance Win32_PhysicalMemory | Select-Object DeviceLocator, Capacity, Speed, ConfiguredClockSpeed, PartNumber
  ```
* **Condition:**
  - Number of modules = 1 (Single channel mode detected).
  - ConfiguredClockSpeed < Speed (e.g. 2933 MHz vs 3200 MHz, or 2133 MHz default vs 3600 MHz XMP).
* **Action:**
  - **No automated command permitted.** XMP/EXPO and physical slot population are strictly BIOS/motherboard level.
* **Risk Tier:** `Tier 0` (Report-only advisory with human guide).
* **Expected Impact:** Enabling Dual-Channel and XMP boosts memory bandwidth by 30–80%, directly improving CPU-bound compilation and gaming frame rates.
* **Source:** [Intel XMP Specification & JEDEC Standard](https://www.intel.com/content/www/us/en/gaming/extreme-memory-profile-xmp.html)

#### Item 3.2: Memory Compression Integrity Check
* **Detection:**
  ```powershell
  (Get-MMAgent).MemoryCompression
  ```
* **Condition:** Memory compression is disabled (`False`), causing premature disk swapping.
* **Apply Command (Tier 2):**
  ```powershell
  Enable-MMAgent -MemoryCompression
  ```
* **Rollback Command:**
  ```powershell
  Disable-MMAgent -MemoryCompression
  ```
* **Risk Tier:** `Tier 2`.
* **Expected Impact:** Keeps inactive pages compressed in RAM at negligible CPU cost, dramatically reducing disk pagefile I/O.
* **Source:** [Microsoft Engineering Blog - Memory Compression in Windows 10](https://blogs.windows.com/windowsexperience/2015/08/18/announcing-windows-10-insider-preview-build-10525/)

---

### 💾 Subsystem 4: Storage & File System

#### Item 4.1: TRIM Protocol Enforcement
* **Detection:**
  ```powershell
  fsutil behavior query DisableDeleteNotify
  ```
  *(Output `0` = Enabled/Permitted; `1` = Disabled)*
* **Condition:** Solid State Drives (NVMe or SATA SSD) where TRIM is disabled (`DisableDeleteNotify = 1`), leading to write amplification and degradation of write speeds over time.
* **Apply Command (Tier 1):**
  ```powershell
  fsutil behavior set DisableDeleteNotify 0
  ```
* **Rollback Command:**
  ```powershell
  fsutil behavior set DisableDeleteNotify 1
  ```
* **Risk Tier:** `Tier 1`.
* **Expected Impact:** Restores NAND flash block reclamation, maintains steady write performance, and extends SSD lifespan.
* **Source:** [Microsoft Learn - fsutil behavior](https://learn.microsoft.com/en-us/windows-server/administration/windows-commands/fsutil-behavior)

#### Item 4.2: Storage Optimization (ReTrim for SSDs vs. Defrag for HDDs)
* **Detection:**
  ```powershell
  Get-PhysicalDisk | Select-Object FriendlyName, MediaType, BusType
  ```
* **Condition:**
  - If MediaType == `SSD`: Execute `Optimize-Volume -ReTrim`.
  - If MediaType == `HDD`: Execute traditional defragmentation `Optimize-Volume -Defrag`.
  - **STRICT PROHIBITION:** Never run `-Defrag` on MediaType `SSD` or BusType `NVMe`.
* **Apply Command (Tier 1):**
  ```powershell
  # SSD Safe ReTrim
  Optimize-Volume -DriveLetter C -ReTrim -Verbose
  
  # HDD Defrag only
  Optimize-Volume -DriveLetter D -Defrag -Verbose
  ```
* **Rollback Command:** None needed (stateless maintenance operation).
* **Risk Tier:** `Tier 1`.
* **Expected Impact:** Reclaims unallocated SSD blocks and reorganizes contiguous HDD tracks without degrading drive longevity.
* **Source:** [Microsoft Learn - Optimize-Volume PowerShell Cmdlet](https://learn.microsoft.com/en-us/powershell/module/storage/optimize-volume)

#### Item 4.3: Safe System Temp Hygiene
* **Detection:**
  ```powershell
  # Inspect size of safe temporary caches
  Get-ChildItem -Path "$env:TEMP", "C:\Windows\Temp" -Recurse -ErrorAction SilentlyContinue | Measure-Object -Property Length -Sum
  ```
* **Condition:** Accumulated obsolete temp files > 2 GB.
* **Apply Command (Tier 1):**
  ```powershell
  # Cleans strictly inside predefined allowlist paths
  Get-ChildItem -Path "$env:TEMP\*" -Recurse -Force -ErrorAction SilentlyContinue | Where-Object { $_.LastWriteTime -lt (Get-Date).AddDays(-3) } | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
  ```
* **Rollback Command:** Not applicable (purging expired ephemeral files).
* **Risk Tier:** `Tier 1`.
* **Expected Impact:** Frees up crucial SSD storage to maintain minimum 15% free space required for optimal SSD wear leveling.
* **Source:** [Windows Storage Sense Documentation](https://support.microsoft.com/en-us/windows/manage-drive-space-with-storage-sense-654f6da5-3101-5085-b90f-ac59ab301979)

---

### ⚡ Subsystem 5: Power & Thermal Management

#### Item 5.1: Battery Health & Wear Diagnostic
* **Detection:**
  ```powershell
  powercfg /batteryreport /output "$env:TEMP\battery_report.html"
  Get-CimInstance Win32_Battery | Select-Object EstimatedChargeRemaining, BatteryStatus, DesignCapacity, FullChargeCapacity
  ```
* **Calculation:**
  $$\text{Battery Wear \%} = \left(1 - \frac{\text{FullChargeCapacity}}{\text{DesignCapacity}}\right) \times 100$$
* **Action:**
  - When Wear > 25%: Provide report advisory on charge threshold management (e.g. Dell Power Manager / Lenovo Vantage 80% charge limit).
* **Risk Tier:** `Tier 0` (Report-only advisory).
* **Source:** [Microsoft Learn - powercfg batteryreport](https://learn.microsoft.com/en-us/windows-hardware/design/device-experiences/powercfg-command-line-options#option_batteryreport)

#### Item 5.2: Thermal Throttling & ACPI Zone Fallback
* **Detection:**
  ```powershell
  # Try reading thermal zone
  Get-CimInstance -Namespace root/wmi -ClassName MSAcpi_ThermalZoneTemperature -ErrorAction SilentlyContinue
  # Fallback to Performance Counter throttling:
  Get-Counter "\Processor Information(_Total)\% Processor Performance" -ErrorAction SilentlyContinue
  ```
* **Graceful Degradation:** If ACPI thermal zones are restricted by vendor firmware (common on modern consumer laptops without elevated vendor drivers), the system logs `"Thermal zone direct query unsupported by firmware; observing CPU frequency throttling counters"` without throwing exceptions.
* **Risk Tier:** `Tier 0`.
* **Source:** [Microsoft Windows WMI ACPI Provider Reference](https://learn.microsoft.com/en-us/windows/win32/wmicoreprov/msacpi-thermalzonetemperature)

---

## 3. Strict Allowlist of Automated Actions

| Action ID | Subsystem | Target Resource | Apply Mechanism | Rollback Mechanism | Risk Tier | Requires Admin? |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `PWR_PLAN_BALANCED` | CPU/Power | Power Scheme | `powercfg /setactive 381b4222...` | `powercfg /setactive <prev_guid>` | Tier 1 | No |
| `PWR_PLAN_PERF` | CPU/Power | Power Scheme | `powercfg /setactive 8c5e7fda...` | `powercfg /setactive 381b4222...` | Tier 1 | No |
| `STARTUP_DISABLE_APP`| CPU | Startup Registry | Set Explorer\StartupApproved `0x03` | Set Explorer\StartupApproved `0x02` | Tier 1 | No |
| `GPU_ENABLE_HAGS` | GPU | GraphicsDrivers HwSchMode | Set `HwSchMode = 2` | Set `HwSchMode = 1` | Tier 2 | **Yes (UAC)** |
| `GPU_APP_PREFERENCE` | GPU | DirectX UserGpuPreferences | Set `GpuPreference=2;` | Remove registry value | Tier 1 | No |
| `RAM_ENABLE_COMPRESS`| RAM | MMAgent | `Enable-MMAgent -MemoryCompression`| `Disable-MMAgent...` | Tier 2 | **Yes (UAC)** |
| `STORAGE_ENABLE_TRIM`| Storage | fsutil DisableDeleteNotify | `fsutil behavior set DisableDeleteNotify 0` | Set `DisableDeleteNotify 1` | Tier 1 | **Yes (UAC)** |
| `STORAGE_RETRIM_SSD` | Storage | Optimize-Volume | `Optimize-Volume -DriveLetter <X> -ReTrim`| Stateless | Tier 1 | **Yes (UAC)** |
| `STORAGE_DEFRAG_HDD` | Storage | Optimize-Volume | `Optimize-Volume -DriveLetter <X> -Defrag`| Stateless | Tier 1 | **Yes (UAC)** |
| `STORAGE_CLEAN_TEMP` | Storage | Safe Temp Folders | Remove older than 3 days | Stateless | Tier 1 | No |

---

## 4. Verification Checkpoints & References
1. Windows Internals, 7th Edition (Part 1 & 2) — Pavel Yosifovich, David A. Solomon, Alex Ionescu, Mark E. Russinovich.
2. Microsoft Learn: [Windows Hardware Developer Documentation](https://learn.microsoft.com/en-us/windows-hardware/).
3. Microsoft Performance Team Blog: [Understanding Memory Pressure and Commit Charge](https://techcommunity.microsoft.com/t5/windows-blog-archive/pushing-the-limits-of-windows-virtual-memory/ba-p/723817).
