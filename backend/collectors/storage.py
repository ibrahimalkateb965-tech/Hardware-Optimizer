from typing import Any, Dict
from backend.collectors.base import BaseCollector

class StorageCollector(BaseCollector):
    SCRIPT = r"""
    $ErrorActionPreference = 'SilentlyContinue'
    $disks = Get-PhysicalDisk | Select-Object FriendlyName, MediaType, BusType, Size, OperationalStatus, HealthStatus
    $volumes = Get-Volume | Where-Object { $_.DriveLetter -ne $null } | Select-Object DriveLetter, FileSystemLabel, FileSystemType, SizeRemaining, Size
    $trimRaw = fsutil behavior query DisableDeleteNotify

    [PSCustomObject]@{
        Disks = $disks
        Volumes = $volumes
        TrimStatusRaw = "$trimRaw"
    } | ConvertTo-Json -Depth 4
    """

    async def collect(self) -> Dict[str, Any]:
        result = await self.execute_powershell_json(self.SCRIPT)
        return result or {}
