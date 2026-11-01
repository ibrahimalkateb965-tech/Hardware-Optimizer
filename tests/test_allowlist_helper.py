import pytest
from backend.helper.allowlist import ACTION_DISPATCH_TABLE, is_action_allowed
from backend.helper.elevated_helper import apply_action, rollback_action
from backend.schemas import ActionID

def test_all_enum_actions_have_dispatch_entry():
    for act in ActionID:
        assert act in ACTION_DISPATCH_TABLE
        assert is_action_allowed(act) is True

def test_no_shell_true_in_dispatch_commands():
    for act_id, spec in ACTION_DISPATCH_TABLE.items():
        apply_cmd = spec.get("apply_cmd")
        rollback_cmd = spec.get("rollback_cmd")
        if apply_cmd:
            assert isinstance(apply_cmd, list), f"{act_id} apply_cmd must be a list of arguments, not a string"
        if rollback_cmd:
            assert isinstance(rollback_cmd, list), f"{act_id} rollback_cmd must be a list of arguments, not a string"

def test_invalid_action_rejected():
    res = apply_action("MALICIOUS_INVENTED_ACTION") # type: ignore
    assert res.success is False
    assert "غير معتمد" in res.message_ar or "غير موجود" in res.message_ar

def test_apply_and_rollback_execution():
    # Test stateless maintenance action
    res = apply_action(ActionID.STORAGE_CLEAN_TEMP)
    assert isinstance(res.success, bool)

    res_rb = rollback_action(ActionID.STORAGE_CLEAN_TEMP)
    assert res_rb.success is True  # Stateless returns True with informative note
