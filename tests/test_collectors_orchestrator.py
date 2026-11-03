import asyncio
import subprocess
import time

import pytest

from backend.collectors import orchestrator as orch_mod
from backend.collectors.base import BaseCollector
from backend.collectors.orchestrator import TelemetryOrchestrator


class FakeCollector:
    def __init__(self, payload, delay=0.0):
        self.payload = payload
        self.delay = delay
        self.calls = 0

    async def collect(self):
        self.calls += 1
        await asyncio.sleep(self.delay)
        return dict(self.payload)


class FakeClock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now


@pytest.fixture(autouse=True)
def _force_live_path(monkeypatch):
    # Exercise the real collection path regardless of host OS or .env sandbox setting
    monkeypatch.setattr(orch_mod.platform, "system", lambda: "Windows")
    monkeypatch.setattr(orch_mod.settings, "SANDBOX_MODE", False)


def _make_orchestrator(delay=0.0, storage_payload=None, clock=None):
    orch = TelemetryOrchestrator(cache_ttl_sec=300.0, clock=clock or FakeClock())
    orch.system_col = FakeCollector({"OperatingSystem": {"Caption": "Windows 11 Pro"}, "ComputerSystem": {"Model": "G3 3500"}}, delay)
    orch.cpu_col = FakeCollector({"Details": {"Name": "i7-10750H"}}, delay)
    orch.gpu_col = FakeCollector({"Controllers": [{"Name": "GTX 1650"}]}, delay)
    orch.ram_col = FakeCollector({"TotalModules": 2}, delay)
    orch.storage_col = FakeCollector(storage_payload or {"Disks": [{"FriendlyName": "NVMe"}]}, delay)
    orch.power_col = FakeCollector({"PowerPlansRaw": "Balanced"}, delay)
    return orch


def _all_cols(orch):
    return [orch.system_col, orch.cpu_col, orch.gpu_col, orch.ram_col, orch.storage_col, orch.power_col]


def test_collectors_run_in_parallel_and_fill_inventory():
    orch = _make_orchestrator(delay=0.2)
    start = time.perf_counter()
    inv = asyncio.run(orch.get_full_inventory())
    elapsed = time.perf_counter() - start

    # Six collectors at 0.2s each: sequential would take 1.2s
    assert elapsed < 0.6
    assert inv["OperatingSystem"]["Caption"] == "Windows 11 Pro"
    assert inv["ComputerSystem"]["Model"] == "G3 3500"
    assert inv["CPU"]["Details"]["Name"] == "i7-10750H"
    assert inv["Storage"]["Disks"][0]["FriendlyName"] == "NVMe"


def test_complete_inventory_is_cached_until_ttl_expires():
    clock = FakeClock()
    orch = _make_orchestrator(clock=clock)

    async def _run():
        first = await orch.get_full_inventory()
        second = await orch.get_full_inventory()
        assert second == first
        assert all(c.calls == 1 for c in _all_cols(orch))

        clock.now += 301.0
        await orch.get_full_inventory()
        assert all(c.calls == 2 for c in _all_cols(orch))

    asyncio.run(_run())


def test_cached_inventory_is_returned_as_a_copy():
    orch = _make_orchestrator()

    async def _run():
        first = await orch.get_full_inventory()
        first["CPU"]["Details"]["Name"] = "tampered"
        second = await orch.get_full_inventory()
        assert second["CPU"]["Details"]["Name"] == "i7-10750H"

    asyncio.run(_run())


def test_refresh_and_invalidate_bypass_cache():
    orch = _make_orchestrator()

    async def _run():
        await orch.get_full_inventory()
        await orch.get_full_inventory(refresh=True)
        assert orch.cpu_col.calls == 2
        orch.invalidate_cache()
        await orch.get_full_inventory()
        assert orch.cpu_col.calls == 3

    asyncio.run(_run())


def test_concurrent_callers_share_one_collection():
    orch = _make_orchestrator(delay=0.1)

    async def _run():
        results = await asyncio.gather(*(orch.get_full_inventory() for _ in range(5)))
        assert all(r == results[0] for r in results)
        assert all(c.calls == 1 for c in _all_cols(orch))

    asyncio.run(_run())


def test_incomplete_inventory_is_not_cached():
    orch = _make_orchestrator(storage_payload={"status": "TIMEOUT", "error": "Query exceeded 25.0s threshold"})

    async def _run():
        inv = await orch.get_full_inventory()
        assert inv["Storage"]["status"] == "TIMEOUT"
        await orch.get_full_inventory()
        assert orch.cpu_col.calls == 2

    asyncio.run(_run())


def test_collection_started_before_invalidate_does_not_repopulate_cache():
    orch = _make_orchestrator(delay=0.1)

    async def _run():
        pending = asyncio.ensure_future(orch.get_full_inventory())
        await asyncio.sleep(0.02)
        orch.invalidate_cache()
        await pending
        assert orch._cache is None
        await orch.get_full_inventory()
        assert orch.cpu_col.calls == 2

    asyncio.run(_run())


def test_powershell_timeout_kills_process_and_reports_timeout(monkeypatch):
    seen = {}

    def fake_run(cmd, **kwargs):
        seen.update(kwargs, cmd=cmd)
        raise subprocess.TimeoutExpired(cmd, kwargs["timeout"])

    monkeypatch.setattr(subprocess, "run", fake_run)
    collector = BaseCollector(timeout_sec=7.5)
    result = asyncio.run(collector.execute_powershell_json("Get-PhysicalDisk"))

    assert result == {"status": "TIMEOUT", "error": "Query exceeded 7.5s threshold"}
    # The timeout is enforced by subprocess.run, which kills powershell.exe on expiry
    assert seen["timeout"] == 7.5
    assert seen["shell"] is False
    assert seen["stdin"] is subprocess.DEVNULL
    assert isinstance(seen["cmd"], list)
