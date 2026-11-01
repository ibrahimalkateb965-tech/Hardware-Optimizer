import json
import re
import subprocess
import sys
from pathlib import Path

POWERSHELL_SCRIPT = r"""
$ErrorActionPreference = 'SilentlyContinue'

# 1. System & OS
$os = Get-CimInstance Win32_OperatingSystem | Select-Object Caption, Version, OSArchitecture, TotalVisibleMemorySize, FreePhysicalMemory, NumberOfProcesses
$cs = Get-CimInstance Win32_ComputerSystem | Select-Object Model, SystemType, TotalPhysicalMemory, NumberOfProcessors, NumberOfLogicalProcessors

# 2. CPU
$cpu = Get-CimInstance Win32_Processor | Select-Object Name, Manufacturer, NumberOfCores, NumberOfLogicalProcessors, MaxClockSpeed, CurrentClockSpeed, L2CacheSize, L3CacheSize, Architecture
$activeScheme = powercfg /getactivescheme
$startupApps = Get-CimInstance Win32_StartupCommand | Select-Object Name, Location

# 3. GPU
$gpus = Get-CimInstance Win32_VideoController | Select-Object Name, AdapterRAM, DriverVersion, DriverDate, VideoProcessor, CurrentHorizontalResolution, CurrentVerticalResolution, Status
$hags = Get-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Control\GraphicsDrivers" -Name "HwSchMode" 2>$null | Select-Object -ExpandProperty HwSchMode
$gameMode = Get-ItemProperty -Path "HKCU:\Software\Microsoft\GameBar" -Name "AutoGameModeEnabled" 2>$null | Select-Object -ExpandProperty AutoGameModeEnabled

# 4. RAM
$ramModules = Get-CimInstance Win32_PhysicalMemory | Select-Object DeviceLocator, Capacity, Speed, ConfiguredClockSpeed, FormFactor, PartNumber
$pagefiles = Get-CimInstance Win32_PageFileUsage | Select-Object Name, AllocatedBaseSize, CurrentUsage, PeakUsage
$mmAgent = Get-MMAgent | Select-Object MemoryCompression, PageCombining

# 5. Storage
$disks = Get-PhysicalDisk | Select-Object FriendlyName, MediaType, BusType, Size, OperationalStatus, HealthStatus
$volumes = Get-Volume | Where-Object { $_.DriveLetter -ne $null } | Select-Object DriveLetter, FileSystemLabel, FileSystemType, SizeRemaining, Size
$trimRaw = fsutil behavior query DisableDeleteNotify

# 6. Power & Thermal
$powerPlans = powercfg /list
$battery = Get-CimInstance Win32_Battery | Select-Object EstimatedChargeRemaining, BatteryStatus, DesignCapacity, FullChargeCapacity
$thermalZones = Get-CimInstance -Namespace root/wmi -ClassName MSAcpi_ThermalZoneTemperature 2>$null | Select-Object CurrentTemperature, CriticalTripPoint

[PSCustomObject]@{
    CollectedAt = (Get-Date).ToString("yyyy-MM-ddTHH:mm:ssZ")
    OperatingSystem = $os
    ComputerSystem = $cs
    CPU = @{
        Details = $cpu
        ActivePowerScheme = "$activeScheme"
        StartupAppsCount = ($startupApps | Measure-Object).Count
        StartupSample = ($startupApps | Select-Object -First 10)
    }
    GPU = @{
        Controllers = $gpus
        HAGSMode = $hags
        GameModeEnabled = $gameMode
    }
    RAM = @{
        Modules = $ramModules
        TotalModules = ($ramModules | Measure-Object).Count
        PageFiles = $pagefiles
        MemoryManagement = $mmAgent
    }
    Storage = @{
        Disks = $disks
        Volumes = $volumes
        TrimStatusRaw = "$trimRaw"
    }
    PowerThermal = @{
        PowerPlansRaw = "$powerPlans"
        Battery = $battery
        ThermalZones = $thermalZones
    }
} | ConvertTo-Json -Depth 6
"""

def sanitize_data(data):
    if isinstance(data, dict):
        sanitized = {}
        for k, v in data.items():
            if k.lower() in ("serialnumber", "uuid", "identifyingnumber", "macaddress", "username"):
                sanitized[k] = "[REDACTED]"
            else:
                sanitized[k] = sanitize_data(v)
        return sanitized
    elif isinstance(data, list):
        return [sanitize_data(item) for item in data]
    elif isinstance(data, str):
        # Redact usernames in paths (e.g., C:\Users\Username)
        redacted = re.sub(r'([A-Za-z]:\\Users\\)[^\\]+', r'\1[USER]', data, flags=re.IGNORECASE)
        # Redact GUIDs
        redacted = re.sub(r'[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}', '[GUID]', redacted)
        return redacted
    else:
        return data

def main():
    print("Collecting hardware inventory via PowerShell...")
    cmd = ["powershell.exe", "-NoProfile", "-Command", POWERSHELL_SCRIPT]
    try:
        proc = subprocess.run(
            cmd,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            check=True
        )
        raw_output = proc.stdout.strip()
        data = json.loads(raw_output)
        sanitized = sanitize_data(data)
        
        output_file = Path("/mnt/f/AI PROJECTS/HardwareOptimizer/inventory.sample.json")
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(sanitized, f, indent=2, ensure_ascii=False)
        
        print(f"Inventory saved successfully to {output_file}")
        print(f"OS: {sanitized.get('OperatingSystem', {}).get('Caption')}")
        print(f"CPU: {sanitized.get('CPU', {}).get('Details', {}).get('Name')}")
        gpus = sanitized.get('GPU', {}).get('Controllers', [])
        if isinstance(gpus, dict):
            gpus = [gpus]
        print(f"GPUs detected: {[g.get('Name') for g in gpus]}")
        ram = sanitized.get('RAM', {})
        print(f"RAM Modules: {ram.get('TotalModules')}")
        disks = sanitized.get('Storage', {}).get('Disks', [])
        if isinstance(disks, dict):
            disks = [disks]
        print(f"Storage Disks: {[d.get('FriendlyName') for d in disks]}")
        return 0
    except Exception as e:
        print(f"Error collecting telemetry: {e}", file=sys.stderr)
        return 1

if __name__ == "__main__":
    sys.exit(main())
