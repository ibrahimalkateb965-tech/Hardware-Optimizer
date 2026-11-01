from typing import Any, Dict
from backend.collectors.base import BaseCollector

class RAMCollector(BaseCollector):
    SCRIPT = r"""
    $ErrorActionPreference = 'SilentlyContinue'
    $ramModules = Get-CimInstance Win32_PhysicalMemory | Select-Object DeviceLocator, Capacity, Speed, ConfiguredClockSpeed, FormFactor, PartNumber
    $pagefiles = Get-CimInstance Win32_PageFileUsage | Select-Object Name, AllocatedBaseSize, CurrentUsage, PeakUsage
    $mmAgent = Get-MMAgent | Select-Object MemoryCompression, PageCombining

    [PSCustomObject]@{
        Modules = $ramModules
        TotalModules = ($ramModules | Measure-Object).Count
        PageFiles = $pagefiles
        MemoryManagement = $mmAgent
    } | ConvertTo-Json -Depth 4
    """

    async def collect(self) -> Dict[str, Any]:
        result = await self.execute_powershell_json(self.SCRIPT)
        return result or {}
