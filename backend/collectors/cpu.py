from typing import Any, Dict
from backend.collectors.base import BaseCollector

class CPUCollector(BaseCollector):
    SCRIPT = r"""
    $ErrorActionPreference = 'SilentlyContinue'
    $cpu = Get-CimInstance Win32_Processor | Select-Object Name, Manufacturer, NumberOfCores, NumberOfLogicalProcessors, MaxClockSpeed, CurrentClockSpeed, L2CacheSize, L3CacheSize, Architecture
    $activeScheme = powercfg /getactivescheme
    $startupApps = Get-CimInstance Win32_StartupCommand | Select-Object Name, Location

    [PSCustomObject]@{
        Details = $cpu
        ActivePowerScheme = "$activeScheme"
        StartupAppsCount = ($startupApps | Measure-Object).Count
        StartupSample = ($startupApps | Select-Object -First 10)
    } | ConvertTo-Json -Depth 4
    """

    async def collect(self) -> Dict[str, Any]:
        result = await self.execute_powershell_json(self.SCRIPT)
        return result or {}
