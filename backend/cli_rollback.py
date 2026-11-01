import argparse
import json
import sys
from pathlib import Path
from backend.db.ledger import StateLedger
from backend.helper.elevated_helper import rollback_action
from backend.schemas import ActionID

def main():
    parser = argparse.ArgumentParser(description="HardwareOptimizer Emergency Standalone Rollback CLI")
    parser.add_argument("--session", type=str, default="latest", help="Session ID to rollback or 'latest'")
    args = parser.parse_args()

    ledger = StateLedger()
    target_session = args.session
    if target_session == "latest":
        target_session = ledger.get_latest_session_id()

    if not target_session:
        print("Error: No recorded optimization sessions found to rollback.")
        sys.exit(1)

    print(f"[*] Commencing Emergency Rollback for Session: {target_session}")

    # Read from session state_backup.json if exists
    backup_file = Path("sessions") / target_session / "state_backup.json"
    actions_to_revert = []

    if backup_file.exists():
        with open(backup_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            for act in data.get("actions", []):
                if act.get("success"):
                    actions_to_revert.append(ActionID(act["action_id"]))
    else:
        # Fallback to querying ledger
        with ledger._get_connection() as conn:
            rows = conn.execute(
                "SELECT action_id FROM applied_actions WHERE session_id = ? AND status = 'SUCCESS'",
                (target_session,)
            ).fetchall()
            actions_to_revert = [ActionID(r["action_id"]) for r in rows]

    if not actions_to_revert:
        print("No active applied actions found for this session.")
        sys.exit(0)

    success_count = 0
    reverted_ids = []
    for act_id in actions_to_revert:
        res = rollback_action(act_id)
        if res.success:
            print(f"[+] Reverted: {act_id.value} - {res.message_ar}")
            success_count += 1
            reverted_ids.append(act_id)
        else:
            print(f"[-] Failed to revert: {act_id.value} - {res.message_ar}")

    ledger.mark_actions_rolled_back(target_session, reverted_ids)
    print(f"\n[✓] Rollback finished: {success_count}/{len(actions_to_revert)} actions reverted successfully.")

if __name__ == "__main__":
    main()
