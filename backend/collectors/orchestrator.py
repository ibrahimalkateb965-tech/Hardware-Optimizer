import asyncio
import copy
import platform
import time
from datetime import datetime, timezone
from typing import Any, Callable, Dict, Optional
from backend.config import settings
from backend.collectors.cpu import CPUCollector
from backend.collectors.gpu import GPUCollector
from backend.collectors.ram import RAMCollector
from backend.collectors.storage import StorageCollector
from backend.collectors.power import PowerThermalCollector
from backend.collectors.system import SystemCollector
from backend.collectors.sandbox import get_sandbox_profile

# Hardware inventory is mostly static; re-collecting it costs ~7s of PowerShell.
INVENTORY_CACHE_TTL_SEC = 300.0
# Get-PhysicalDisk spins up the Storage WMI provider (2.7s warm, 7s+ under load).
STORAGE_TIMEOUT_SEC = 25.0


def _section_ok(section: Any) -> bool:
    # Empty output means PowerShell returned nothing usable: treat as a failure
    return isinstance(section, dict) and bool(section) and "error" not in section and section.get("status") not in ("TIMEOUT", "ERROR")


class TelemetryOrchestrator:
    """Orchestrates parallel collection across all subsystems with a TTL cache.

    Concurrent callers share one in-flight collection, and only complete
    inventories (no timed-out or failed section) are cached.
    """

    def __init__(self, cache_ttl_sec: float = INVENTORY_CACHE_TTL_SEC, clock: Callable[[], float] = time.monotonic):
        self.system_col = SystemCollector()
        self.cpu_col = CPUCollector()
        self.gpu_col = GPUCollector()
        self.ram_col = RAMCollector()
        self.storage_col = StorageCollector(timeout_sec=STORAGE_TIMEOUT_SEC)
        self.power_col = PowerThermalCollector()

        self.cache_ttl_sec = cache_ttl_sec
        self._clock = clock
        self._cache: Optional[Dict[str, Any]] = None
        self._cache_time = 0.0
        self._generation = 0
        self._inflight: Optional[asyncio.Task] = None

    def invalidate_cache(self) -> None:
        """Drops the cached inventory, e.g. after actions changed system state."""
        self._generation += 1
        self._cache = None
        self._inflight = None

    async def get_full_inventory(self, force_sandbox: bool = False, profile_name: str = "default", refresh: bool = False) -> Dict[str, Any]:
        # If in sandbox mode or non-windows environment, use sandbox fixture
        if force_sandbox or settings.SANDBOX_MODE or platform.system().lower() != "windows":
            return get_sandbox_profile(profile_name)

        if refresh:
            self.invalidate_cache()
        elif self._cache is not None and self._clock() - self._cache_time < self.cache_ttl_sec:
            return copy.deepcopy(self._cache)

        loop = asyncio.get_running_loop()
        if self._inflight is None or self._inflight.done() or self._inflight.get_loop() is not loop:
            self._inflight = loop.create_task(self._collect(self._generation))
        # Shield so one disconnecting client does not cancel the shared collection
        inventory = await asyncio.shield(self._inflight)
        return copy.deepcopy(inventory)

    async def _collect(self, generation: int) -> Dict[str, Any]:
        # Collectors run concurrently, each in its own powershell.exe with its own timeout
        results = await asyncio.gather(
            self.system_col.collect(),
            self.cpu_col.collect(),
            self.gpu_col.collect(),
            self.ram_col.collect(),
            self.storage_col.collect(),
            self.power_col.collect(),
            return_exceptions=True
        )

        sys_res, cpu_res, gpu_res, ram_res, storage_res, power_res = [
            r if not isinstance(r, Exception) else {"error": str(r)} for r in results
        ]

        inventory = {
            "CollectedAt": datetime.now(timezone.utc).isoformat(),
            "OperatingSystem": (sys_res.get("OperatingSystem") or {}) if _section_ok(sys_res) else sys_res,
            "ComputerSystem": (sys_res.get("ComputerSystem") or {}) if _section_ok(sys_res) else sys_res,
            "CPU": cpu_res,
            "GPU": gpu_res,
            "RAM": ram_res,
            "Storage": storage_res,
            "PowerThermal": power_res
        }

        # A collection started before invalidate_cache() must not repopulate the cache
        if generation == self._generation and all(_section_ok(r) for r in (sys_res, cpu_res, gpu_res, ram_res, storage_res, power_res)):
            self._cache = inventory
            self._cache_time = self._clock()
        return inventory
