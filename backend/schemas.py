from enum import Enum
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field


class SubsystemName(str, Enum):
    CPU = "CPU"
    GPU = "GPU"
    RAM = "RAM"
    STORAGE = "Storage"
    POWER = "PowerThermal"


class RiskTier(int, Enum):
    TIER_0 = 0  # Report-only advisory
    TIER_1 = 1  # Safe, low-risk, instantly reversible
    TIER_2 = 2  # Requires explicit confirmation / reboot / elevated
    TIER_3 = 3  # Forbidden - not permitted in code


class ActionID(str, Enum):
    PWR_PLAN_PERF = "PWR_PLAN_PERF"
    PWR_PLAN_BALANCED = "PWR_PLAN_BALANCED"
    STARTUP_DISABLE_APP = "STARTUP_DISABLE_APP"
    GPU_ENABLE_HAGS = "GPU_ENABLE_HAGS"
    GPU_APP_PREFERENCE = "GPU_APP_PREFERENCE"
    RAM_ENABLE_COMPRESS = "RAM_ENABLE_COMPRESS"
    STORAGE_ENABLE_TRIM = "STORAGE_ENABLE_TRIM"
    STORAGE_RETRIM_SSD = "STORAGE_RETRIM_SSD"
    STORAGE_DEFRAG_HDD = "STORAGE_DEFRAG_HDD"
    STORAGE_CLEAN_TEMP = "STORAGE_CLEAN_TEMP"


class LiveTelemetry(BaseModel):
    timestamp: float
    cpu_percent: float
    cpu_cores: List[float] = Field(default_factory=list)
    cpu_freq_mhz: Optional[float] = None
    ram_total_bytes: int
    ram_available_bytes: int
    ram_used_percent: float
    gpu_telemetry: List[Dict[str, Any]] = Field(default_factory=list)
    disk_read_bytes_sec: float = 0.0
    disk_write_bytes_sec: float = 0.0


class HardwareInventory(BaseModel):
    collected_at: str
    operating_system: Dict[str, Any] = Field(default_factory=dict)
    computer_system: Dict[str, Any] = Field(default_factory=dict)
    cpu: Dict[str, Any] = Field(default_factory=dict)
    gpu: Dict[str, Any] = Field(default_factory=dict)
    ram: Dict[str, Any] = Field(default_factory=dict)
    storage: Dict[str, Any] = Field(default_factory=dict)
    power_thermal: Dict[str, Any] = Field(default_factory=dict)


class CandidateAction(BaseModel):
    action_id: ActionID
    subsystem: SubsystemName
    tier: RiskTier
    title_ar: str
    current_value: str
    proposed_value: str
    description_ar: str
    requires_admin: bool = False
    requires_reboot: bool = False
    target_identifier: Optional[str] = None  # e.g., app name, drive letter


class Recommendation(BaseModel):
    action_id: ActionID
    subsystem: SubsystemName
    tier: RiskTier
    title_ar: str
    current_value: str
    proposed_value: str
    priority: int = Field(ge=1, le=10, default=5)
    rationale_ar: str
    rollback_summary_ar: str
    requires_admin: bool = False
    requires_reboot: bool = False
    target_identifier: Optional[str] = None


class HealthScores(BaseModel):
    overall: int = Field(ge=0, le=100)
    cpu: int = Field(ge=0, le=100)
    gpu: int = Field(ge=0, le=100)
    ram: int = Field(ge=0, le=100)
    storage: int = Field(ge=0, le=100)
    power: int = Field(ge=0, le=100)


class RecommendationsResponse(BaseModel):
    session_id: str
    health_scores: HealthScores
    recommendations: List[Recommendation]
    llm_assisted: bool = True
    notice_ar: Optional[str] = None


class ApplyRequest(BaseModel):
    session_id: str
    selected_action_ids: List[ActionID]
    target_identifiers: Optional[Dict[str, str]] = None


class ActionResult(BaseModel):
    action_id: Union[ActionID, str]
    success: bool
    message_ar: str
    previous_state: Optional[str] = None
    applied_state: Optional[str] = None


class ApplyResponse(BaseModel):
    session_id: str
    success: bool
    results: List[ActionResult]
    restore_point_created: bool
    restore_point_id: Optional[str] = None


class RollbackRequest(BaseModel):
    session_id: str
    target_action_ids: Optional[List[ActionID]] = None


class RollbackResponse(BaseModel):
    session_id: str
    success: bool
    results: List[ActionResult]
