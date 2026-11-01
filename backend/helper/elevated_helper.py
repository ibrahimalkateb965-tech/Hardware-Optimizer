import argparse
import ctypes
import json
import logging
import os
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from backend.helper.allowlist import ACTION_DISPATCH_TABLE
from backend.schemas import ActionID, ActionResult

logger = logging.getLogger("elevated_helper")

def is_admin() -> bool:
    """Checks if the current process has administrative elevation on Windows."""
    if platform.system().lower() != "windows":
        return True  # For local Linux/WSL dev & tests
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        return False


def create_system_restore_point(session_id: str) -> bool:
    """Creates an official Windows System Restore Point prior to system changes."""
    if platform.system().lower() != "windows":
        logger.info(f"Non-Windows environment: simulated System Restore Point for {session_id}")
        return True

    cmd = [
        "powershell.exe", "-NoProfile", "-Command",
        f'Checkpoint-Computer -Description "HardwareOptimizer_{session_id}" -RestorePointType "MODIFY_SETTINGS"'
    ]
    try:
        proc = subprocess.run(cmd, stdin=subprocess.DEVNULL, capture_output=True, text=True, check=False)
        return proc.returncode == 0
    except Exception as e:
        logger.warning(f"Could not create System Restore Point: {e}")
        return False


def apply_action(action_id: ActionID) -> ActionResult:
    """Executes a single allowlisted action directly without shell interpolation."""
    spec = ACTION_DISPATCH_TABLE.get(action_id)
    if not spec:
        return ActionResult(
            action_id=action_id,
            success=False,
            message_ar="الإجراء غير موجود في قائمة الإجراءات المعتمدة (Allowlist)."
        )

    cmd = spec.get("apply_cmd")
    if not cmd:
        return ActionResult(
            action_id=action_id,
            success=True,
            message_ar="تم تطبيق الإجراء بدون أوامر طرفية."
        )

    try:
        # Strict binary execution with stdin decoupled
        proc = subprocess.run(
            cmd,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            check=False
        )
        success = proc.returncode == 0
        msg = f"تم التطبيق بنجاح: {spec.get('title_ar')}" if success else f"فشل التطبيق: {proc.stderr.strip() or proc.stdout.strip()}"
        return ActionResult(
            action_id=action_id,
            success=success,
            message_ar=msg,
            applied_state="Applied" if success else "Failed"
        )
    except Exception as e:
        return ActionResult(
            action_id=action_id,
            success=False,
            message_ar=f"خطأ أثناء التنفيذ: {e}"
        )


def rollback_action(action_id: ActionID) -> ActionResult:
    """Reverts a single allowlisted action using its predefined rollback command."""
    spec = ACTION_DISPATCH_TABLE.get(action_id)
    if not spec:
        return ActionResult(
            action_id=action_id,
            success=False,
            message_ar="الإجراء غير مسجل في الـ Allowlist للتراجع."
        )

    cmd = spec.get("rollback_cmd")
    if not cmd:
        return ActionResult(
            action_id=action_id,
            success=True,
            message_ar="هذا الإجراء صيانة لمرة واحدة ولا يتطلب تراجعاً برمجياً."
        )

    try:
        proc = subprocess.run(
            cmd,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            check=False
        )
        success = proc.returncode == 0
        msg = f"تم التراجع بنجاح: {spec.get('title_ar')}" if success else f"فشل التراجع: {proc.stderr.strip()}"
        return ActionResult(
            action_id=action_id,
            success=success,
            message_ar=msg,
            applied_state="RolledBack" if success else "RollbackFailed"
        )
    except Exception as e:
        return ActionResult(
            action_id=action_id,
            success=False,
            message_ar=f"خطأ أثناء التراجع: {e}"
        )


def main():
    parser = argparse.ArgumentParser(description="HardwareOptimizer Elevated Execution Helper")
    parser.add_argument("--mode", choices=["apply", "rollback"], required=True, help="Execution mode")
    parser.add_argument("--payload", type=str, required=True, help="Path to JSON execution ticket")
    args = parser.parse_args()

    payload_path = Path(args.payload)
    if not payload_path.exists():
        print(json.dumps({"error": f"Payload file not found: {payload_path}"}))
        sys.exit(1)

    with open(payload_path, "r", encoding="utf-8") as f:
        ticket = json.load(f)

    session_id = ticket.get("session_id", "sess_unknown")
    action_ids_raw = ticket.get("action_ids", [])
    
    results: List[ActionResult] = []

    if args.mode == "apply":
        # Create Restore Point before executing any modifications
        rp_success = create_system_restore_point(session_id)
        
        for raw_id in action_ids_raw:
            try:
                act_id = ActionID(raw_id)
                res = apply_action(act_id)
                results.append(res)
            except ValueError:
                results.append(ActionResult(
                    action_id=ActionID.PWR_PLAN_PERF, # placeholder
                    success=False,
                    message_ar=f"معرف إجراء غير صالح أو غير معتمد: {raw_id}"
                ))

        # Persist backup state to sessions folder
        session_dir = Path("sessions") / session_id
        session_dir.mkdir(parents=True, exist_ok=True)
        backup_file = session_dir / "state_backup.json"
        with open(backup_file, "w", encoding="utf-8") as f:
            json.dump({
                "session_id": session_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "restore_point_created": rp_success,
                "actions": [r.dict() for r in results]
            }, f, indent=2, ensure_ascii=False)

    elif args.mode == "rollback":
        for raw_id in action_ids_raw:
            try:
                act_id = ActionID(raw_id)
                res = rollback_action(act_id)
                results.append(res)
            except ValueError:
                pass

    output = {
        "session_id": session_id,
        "mode": args.mode,
        "results": [r.dict() for r in results]
    }
    print(json.dumps(output, ensure_ascii=False))

if __name__ == "__main__":
    main()
