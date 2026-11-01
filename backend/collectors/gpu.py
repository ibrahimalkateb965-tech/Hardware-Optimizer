from typing import Any, Dict
from backend.collectors.base import BaseCollector

class GPUCollector(BaseCollector):
    SCRIPT = r"""
    $ErrorActionPreference = 'SilentlyContinue'
    $gpus = Get-CimInstance Win32_VideoController | Select-Object Name, AdapterRAM, DriverVersion, DriverDate, VideoProcessor, CurrentHorizontalResolution, CurrentVerticalResolution, Status
    $hags = Get-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Control\GraphicsDrivers" -Name "HwSchMode" 2>$null | Select-Object -ExpandProperty HwSchMode
    $gameMode = Get-ItemProperty -Path "HKCU:\Software\Microsoft\GameBar" -Name "AutoGameModeEnabled" 2>$null | Select-Object -ExpandProperty AutoGameModeEnabled

    [PSCustomObject]@{
        Controllers = $gpus
        HAGSMode = $hags
        GameModeEnabled = $gameMode
    } | ConvertTo-Json -Depth 4
    """

    async def collect(self) -> Dict[str, Any]:
        result = await self.execute_powershell_json(self.SCRIPT)
        return result or {}
