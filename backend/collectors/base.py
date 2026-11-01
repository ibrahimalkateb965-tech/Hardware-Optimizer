import asyncio
import json
import logging
import platform
import subprocess
from typing import Any, Dict, Optional
from backend.security import sanitize_telemetry_dict

logger = logging.getLogger("collectors")

class BaseCollector:
    """Base class for telemetry collectors with strict async timeout enforcement."""

    def __init__(self, timeout_sec: float = 3.0):
        self.timeout_sec = timeout_sec
        self.is_windows = platform.system().lower() == "windows"

    async def execute_powershell_json(self, script: str) -> Optional[Dict[str, Any]]:
        """Executes a PowerShell script block and parses JSON output with timeout."""
        try:
            return await asyncio.wait_for(
                self._run_powershell_subproc(script),
                timeout=self.timeout_sec
            )
        except asyncio.TimeoutError:
            logger.warning(f"Telemetry collector timed out after {self.timeout_sec}s.")
            return {"status": "TIMEOUT", "error": "Query exceeded 3.0s threshold"}
        except Exception as e:
            logger.error(f"Collector error: {e}")
            return {"status": "ERROR", "error": str(e)}

    async def _run_powershell_subproc(self, script: str) -> Optional[Dict[str, Any]]:
        loop = asyncio.get_running_loop()
        def _invoke():
            cmd = ["powershell.exe", "-NoProfile", "-Command", script]
            proc = subprocess.run(
                cmd,
                stdin=subprocess.DEVNULL,
                capture_output=True,
                text=True,
                check=False
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

        return await loop.run_in_executor(None, _invoke)
