from typing import Any, Dict
from backend.collectors.base import BaseCollector

class PowerThermalCollector(BaseCollector):
    SCRIPT = r"""
    $ErrorActionPreference = 'SilentlyContinue'
    $powerPlans = powercfg /list
    $battery = Get-CimInstance Win32_Battery | Select-Object EstimatedChargeRemaining, BatteryStatus, DesignCapacity, FullChargeCapacity
    $thermalZones = Get-CimInstance -Namespace root/wmi -ClassName MSAcpi_ThermalZoneTemperature 2>$null | Select-Object CurrentTemperature, CriticalTripPoint

    [PSCustomObject]@{
        PowerPlansRaw = "$powerPlans"
        Battery = $battery
        ThermalZones = $thermalZones
    } | ConvertTo-Json -Depth 4
    """

    async def collect(self) -> Dict[str, Any]:
        result = await self.execute_powershell_json(self.SCRIPT)
        return result or {}
