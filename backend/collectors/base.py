import asyncio
import json
import logging
import platform
import subprocess
from typing import Any, Dict, Optional
from backend.security import sanitize_telemetry_dict

logger = logging.getLogger("collectors")

# Measured on a Windows 11 laptop with all collectors running concurrently:
# 2.4-7.1s per collector (cold powershell.exe start + CIM provider spin-up),
# so the old 3.0s cap failed every collector on a cold boot.
DEFAULT_TIMEOUT_SEC = 15.0


class BaseCollector:
    """Base class for telemetry collectors with strict timeout enforcement."""

    def __init__(self, timeout_sec: float = DEFAULT_TIMEOUT_SEC):
        self.timeout_sec = timeout_sec
        self.is_windows = platform.system().lower() == "windows"

    async def execute_powershell_json(self, script: str) -> Optional[Dict[str, Any]]:
        """Executes a PowerShell script block and parses JSON output with timeout."""
        name = type(self).__name__
        try:
            return await asyncio.to_thread(self._invoke_powershell, script)
        except subprocess.TimeoutExpired:
            # subprocess.run has already killed the timed-out powershell.exe
            logger.warning(f"{name} timed out after {self.timeout_sec}s.")
            return {"status": "TIMEOUT", "error": f"Query exceeded {self.timeout_sec}s threshold"}
        except Exception as e:
            logger.error(f"{name} error: {e}")
            return {"status": "ERROR", "error": str(e)}

    def _invoke_powershell(self, script: str) -> Optional[Dict[str, Any]]:
        cmd = ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", script]
        proc = subprocess.run(
            cmd,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            check=False,
            shell=False,
            timeout=self.timeout_sec,
        )
        raw = proc.stdout.strip()
        if not raw:
            return {}
        try:
            data = json.loads(raw)
            return sanitize_telemetry_dict(data)
        except Exception as parse_err:
            logger.debug(f"JSON parse error from PowerShell: {parse_err}")
            return {"raw": raw}
