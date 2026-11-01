from typing import Any, Dict, List, Optional
from backend.schemas import ActionID

# Canonical Plan GUIDs
GUID_BALANCED = "381b4222-f694-41f0-9685-ff5bb260df2e"
GUID_HIGH_PERF = "8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c"

ACTION_DISPATCH_TABLE: Dict[ActionID, Dict[str, Any]] = {
    ActionID.PWR_PLAN_PERF: {
        "apply_cmd": ["powercfg.exe", "/setactive", GUID_HIGH_PERF],
        "rollback_cmd": ["powercfg.exe", "/setactive", GUID_BALANCED],
        "requires_admin": False,
        "title_ar": "تفعيل خطة الأداء العالي"
    },
    ActionID.PWR_PLAN_BALANCED: {
        "apply_cmd": ["powercfg.exe", "/setactive", GUID_BALANCED],
        "rollback_cmd": ["powercfg.exe", "/setactive", GUID_HIGH_PERF],
        "requires_admin": False,
        "title_ar": "تفعيل خطة الطاقة المتوازنة"
    },
    ActionID.GPU_ENABLE_HAGS: {
        "apply_cmd": ["reg.exe", "add", r"HKLM\SYSTEM\CurrentControlSet\Control\GraphicsDrivers", "/v", "HwSchMode", "/t", "REG_DWORD", "/d", "2", "/f"],
        "rollback_cmd": ["reg.exe", "add", r"HKLM\SYSTEM\CurrentControlSet\Control\GraphicsDrivers", "/v", "HwSchMode", "/t", "REG_DWORD", "/d", "1", "/f"],
        "requires_admin": True,
        "title_ar": "تفعيل جدولة معالجة الرسوميات المسرعة بالعتاد (HAGS)"
    },
    ActionID.RAM_ENABLE_COMPRESS: {
        "apply_cmd": ["powershell.exe", "-NoProfile", "-Command", "Enable-MMAgent -MemoryCompression"],
        "rollback_cmd": ["powershell.exe", "-NoProfile", "-Command", "Disable-MMAgent -MemoryCompression"],
        "requires_admin": True,
        "title_ar": "تفعيل ضغط الذاكرة في النظام"
    },
    ActionID.STORAGE_ENABLE_TRIM: {
        "apply_cmd": ["fsutil.exe", "behavior", "set", "DisableDeleteNotify", "0"],
        "rollback_cmd": ["fsutil.exe", "behavior", "set", "DisableDeleteNotify", "1"],
        "requires_admin": True,
        "title_ar": "تفعيل بروتوكول TRIM لأقراص SSD"
    },
    ActionID.STORAGE_RETRIM_SSD: {
        "apply_cmd": [
            "powershell.exe", "-NoProfile", "-Command",
            "if (Get-Volume -DriveLetter C -ErrorAction SilentlyContinue) { Optimize-Volume -DriveLetter C -ReTrim -Verbose } else { Write-Output 'Drive C is not present.' }"
        ],
        "rollback_cmd": None,  # Stateless maintenance
        "requires_admin": True,
        "title_ar": "إجراء ReTrim للقرص C"
    },
    ActionID.STORAGE_DEFRAG_HDD: {
        "apply_cmd": [
            "powershell.exe", "-NoProfile", "-Command",
            "if (Get-Volume -DriveLetter D -ErrorAction SilentlyContinue) { Optimize-Volume -DriveLetter D -Defrag -Verbose } else { Write-Output 'Drive D is not present on this system, skipping defrag.' }"
        ],
        "rollback_cmd": None,  # Stateless maintenance
        "requires_admin": True,
        "title_ar": "إلغاء تجزئة القرص الميكانيكي D"
    },
    ActionID.STORAGE_CLEAN_TEMP: {
        "apply_cmd": [
            "powershell.exe", "-NoProfile", "-Command",
            r"Get-ChildItem -Path $env:TEMP\* -Recurse -Force -ErrorAction SilentlyContinue | Where-Object { $_.LastWriteTime -lt (Get-Date).AddDays(-3) } | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue"
        ],
        "rollback_cmd": None,  # Stateless maintenance
        "requires_admin": False,
        "title_ar": "تنظيف الملفات المؤقتة القديمة"
    },
    ActionID.STARTUP_DISABLE_APP: {
        # App-specific startup disabled via StartupApproved registry key
        "requires_admin": False,
        "title_ar": "تعطيل برامج بدء التشغيل"
    },
    ActionID.GPU_APP_PREFERENCE: {
        # DirectX UserGpuPreferences
        "requires_admin": False,
        "title_ar": "تفضيل بطاقة الرسوميات لتطبيقات محددة"
    }
}


def is_action_allowed(action_id: ActionID) -> bool:
    return action_id in ACTION_DISPATCH_TABLE
