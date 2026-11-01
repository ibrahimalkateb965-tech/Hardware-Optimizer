import tempfile
from pathlib import Path
from backend.db.ledger import StateLedger
from backend.schemas import ActionID, ActionResult

def test_ledger_session_and_rollback_flow():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_ledger.db"
        ledger = StateLedger(db_path=db_path)

        session_id = "sess_test_001"
        ledger.create_session(session_id, health_score_before=75)

        # Record metrics snapshot
        ledger.record_snapshot(session_id, "before", cpu_percent=15.0, ram_used_percent=55.0)

        # Record applied actions
        results = [
            ActionResult(
                action_id=ActionID.PWR_PLAN_PERF,
                success=True,
                message_ar="تم تفعيل الأداء العالي",
                applied_state="Applied"
            )
        ]
        ledger.record_applied_actions(session_id, results, restore_point_created=True)
        ledger.record_snapshot(session_id, "after", cpu_percent=5.0, ram_used_percent=48.0)
        ledger.update_session_health_after(session_id, 90)

        # Verify comparison retrieval
        comp = ledger.get_comparison(session_id)
        assert comp is not None
        assert comp["health_score_before"] == 75
        assert comp["health_score_after"] == 90
        assert comp["before"]["cpu_percent"] == 15.0
        assert comp["after"]["cpu_percent"] == 5.0
        assert comp["before"]["ram_used_percent"] == 55.0
        assert comp["after"]["ram_used_percent"] == 48.0
        assert len(comp["actions"]) == 1

        history = ledger.get_session_history()
        assert len(history) == 1
        assert history[0]["session_id"] == session_id
        assert history[0]["restore_point_created"] is True
        assert len(history[0]["actions"]) == 1

        # Mark rolled back
        ledger.mark_actions_rolled_back(session_id, [ActionID.PWR_PLAN_PERF])
        updated_history = ledger.get_session_history()
        assert updated_history[0]["actions"][0]["status"] == "ROLLED_BACK"
