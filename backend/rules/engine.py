from typing import Any, Dict, List, Tuple
from backend.schemas import (
    ActionID,
    CandidateAction,
    HealthScores,
    RiskTier,
    SubsystemName,
)


class RulesEngine:
    """Deterministic rules engine mapping hardware telemetry to verified candidate optimizations."""

    def evaluate(self, inventory: Dict[str, Any]) -> Tuple[List[CandidateAction], HealthScores]:
        candidates: List[CandidateAction] = []
        
        cpu_score = 100
        gpu_score = 100
        ram_score = 100
        storage_score = 100
        power_score = 100

        # 1. CPU Rules
        cpu_data = inventory.get("CPU", {})
        active_plan = str(cpu_data.get("ActivePowerScheme", "")).lower()
        if "balanced" in active_plan:
            candidates.append(CandidateAction(
                action_id=ActionID.PWR_PLAN_PERF,
                subsystem=SubsystemName.CPU,
                tier=RiskTier.TIER_1,
                title_ar="تفعيل خطة الأداء العالي (High Performance Power Plan)",
                current_value="Balanced",
                proposed_value="High Performance",
                description_ar="يزيل تأخير رفع تردد المعالج أثناء أعباء العمل البرمجية وتجميع الأكواد الثقيلة.",
                requires_admin=False,
                requires_reboot=False
            ))
            cpu_score -= 10

        startup_count = cpu_data.get("StartupAppsCount", 0)
        if isinstance(startup_count, int) and startup_count > 10:
            candidates.append(CandidateAction(
                action_id=ActionID.STARTUP_DISABLE_APP,
                subsystem=SubsystemName.CPU,
                tier=RiskTier.TIER_1,
                title_ar="تحسين برامج بدء التشغيل وتقليل أعباء الإقلاع",
                current_value=f"{startup_count} برامج مسجلة",
                proposed_value="تعطيل البرامج غير الحيوية",
                description_ar="يقلل زمن الإقلاع بمقدار 15–35% ويوفر ما يصل إلى 1GB من الذاكرة العشوائية المستهلكة في الخلفية.",
                requires_admin=False,
                requires_reboot=False
            ))
            cpu_score -= 15

        # 2. GPU Rules
        gpu_data = inventory.get("GPU", {})
        hags_mode = gpu_data.get("HAGSMode")
        # If HAGS is explicitly disabled (1) or not set, and supported GPU exists
        controllers = gpu_data.get("Controllers", [])
        if isinstance(controllers, dict):
            controllers = [controllers]
        
        has_supported_gpu = any("nvidia" in str(c.get("Name", "")).lower() or "rtx" in str(c.get("Name", "")).lower() or "gtx" in str(c.get("Name", "")).lower() for c in controllers)
        if has_supported_gpu and hags_mode != 2:
            candidates.append(CandidateAction(
                action_id=ActionID.GPU_ENABLE_HAGS,
                subsystem=SubsystemName.GPU,
                tier=RiskTier.TIER_2,
                title_ar="تفعيل جدولة معالجة الرسوميات المسرعة بالعتاد (HAGS)",
                current_value="معطل (Disabled)",
                proposed_value="مفعل (Enabled)",
                description_ar="ينقل إدارة جدولة الإطارات من المعالج المركزي إلى معالج الرسوميات، مما يقلل زمن تأخير الإدخال وتذبذب الإطارات.",
                requires_admin=True,
                requires_reboot=True
            ))
            gpu_score -= 15

        # Check for Dual-GPU
        if len(controllers) >= 2:
            candidates.append(CandidateAction(
                action_id=ActionID.GPU_APP_PREFERENCE,
                subsystem=SubsystemName.GPU,
                tier=RiskTier.TIER_1,
                title_ar="توجيه التطبيقات البرمجية لبطاقة NVIDIA الرسومية المنفصلة",
                current_value="تلقائي (Windows Default)",
                proposed_value="High Performance (NVIDIA dGPU)",
                description_ar="يضمن تشغيل محركات التصيير وأدوات التطوير على البطاقة المنفصلة دون استنزاف البطاقة المدمجة.",
                requires_admin=False,
                requires_reboot=False
            ))

        # 3. RAM Rules
        ram_data = inventory.get("RAM", {})
        mm_agent = ram_data.get("MemoryManagement", {})
        if isinstance(mm_agent, dict) and mm_agent.get("MemoryCompression") is False:
            candidates.append(CandidateAction(
                action_id=ActionID.RAM_ENABLE_COMPRESS,
                subsystem=SubsystemName.RAM,
                tier=RiskTier.TIER_2,
                title_ar="تفعيل تقنية ضغط الذاكرة في نظام التشغيل (Memory Compression)",
                current_value="معطل (False)",
                proposed_value="مفعل (True)",
                description_ar="يحتفظ بالصفحات غير النشطة مضغوطة داخل الرام بدلاً من ترحيلها إلى القرص الصلب، مما يمنع بطء الاستجابة.",
                requires_admin=True,
                requires_reboot=False
            ))
            ram_score -= 20

        # 4. Storage Rules
        storage_data = inventory.get("Storage", {})
        trim_raw = str(storage_data.get("TrimStatusRaw", ""))
        disks = storage_data.get("Disks", [])
        if isinstance(disks, dict):
            disks = [disks]

        has_ssd = any("ssd" in str(d.get("MediaType", "")).lower() or "nvme" in str(d.get("BusType", "")).lower() for d in disks)
        has_hdd = any("hdd" in str(d.get("MediaType", "")).lower() or "sata" in str(d.get("BusType", "")).lower() for d in disks)

        if has_ssd and "disabledeletenotify = 1" in trim_raw.lower():
            candidates.append(CandidateAction(
                action_id=ActionID.STORAGE_ENABLE_TRIM,
                subsystem=SubsystemName.STORAGE,
                tier=RiskTier.TIER_1,
                title_ar="تفعيل بروتوكول TRIM لأقراص SSD / NVMe",
                current_value="معطل (DisableDeleteNotify = 1)",
                proposed_value="مفعل (DisableDeleteNotify = 0)",
                description_ar="يستعيد كتل الذاكرة غير المستخدمة في أقراص الفلاش، مما يحافظ على سرعة الكتابة القصوى ويطيل عمر القرص.",
                requires_admin=True,
                requires_reboot=False
            ))
            storage_score -= 25

        if has_ssd:
            candidates.append(CandidateAction(
                action_id=ActionID.STORAGE_RETRIM_SSD,
                subsystem=SubsystemName.STORAGE,
                tier=RiskTier.TIER_1,
                title_ar="تنفيذ صيانة ReTrim الآمنة لأقراص SSD (تحسين المساحة)",
                current_value="لم يتم التحسين مؤخراً",
                proposed_value="Optimize-Volume -ReTrim",
                description_ar="يعيد إخطار وحدة تحكم SSD بالكتل المحذوفة بأمان تام وبدون أي defragmentation مجهد لخلايا الذاكرة.",
                requires_admin=True,
                requires_reboot=False
            ))

        if has_hdd:
            candidates.append(CandidateAction(
                action_id=ActionID.STORAGE_DEFRAG_HDD,
                subsystem=SubsystemName.STORAGE,
                tier=RiskTier.TIER_1,
                title_ar="إلغاء تجزئة القرص الميكانيكي HDD (فصل مسار SSD)",
                current_value="تجزئة مسجلة في ملفات القرص الميكانيكي",
                proposed_value="Optimize-Volume -Defrag",
                description_ar="يرتب المسارات المغناطيسية للقرص الميكانيكي التقليدي فقط، مع حظر تشغيله على أقراص SSD/NVMe نهائياً.",
                requires_admin=True,
                requires_reboot=False
            ))

        candidates.append(CandidateAction(
            action_id=ActionID.STORAGE_CLEAN_TEMP,
            subsystem=SubsystemName.STORAGE,
            tier=RiskTier.TIER_1,
            title_ar="تنظيف الملفات المؤقتة القديمة ومخلفات التحديثات المنتهية",
            current_value="تراكم ملفات مؤقتة نظامية",
            proposed_value="حذف الملفات الأقدم من 3 أيام ضمن مسارات Allowlist",
            description_ar="يفرغ مساحة تخزينية حيوية لضمان بقاء نسبة لا تقل عن 15% مساحة حرة لازمة لتوزيع التآكل في أقراص SSD.",
            requires_admin=False,
            requires_reboot=False
        ))

        # 5. Power Rules
        power_data = inventory.get("PowerThermal", {})
        battery = power_data.get("Battery")
        if battery:
            power_score = 85
        else:
            power_score = 95

        overall_score = int((cpu_score + gpu_score + ram_score + storage_score + power_score) / 5)

        health_scores = HealthScores(
            overall=max(0, min(100, overall_score)),
            cpu=max(0, min(100, cpu_score)),
            gpu=max(0, min(100, gpu_score)),
            ram=max(0, min(100, ram_score)),
            storage=max(0, min(100, storage_score)),
            power=max(0, min(100, power_score))
        )

        return candidates, health_scores
