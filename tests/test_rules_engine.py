import pytest
from backend.collectors.sandbox import get_sandbox_profile
from backend.rules.engine import RulesEngine
from backend.schemas import ActionID, RiskTier, SubsystemName

def test_rules_engine_default_profile():
    engine = RulesEngine()
    inventory = get_sandbox_profile("default")
    candidates, scores = engine.evaluate(inventory)
    
    assert len(candidates) > 0
    assert 0 <= scores.overall <= 100
    
    action_ids = [c.action_id for c in candidates]
    # Balanced power plan should trigger PWR_PLAN_PERF
    assert ActionID.PWR_PLAN_PERF in action_ids
    # Startup apps > 10 should trigger STARTUP_DISABLE_APP
    assert ActionID.STARTUP_DISABLE_APP in action_ids
    # SSD present should propose ReTrim
    assert ActionID.STORAGE_RETRIM_SSD in action_ids
    # HDD present should propose Defrag for HDD
    assert ActionID.STORAGE_DEFRAG_HDD in action_ids

def test_rules_engine_misconfigured_desktop():
    engine = RulesEngine()
    inventory = get_sandbox_profile("misconfigured_desktop")
    candidates, scores = engine.evaluate(inventory)
    
    action_ids = [c.action_id for c in candidates]
    # TRIM disabled should trigger STORAGE_ENABLE_TRIM
    assert ActionID.STORAGE_ENABLE_TRIM in action_ids
    # HAGS disabled with RTX 3080 should trigger GPU_ENABLE_HAGS
    assert ActionID.GPU_ENABLE_HAGS in action_ids
    # Memory compression disabled should trigger RAM_ENABLE_COMPRESS
    assert ActionID.RAM_ENABLE_COMPRESS in action_ids
    
    # Check that tier assignments match safety policy
    hags_cand = next(c for c in candidates if c.action_id == ActionID.GPU_ENABLE_HAGS)
    assert hags_cand.tier == RiskTier.TIER_2
    assert hags_cand.requires_admin is True
    assert hags_cand.requires_reboot is True

def test_no_defrag_on_ssd_only():
    engine = RulesEngine()
    inventory = {
        "CPU": {},
        "GPU": {},
        "RAM": {},
        "Storage": {
            "Disks": [{"FriendlyName": "NVMe 1TB", "MediaType": "SSD", "BusType": "NVMe"}]
        },
        "PowerThermal": {}
    }
    candidates, _ = engine.evaluate(inventory)
    action_ids = [c.action_id for c in candidates]
    
    # Defrag for HDD must NOT be present
    assert ActionID.STORAGE_DEFRAG_HDD not in action_ids
    # ReTrim for SSD must be present
    assert ActionID.STORAGE_RETRIM_SSD in action_ids
