from unittest import mock

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

import backend.helper.elevated_helper as eh
import backend.main as main
from backend.config import settings
from backend.schemas import ActionID, ActionResult, ApplyRequest, RollbackRequest

MALICIOUS_SESSION_IDS = [
    'x"; Start-Process calc; "',
    "x'; Start-Process calc; '",
    "$(Start-Process calc)",
    "..\\..\\Windows\\Temp",
    "../../etc",
    "C:\\Windows\\Temp\\pwn",
    "a b",
    "",
]


@pytest.mark.parametrize("bad_id", MALICIOUS_SESSION_IDS)
def test_request_models_reject_unsafe_session_ids(bad_id):
    with pytest.raises(ValidationError):
        ApplyRequest(session_id=bad_id, selected_action_ids=[ActionID.PWR_PLAN_PERF])
    with pytest.raises(ValidationError):
        RollbackRequest(session_id=bad_id)


@pytest.mark.parametrize("bad_id", MALICIOUS_SESSION_IDS)
def test_helper_rejects_unsafe_session_ids_before_any_side_effect(bad_id):
    with mock.patch.object(eh.subprocess, "run") as run, mock.patch.object(eh.platform, "system", return_value="Windows"):
        with pytest.raises(ValueError):
            eh.create_system_restore_point(bad_id)
        with pytest.raises(ValueError):
            eh.execute_actions(mode="apply", session_id=bad_id, action_ids=[ActionID.PWR_PLAN_PERF])
        run.assert_not_called()


def test_restore_point_command_uses_single_quoted_literal():
    captured = {}

    def fake_run(cmd, **kwargs):
        captured["cmd"] = cmd
        return mock.Mock(returncode=0)

    with mock.patch.object(eh.subprocess, "run", side_effect=fake_run), mock.patch.object(eh.platform, "system", return_value="Windows"):
        assert eh.create_system_restore_point("sess_20261101_120000") is True
    assert "-Description 'HardwareOptimizer_sess_20261101_120000'" in captured["cmd"][-1]


def test_ps_quote_escapes_single_quotes():
    assert eh._ps_quote("C:\\O'Brien\\python.exe") == "'C:\\O''Brien\\python.exe'"


def test_health_endpoint_does_not_leak_token():
    client = TestClient(main.app)
    res = client.get("/api/health")
    assert res.status_code == 200
    assert "session_token" not in res.json()
    assert settings.SESSION_TOKEN not in res.text


def test_cors_rejects_other_local_ports():
    client = TestClient(main.app)
    other_origin = f"http://localhost:{settings.PORT + 1}"
    res = client.get("/api/health", headers={"Origin": other_origin})
    assert res.headers.get("access-control-allow-origin") != other_origin


def test_apply_with_zero_successes_does_not_raise_health_score():
    fake_ledger = mock.Mock()
    fake_ledger.get_session.return_value = {"session_id": "sess_x", "health_score_before": 60}
    failed = {
        "all_success": False,
        "restore_point_created": False,
        "restore_point_id": None,
        "results": [ActionResult(action_id=ActionID.PWR_PLAN_PERF, success=False, message_ar="UAC cancelled")],
    }
    with mock.patch.object(main, "ledger", fake_ledger), \
         mock.patch.object(main, "execute_actions", return_value=failed), \
         mock.patch.object(main.psutil, "cpu_percent", return_value=3.0):
        client = TestClient(main.app)
        res = client.post(
            "/api/apply",
            json={"session_id": "sess_x", "selected_action_ids": [ActionID.PWR_PLAN_PERF.value]},
            headers={"X-Session-Token": settings.SESSION_TOKEN},
        )
    assert res.status_code == 200
    fake_ledger.update_session_health_after.assert_called_once_with("sess_x", 60)


def test_apply_unknown_session_returns_404():
    fake_ledger = mock.Mock()
    fake_ledger.get_session.return_value = None
    with mock.patch.object(main, "ledger", fake_ledger), mock.patch.object(main, "execute_actions") as ex:
        client = TestClient(main.app)
        res = client.post(
            "/api/apply",
            json={"session_id": "sess_missing", "selected_action_ids": [ActionID.PWR_PLAN_PERF.value]},
            headers={"X-Session-Token": settings.SESSION_TOKEN},
        )
    assert res.status_code == 404
    ex.assert_not_called()
