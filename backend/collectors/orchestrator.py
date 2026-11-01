import asyncio
import platform
from datetime import datetime, timezone
from typing import Any, Dict
from backend.config import settings
from backend.collectors.cpu import CPUCollector
from backend.collectors.gpu import GPUCollector
from backend.collectors.ram import RAMCollector
from backend.collectors.storage import StorageCollector
from backend.collectors.power import PowerThermalCollector
from backend.collectors.sandbox import get_sandbox_profile


class TelemetryOrchestrator:
    """Orchestrates async collection across all 5 subsystems."""

    def __init__(self):
        self.cpu_col = CPUCollector()
        self.gpu_col = GPUCollector()
        self.ram_col = RAMCollector()
        self.storage_col = StorageCollector()
        self.power_col = PowerThermalCollector()

    async def get_full_inventory(self, force_sandbox: bool = False, profile_name: str = "default") -> Dict[str, Any]:
        # If in sandbox mode or non-windows environment, use sandbox fixture
        if force_sandbox or settings.SANDBOX_MODE or platform.system().lower() != "windows":
            return get_sandbox_profile(profile_name)

        # Run collectors concurrently with 3.0s individual timeout envelopes
        results = await asyncio.gather(
            self.cpu_col.collect(),
            self.gpu_col.collect(),
            self.ram_col.collect(),
            self.storage_col.collect(),
            self.power_col.collect(),
            return_exceptions=True
        )

        cpu_res, gpu_res, ram_res, storage_res, power_res = [
            r if not isinstance(r, Exception) else {"error": str(r)} for r in results
        ]

        return {
            "CollectedAt": datetime.now(timezone.utc).isoformat(),
            "CPU": cpu_res,
            "GPU": gpu_res,
            "RAM": ram_res,
            "Storage": storage_res,
            "PowerThermal": power_res
        }
