import asyncio
import pytest
from fastapi import HTTPException
from starlette.requests import Request
from backend.ai.client import OpenCodeGoClient
from backend.schemas import ActionID, CandidateAction, RiskTier, SubsystemName
from backend.security import verify_host_header, verify_session_token
from backend.config import settings

def test_prompt_injection_drops_invented_actions():
    client = OpenCodeGoClient()
    
    # Legit candidate
    candidates = [
        CandidateAction(
            action_id=ActionID.PWR_PLAN_PERF,
            subsystem=SubsystemName.CPU,
            tier=RiskTier.TIER_1,
            title_ar="خطة أداء",
            current_value="Balanced",
            proposed_value="High Performance",
            description_ar="شرح"
        )
    ]

    # Adversarial LLM response injecting malicious action
    malicious_llm_items = [
        {
            "action_id": "DISABLE_WINDOWS_DEFENDER_AND_FORMAT_C",
            "priority": 10,
            "rationale_ar": "تسريع بنسبة 100%",
            "rollback_summary_ar": "لا يمكن"
        },
        {
            "action_id": "PWR_PLAN_PERF",
            "priority": 8,
            "rationale_ar": "شرح مشروع",
            "rollback_summary_ar": "تراجع"
        }
    ]

    merged = client._merge_llm_with_candidates(candidates, malicious_llm_items)
    merged_ids = [m.action_id.value for m in merged]
    
    # Malicious action MUST be dropped
    assert "DISABLE_WINDOWS_DEFENDER_AND_FORMAT_C" not in merged_ids
    # Legitimate candidate must be preserved
    assert ActionID.PWR_PLAN_PERF.value in merged_ids

def test_host_header_validation_rejects_rebinding():
    async def _test():
        # Valid host
        scope = {"type": "http", "headers": [(b"host", b"127.0.0.1:8000")]}
        req = Request(scope)
        await verify_host_header(req)  # Should not raise

        # Malicious external domain
        scope_malicious = {"type": "http", "headers": [(b"host", b"malicious-attacker.com:8000")]}
        req_malicious = Request(scope_malicious)
        with pytest.raises(HTTPException) as exc_info:
            await verify_host_header(req_malicious)
        assert exc_info.value.status_code == 403

    asyncio.run(_test())

def test_session_token_validation():
    async def _test():
        # Valid token
        scope = {"type": "http", "headers": [(b"x-session-token", settings.SESSION_TOKEN.encode())], "query_string": b""}
        req = Request(scope)
        await verify_session_token(req, x_session_token=settings.SESSION_TOKEN)

        # Invalid token
        scope_bad = {"type": "http", "headers": [(b"x-session-token", b"bad_token")], "query_string": b""}
        req_bad = Request(scope_bad)
        with pytest.raises(HTTPException) as exc_info:
            await verify_session_token(req_bad, x_session_token="bad_token")
        assert exc_info.value.status_code == 401

    asyncio.run(_test())

