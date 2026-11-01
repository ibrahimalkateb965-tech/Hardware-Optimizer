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
from backend.helper.elevated_helper import apply_action, create_system_restore_point, rollback_action
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

# CORS restricted strictly to localhost
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        f"http://127.0.0.1:{settings.PORT}",
        f"http://localhost:{settings.PORT}",
        "http://127.0.0.1:5173",  # Vite Dev
        "http://localhost:5173",
    ],
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


@app.get("/api/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": "1.0.0",
        "sandbox_mode": settings.SANDBOX_MODE,
        "session_token": settings.SESSION_TOKEN
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
async def get_inventory(sandbox: bool = False, profile: str = "default"):
    """Collects comprehensive 5-subsystem inventory with 3.0s timeout envelopes."""
    return await orchestrator.get_full_inventory(force_sandbox=sandbox, profile_name=profile)


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
    """Executes validated allowlisted actions with automatic System Restore Point."""
    if not req.selected_action_ids:
        raise HTTPException(status_code=400, detail="No optimization actions selected.")

    # 1. System Restore Point
    rp_created = create_system_restore_point(req.session_id)
    
    # 2. Execute actions
    results: List[ActionResult] = []
    all_success = True
    for action_id in req.selected_action_ids:
        res = apply_action(action_id)
        results.append(res)
        if not res.success:
            all_success = False

    # 3. Record in ledger
    ledger.record_applied_actions(req.session_id, results, restore_point_created=rp_created)
    
    # Record post-apply snapshot
    mem = psutil.virtual_memory()
    ledger.record_snapshot(
        session_id=req.session_id,
        phase="after",
        cpu_percent=psutil.cpu_percent(interval=None),
        ram_used_percent=mem.percent
    )

    return ApplyResponse(
        session_id=req.session_id,
        success=all_success,
        results=results,
        restore_point_created=rp_created,
        restore_point_id=f"HardwareOptimizer_{req.session_id}" if rp_created else None
    )


@app.post("/api/rollback", response_model=RollbackResponse)
async def rollback_optimizations(
    req: RollbackRequest,
    _=Depends(verify_session_token)
):
    """Reverts applied optimizations for a session."""
    target_actions = req.target_action_ids
    if not target_actions:
        # Load from ledger history
        history = ledger.get_session_history()
        session_info = next((s for s in history if s["session_id"] == req.session_id), None)
        if not session_info:
            raise HTTPException(status_code=404, detail="Session not found in ledger.")
        target_actions = [ActionID(a["action_id"]) for a in session_info.get("actions", [])]

    results: List[ActionResult] = []
    reverted_ids: List[ActionID] = []
    for act_id in target_actions:
        res = rollback_action(act_id)
        results.append(res)
        if res.success:
            reverted_ids.append(act_id)

    ledger.mark_actions_rolled_back(req.session_id, reverted_ids)

    return RollbackResponse(
        session_id=req.session_id,
        success=all(r.success for r in results),
        results=results
    )


@app.get("/api/history")
async def get_history():
    """Returns past optimization sessions and rollback ledger."""
    return {"sessions": ledger.get_session_history()}


# Mount static frontend build if dist exists
if FRONTEND_DIST_DIR.exists():
    app.mount("/assets", StaticFiles(directory=str(FRONTEND_DIST_DIR / "assets")), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        file_path = FRONTEND_DIST_DIR / full_path
        if file_path.exists() and file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(FRONTEND_DIST_DIR / "index.html")
