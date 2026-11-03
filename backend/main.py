import asyncio
import json
import logging
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import psutil
from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from backend.ai.client import OpenCodeGoClient
from backend.collectors.orchestrator import TelemetryOrchestrator
from backend.config import FRONTEND_DIST_DIR, settings
from backend.db.ledger import StateLedger
from backend.helper.elevated_helper import (
    apply_action,
    create_system_restore_point,
    execute_actions,
    rollback_action,
)
from backend.rules.engine import RulesEngine
from backend.schemas import (
    ActionID,
    ActionResult,
    ApplyRequest,
    ApplyResponse,
    LiveTelemetry,
    RecommendationsResponse,
    RollbackRequest,
    RollbackResponse,
)
from backend.security import verify_host_header, verify_session_token

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("server")

app = FastAPI(
    title="Windows Hardware Diagnostics & Optimizer",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url=None,
    dependencies=[Depends(verify_host_header)]
)

# CORS limited to this server's own origin; other local ports (dev servers, other apps) must not read API responses
app.add_middleware(
    CORSMiddleware,
    allow_origins=[f"http://127.0.0.1:{settings.PORT}", f"http://localhost:{settings.PORT}"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

# Singletons
orchestrator = TelemetryOrchestrator()
rules_engine = RulesEngine()
ai_client = OpenCodeGoClient()
ledger = StateLedger()

# Initial disk io counters for rate calculation
_last_disk_io = psutil.disk_io_counters()
_last_disk_time = time.time()


@app.on_event("startup")
async def on_startup():
    logger.info("=" * 60)
    logger.info("🚀 Windows Hardware Diagnostics & Optimizer Backend Initialized")
    logger.info(f"📍 Binding Address: http://{settings.HOST}:{settings.PORT}")
    logger.info(f"🔑 Session Security Token: {settings.SESSION_TOKEN}")
    logger.info(f"🤖 LLM Assisted Engine: {settings.OPENCODE_GO_MODEL}")
    logger.info("=" * 60)
    # Warm the inventory cache so the first diagnostics view does not wait on PowerShell
    asyncio.create_task(orchestrator.get_full_inventory())


@app.get("/api/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": "1.0.0",
        "sandbox_mode": settings.SANDBOX_MODE,
    }


@app.get("/api/telemetry/live", response_model=LiveTelemetry)
async def get_live_telemetry():
    global _last_disk_io, _last_disk_time
    
    cpu_percent = psutil.cpu_percent(interval=None)
    cpu_cores = psutil.cpu_percent(interval=None, percpu=True)
    
    cpu_freq = psutil.cpu_freq()
    freq_mhz = cpu_freq.current if cpu_freq else None
    
    mem = psutil.virtual_memory()
    
    # Calculate disk I/O rates
    current_time = time.time()
    current_io = psutil.disk_io_counters()
    time_delta = max(0.1, current_time - _last_disk_time)
    
    read_rate = 0.0
    write_rate = 0.0
    if current_io and _last_disk_io:
        read_rate = (current_io.read_bytes - _last_disk_io.read_bytes) / time_delta
        write_rate = (current_io.write_bytes - _last_disk_io.write_bytes) / time_delta
    
    _last_disk_io = current_io
    _last_disk_time = current_time

    return LiveTelemetry(
        timestamp=current_time,
        cpu_percent=cpu_percent,
        cpu_cores=cpu_cores,
        cpu_freq_mhz=freq_mhz,
        ram_total_bytes=mem.total,
        ram_available_bytes=mem.available,
        ram_used_percent=mem.percent,
        gpu_telemetry=[],
        disk_read_bytes_sec=max(0.0, read_rate),
        disk_write_bytes_sec=max(0.0, write_rate)
    )


@app.get("/api/inventory")
async def get_inventory(sandbox: bool = False, profile: str = "default", refresh: bool = False):
    """Returns the hardware inventory (cached for a few minutes; refresh=true re-collects)."""
    return await orchestrator.get_full_inventory(force_sandbox=sandbox, profile_name=profile, refresh=refresh)


@app.post("/api/recommendations/analyze", response_model=RecommendationsResponse)
async def analyze_recommendations(
    sandbox: bool = False,
    profile: str = "default",
    _=Depends(verify_session_token)
):
    """Executes deterministic rules engine + GLM-5.3-Flash Arabic explainer."""
    inventory = await orchestrator.get_full_inventory(force_sandbox=sandbox, profile_name=profile)
    candidates, health_scores = rules_engine.evaluate(inventory)
    
    session_id = f"sess_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
    ledger.create_session(session_id, health_score_before=health_scores.overall)
    
    # Record baseline snapshot
    mem = psutil.virtual_memory()
    ledger.record_snapshot(
        session_id=session_id,
        phase="before",
        cpu_percent=psutil.cpu_percent(interval=None),
        ram_used_percent=mem.percent
    )

    recs, is_llm, notice = await ai_client.prioritize_and_explain(
        inventory_summary={
            "OS": inventory.get("OperatingSystem", {}).get("Caption"),
            "CPU": inventory.get("CPU", {}).get("Details", {}).get("Name"),
            "RAM_Total": inventory.get("RAM", {}).get("TotalModules")
        },
        candidates=candidates
    )

    return RecommendationsResponse(
        session_id=session_id,
        health_scores=health_scores,
        recommendations=recs,
        llm_assisted=is_llm,
        notice_ar=notice
    )


@app.post("/api/apply", response_model=ApplyResponse)
async def apply_optimizations(
    req: ApplyRequest,
    _=Depends(verify_session_token)
):
    """Executes validated allowlisted actions with automatic System Restore Point and UAC elevation."""
    if not req.selected_action_ids:
        raise HTTPException(status_code=400, detail="No optimization actions selected.")
    if not ledger.get_session(req.session_id):
        raise HTTPException(status_code=404, detail="Session not found in ledger.")

    # 1. Execute actions workflow (handles UAC elevation, restore point, and allowlist execution)
    res_data = execute_actions(
        mode="apply",
        session_id=req.session_id,
        action_ids=req.selected_action_ids
    )
    # Applied actions change system state: the next scan must not reuse the cache
    orchestrator.invalidate_cache()

    results: List[ActionResult] = [
        ActionResult(**r) if isinstance(r, dict) else r for r in res_data.get("results", [])
    ]
    all_success = res_data.get("all_success", False)
    rp_created = res_data.get("restore_point_created", False)
    rp_id = res_data.get("restore_point_id")

    # 2. Record in ledger
    ledger.record_applied_actions(req.session_id, results, restore_point_created=rp_created)
    
    # Record post-apply snapshot
    mem = psutil.virtual_memory()
    # Sample over a real window; interval=None compares against an arbitrary earlier call
    post_cpu = await asyncio.to_thread(psutil.cpu_percent, 1.0)
    post_ram = mem.percent
    ledger.record_snapshot(
        session_id=req.session_id,
        phase="after",
        cpu_percent=post_cpu,
        ram_used_percent=post_ram
    )

    # Calculate improved health score after apply
    session_info = ledger.get_session(req.session_id)
    before_score = session_info.get("health_score_before", 75) if session_info else 75
    successful_count = sum(1 for r in results if r.success)
    # No successful action means no improvement: never report a gain that did not happen
    after_score = min(100, (before_score or 75) + successful_count * 8) if successful_count else (before_score or 75)
    ledger.update_session_health_after(req.session_id, after_score)

    return ApplyResponse(
        session_id=req.session_id,
        success=all_success,
        results=results,
        restore_point_created=rp_created,
        restore_point_id=rp_id
    )


@app.post("/api/rollback", response_model=RollbackResponse)
async def rollback_optimizations(
    req: RollbackRequest,
    _=Depends(verify_session_token)
):
    """Reverts applied optimizations for a session with UAC elevation support."""
    if not ledger.get_session(req.session_id):
        raise HTTPException(status_code=404, detail="Session not found in ledger.")
    target_actions = req.target_action_ids
    if not target_actions:
        # Load from ledger history
        history = ledger.get_session_history()
        session_info = next((s for s in history if s["session_id"] == req.session_id), None)
        if not session_info:
            raise HTTPException(status_code=404, detail="Session not found in ledger.")
        target_actions = [ActionID(a["action_id"]) for a in session_info.get("actions", [])]

    # Execute rollback workflow
    res_data = execute_actions(
        mode="rollback",
        session_id=req.session_id,
        action_ids=target_actions
    )
    orchestrator.invalidate_cache()

    results: List[ActionResult] = [
        ActionResult(**r) if isinstance(r, dict) else r for r in res_data.get("results", [])
    ]
    all_success = res_data.get("all_success", False)
    reverted_ids = [r.action_id for r in results if r.success]

    ledger.mark_actions_rolled_back(req.session_id, reverted_ids)

    return RollbackResponse(
        session_id=req.session_id,
        success=all_success,
        results=results
    )


@app.get("/api/comparison")
async def get_comparison_metrics(
    session_id: Optional[str] = None,
    _=Depends(verify_session_token)
):
    """Returns before and after metrics snapshot comparison for a session or latest."""
    data = ledger.get_comparison(session_id)
    if not data:
        return {
            "has_data": False,
            "session_id": None,
            "message_ar": "لا توجد جلسات تحسين مسجلة حتى الآن."
        }
    return {
        "has_data": True,
        **data
    }


@app.get("/api/history")
async def get_history():
    """Returns past optimization sessions and rollback ledger."""
    return {"sessions": ledger.get_session_history()}


# Mount static frontend build if dist exists
if FRONTEND_DIST_DIR.exists():
    assets_dir = FRONTEND_DIST_DIR / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        file_path = FRONTEND_DIST_DIR / full_path
        if file_path.exists() and file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(FRONTEND_DIST_DIR / "index.html")
