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
from typing import Any, Dict, List, Optional

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

    title = spec.get("title_ar", str(action_id))
    cmd = spec.get("apply_cmd")
    if not cmd:
        return ActionResult(
            action_id=action_id,
            success=True,
            message_ar=f"تم تطبيق الإجراء بنجاح: {title}."
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
        err_msg = proc.stderr.strip() or proc.stdout.strip() or f"رمز الخطأ (Exit Code: {proc.returncode})"
        msg = f"تم التطبيق بنجاح: {title}" if success else f"فشل التطبيق ({title}): {err_msg}"
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
            message_ar=f"خطأ أثناء التنفيذ ({title}): {e}"
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

    title = spec.get("title_ar", str(action_id))
    cmd = spec.get("rollback_cmd")
    if not cmd:
        return ActionResult(
            action_id=action_id,
            success=True,
            message_ar=f"هذا الإجراء صيانة لمرة واحدة ولا يتطلب تراجعاً برمجياً ({title})."
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
        err_msg = proc.stderr.strip() or proc.stdout.strip() or f"رمز الخطأ (Exit Code: {proc.returncode})"
        msg = f"تم التراجع بنجاح: {title}" if success else f"فشل التراجع ({title}): {err_msg}"
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
            message_ar=f"خطأ أثناء التراجع ({title}): {e}"
        )


def _launch_elevated_windows(executable: str, params: str, cwd: str) -> int:
    """Launches an elevated process on Windows via ShellExecuteExW or Start-Process and waits for it."""
    try:
        from ctypes import wintypes
        
        SEE_MASK_NOCLOSEPROCESS = 0x00000040
        INFINITE = 0xFFFFFFFF
        
        class SHELLEXECUTEINFO(ctypes.Structure):
            _fields_ = [
                ("cbSize", wintypes.DWORD),
                ("fMask", wintypes.ULONG),
                ("hwnd", wintypes.HWND),
                ("lpVerb", wintypes.LPCWSTR),
                ("lpFile", wintypes.LPCWSTR),
                ("lpParameters", wintypes.LPCWSTR),
                ("lpDirectory", wintypes.LPCWSTR),
                ("nShow", ctypes.c_int),
                ("hInstApp", wintypes.HINSTANCE),
                ("lpIDList", wintypes.LPVOID),
                ("lpClass", wintypes.LPCWSTR),
                ("hkeyClass", wintypes.HKEY),
                ("dwHotKey", wintypes.DWORD),
                ("hIconOrMonitor", wintypes.HANDLE),
                ("hProcess", wintypes.HANDLE)
            ]
            
        sei = SHELLEXECUTEINFO()
        sei.cbSize = ctypes.sizeof(SHELLEXECUTEINFO)
        sei.fMask = SEE_MASK_NOCLOSEPROCESS
        sei.hwnd = None
        sei.lpVerb = "runas"
        sei.lpFile = executable
        sei.lpParameters = params
        sei.lpDirectory = cwd
        sei.nShow = 1  # SW_SHOWNORMAL
        
        res = ctypes.windll.shell32.ShellExecuteExW(ctypes.byref(sei))
        if not res:
            err = ctypes.GetLastError()
            if err == 1223:  # ERROR_CANCELLED (user clicked "No" on UAC prompt)
                raise PermissionError("UAC_CANCELLED")
            raise RuntimeError(f"ShellExecuteExW failed with code {err}")
            
        hProcess = sei.hProcess
        if hProcess:
            try:
                ctypes.windll.kernel32.WaitForSingleObject(hProcess, INFINITE)
                exit_code = wintypes.DWORD()
                ctypes.windll.kernel32.GetExitCodeProcess(hProcess, ctypes.byref(exit_code))
                return exit_code.value
            finally:
                ctypes.windll.kernel32.CloseHandle(hProcess)
        return 0
    except PermissionError:
        raise
    except Exception as e:
        logger.warning(f"ShellExecuteExW failed, falling back to powershell Start-Process: {e}")
        cmd = [
            "powershell.exe", "-NoProfile", "-Command",
            f"Start-Process -FilePath '{executable}' -ArgumentList '{params}' -Verb RunAs -Wait"
        ]
        proc = subprocess.run(cmd, stdin=subprocess.DEVNULL, capture_output=True, text=True, check=False)
        if proc.returncode != 0:
            if "canceled by the user" in proc.stderr.lower():
                raise PermissionError("UAC_CANCELLED")
            raise RuntimeError(f"PowerShell elevation failed: {proc.stderr.strip()}")
        return proc.returncode


def _execute_direct(
    mode: str,
    session_id: str,
    action_ids: List[Any],
    result_file: Optional[Path] = None
) -> Dict[str, Any]:
    """Internal synchronous runner for actions (called directly or from elevated helper)."""
    results: List[ActionResult] = []
    rp_success = False

    if mode == "apply":
        rp_success = create_system_restore_point(session_id)
        for raw_id in action_ids:
            try:
                act_id = ActionID(raw_id) if not isinstance(raw_id, ActionID) else raw_id
                res = apply_action(act_id)
                results.append(res)
            except ValueError:
                results.append(ActionResult(
                    action_id=raw_id,
                    success=False,
                    message_ar=f"معرف إجراء غير صالح أو غير معتمد: {raw_id}"
                ))

        # Persist backup state to sessions folder for rollback
        session_dir = Path("sessions") / session_id
        session_dir.mkdir(parents=True, exist_ok=True)
        backup_file = session_dir / "state_backup.json"
        with open(backup_file, "w", encoding="utf-8") as f:
            json.dump({
                "session_id": session_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "restore_point_created": rp_success,
                "actions": [r.model_dump() if hasattr(r, "model_dump") else r.dict() for r in results]
            }, f, indent=2, ensure_ascii=False)

    elif mode == "rollback":
        for raw_id in action_ids:
            try:
                act_id = ActionID(raw_id) if not isinstance(raw_id, ActionID) else raw_id
                res = rollback_action(act_id)
                results.append(res)
            except ValueError:
                results.append(ActionResult(
                    action_id=raw_id,
                    success=False,
                    message_ar=f"معرف إجراء غير صالح أو غير مسجل للتراجع: {raw_id}"
                ))

    all_success = all(r.success for r in results) if results else True
    output = {
        "session_id": session_id,
        "mode": mode,
        "all_success": all_success,
        "restore_point_created": rp_success,
        "restore_point_id": f"HardwareOptimizer_{session_id}" if rp_success else None,
        "results": [r.model_dump() if hasattr(r, "model_dump") else r.dict() for r in results]
    }

    if result_file:
        with open(result_file, "w", encoding="utf-8") as f:
            json.dump(output, f, indent=2, ensure_ascii=False)

    return {
        "session_id": session_id,
        "mode": mode,
        "all_success": all_success,
        "restore_point_created": rp_success,
        "restore_point_id": f"HardwareOptimizer_{session_id}" if rp_success else None,
        "results": results
    }


def execute_actions(
    mode: str,
    session_id: str,
    action_ids: List[Any]
) -> Dict[str, Any]:
    """
    Executes a batch of actions (apply or rollback).
    If running non-elevated on Windows and any action requires admin privileges,
    spawns elevated_helper via Windows UAC dialog (runas) and collects execution output.
    """
    is_win = platform.system().lower() == "windows"
    admin = is_admin()

    # Determine if elevation is required
    needs_admin = False
    if is_win:
        if mode == "apply":
            needs_admin = any(
                ACTION_DISPATCH_TABLE.get(aid if isinstance(aid, ActionID) else ActionID(aid), {}).get("requires_admin", False)
                for aid in action_ids if aid in ActionID._value2member_map_ or isinstance(aid, ActionID)
            )
        elif mode == "rollback":
            needs_admin = any(
                ACTION_DISPATCH_TABLE.get(aid if isinstance(aid, ActionID) else ActionID(aid), {}).get("requires_admin", False)
                for aid in action_ids if aid in ActionID._value2member_map_ or isinstance(aid, ActionID)
            )

    # Session directory and ticket/result file paths
    session_dir = Path("sessions") / session_id
    session_dir.mkdir(parents=True, exist_ok=True)
    ticket_file = session_dir / f"ticket_{mode}.json"
    result_file = session_dir / f"result_{mode}.json"

    ticket_data = {
        "session_id": session_id,
        "mode": mode,
        "action_ids": [a.value if isinstance(a, ActionID) else str(a) for a in action_ids]
    }
    with open(ticket_file, "w", encoding="utf-8") as f:
        json.dump(ticket_data, f, indent=2, ensure_ascii=False)

    # Case A: Elevation required on Windows and current process is standard user
    if is_win and needs_admin and not admin:
        try:
            if result_file.exists():
                result_file.unlink()

            python_exe = sys.executable
            params = f'-m backend.helper.elevated_helper --mode {mode} --payload "{ticket_file.resolve()}"'
            cwd = str(Path.cwd().resolve())

            _launch_elevated_windows(python_exe, params, cwd)

            if result_file.exists():
                with open(result_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    results = [ActionResult(**r) if isinstance(r, dict) else r for r in data.get("results", [])]
                    return {
                        "session_id": session_id,
                        "mode": mode,
                        "all_success": data.get("all_success", False),
                        "restore_point_created": data.get("restore_point_created", False),
                        "restore_point_id": data.get("restore_point_id"),
                        "results": results
                    }
            else:
                return {
                    "session_id": session_id,
                    "mode": mode,
                    "all_success": False,
                    "restore_point_created": False,
                    "restore_point_id": None,
                    "results": [
                        ActionResult(
                            action_id=aid,
                            success=False,
                            message_ar="لم يتم استلام تقرير التنفيذ من معالج الصلاحيات المرتفعة."
                        ) for aid in action_ids
                    ]
                }
        except PermissionError:
            return {
                "session_id": session_id,
                "mode": mode,
                "all_success": False,
                "restore_point_created": False,
                "restore_point_id": None,
                "results": [
                    ActionResult(
                        action_id=aid,
                        success=False,
                        message_ar="تم إلغاء أو رفض منح صلاحيات المسؤول (UAC) المطلوبة لتطبيق هذا الإجراء."
                    ) for aid in action_ids
                ]
            }
        except Exception as e:
            logger.error(f"Failed to launch elevated helper: {e}")
            return {
                "session_id": session_id,
                "mode": mode,
                "all_success": False,
                "restore_point_created": False,
                "restore_point_id": None,
                "results": [
                    ActionResult(
                        action_id=aid,
                        success=False,
                        message_ar=f"فشل تشغيل معالج الصلاحيات المرتفعة: {e}"
                    ) for aid in action_ids
                ]
            }

    # Case B: Already elevated, non-Windows, or no admin required
    return _execute_direct(mode, session_id, action_ids, result_file)


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
    
    result_file = payload_path.parent / f"result_{args.mode}.json"
    out = _execute_direct(args.mode, session_id, action_ids_raw, result_file)

    # Print output to stdout
    print(json.dumps({
        "session_id": out["session_id"],
        "mode": out["mode"],
        "all_success": out["all_success"],
        "restore_point_created": out["restore_point_created"],
        "restore_point_id": out["restore_point_id"],
        "results": [r.model_dump() if hasattr(r, "model_dump") else (r.dict() if hasattr(r, "dict") else r) for r in out["results"]]
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
