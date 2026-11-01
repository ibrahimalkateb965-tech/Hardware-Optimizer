from typing import Any, Dict
from backend.collectors.base import BaseCollector

class SystemCollector(BaseCollector):
    SCRIPT = r"""
    $ErrorActionPreference = 'SilentlyContinue'
    $os = Get-CimInstance Win32_OperatingSystem | Select-Object Caption, Version, OSArchitecture, TotalVisibleMemorySize, FreePhysicalMemory, NumberOfProcesses
    $cs = Get-CimInstance Win32_ComputerSystem | Select-Object Model, SystemType, TotalPhysicalMemory, NumberOfProcessors, NumberOfLogicalProcessors

    [PSCustomObject]@{
        OperatingSystem = $os
        ComputerSystem = $cs
    } | ConvertTo-Json -Depth 4
    """

    async def collect(self) -> Dict[str, Any]:
        result = await self.execute_powershell_json(self.SCRIPT)
        return result or {}
