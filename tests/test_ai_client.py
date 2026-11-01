import pytest
from backend.ai.client import OpenCodeGoClient
from backend.schemas import ActionID, CandidateAction, RiskTier, SubsystemName

def test_ai_client_local_fallback():
    client = OpenCodeGoClient()
    # Ensure key is empty for local fallback test
    client.api_key = ""

    candidates = [
        CandidateAction(
            action_id=ActionID.STORAGE_ENABLE_TRIM,
            subsystem=SubsystemName.STORAGE,
            tier=RiskTier.TIER_1,
            title_ar="TRIM",
            current_value="0",
            proposed_value="1",
            description_ar="تفعيل تريم"
        ),
        CandidateAction(
            action_id=ActionID.GPU_ENABLE_HAGS,
            subsystem=SubsystemName.GPU,
            tier=RiskTier.TIER_2,
            title_ar="HAGS",
            current_value="1",
            proposed_value="2",
            description_ar="تفعيل HAGS"
        )
    ]

    recs = client._local_fallback(candidates)
    assert len(recs) == 2
    # Tier 1 should be prioritized before Tier 2 in fallback
    assert recs[0].tier == RiskTier.TIER_1
    assert recs[0].action_id == ActionID.STORAGE_ENABLE_TRIM
