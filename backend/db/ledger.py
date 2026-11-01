import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from backend.config import settings
from backend.schemas import ActionID, ActionResult


from contextlib import contextmanager

class StateLedger:
    """ACID-compliant SQLite ledger for sessions, metrics snapshots, and rollback states."""

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or settings.DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    @contextmanager
    def _connection(self):
        conn = sqlite3.connect(str(self.db_path))
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA foreign_keys=ON;")
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _init_db(self) -> None:
        with self._connection() as conn:
            conn.executescript("""
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                status TEXT NOT NULL,
                restore_point_created INTEGER DEFAULT 0,
                health_score_before INTEGER,
                health_score_after INTEGER
            );

            CREATE TABLE IF NOT EXISTS applied_actions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                action_id TEXT NOT NULL,
                subsystem TEXT NOT NULL,
                tier INTEGER NOT NULL,
                previous_value TEXT,
                applied_value TEXT,
                status TEXT NOT NULL,
                applied_at TEXT NOT NULL,
                rolled_back_at TEXT,
                FOREIGN KEY (session_id) REFERENCES sessions(session_id)
            );

            CREATE TABLE IF NOT EXISTS metrics_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                phase TEXT NOT NULL, -- 'before' or 'after'
                cpu_percent REAL,
                ram_used_percent REAL,
                timestamp TEXT NOT NULL,
                FOREIGN KEY (session_id) REFERENCES sessions(session_id)
            );
            """)

    def create_session(self, session_id: str, health_score_before: int = 0) -> None:
        now_str = datetime.now(timezone.utc).isoformat()
        with self._connection() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO sessions (session_id, created_at, status, health_score_before) VALUES (?, ?, 'ACTIVE', ?)",
                (session_id, now_str, health_score_before)
            )

    def record_snapshot(self, session_id: str, phase: str, cpu_percent: float, ram_used_percent: float) -> None:
        now_str = datetime.now(timezone.utc).isoformat()
        with self._connection() as conn:
            conn.execute(
                "INSERT INTO metrics_snapshots (session_id, phase, cpu_percent, ram_used_percent, timestamp) VALUES (?, ?, ?, ?, ?)",
                (session_id, phase, cpu_percent, ram_used_percent, now_str)
            )

    def record_applied_actions(self, session_id: str, results: List[ActionResult], restore_point_created: bool = False) -> None:
        now_str = datetime.now(timezone.utc).isoformat()
        with self._connection() as conn:
            conn.execute(
                "UPDATE sessions SET restore_point_created = ?, status = 'COMPLETED' WHERE session_id = ?",
                (1 if restore_point_created else 0, session_id)
            )
            for res in results:
                conn.execute(
                    """
                    INSERT INTO applied_actions (session_id, action_id, subsystem, tier, applied_value, status, applied_at)
                    VALUES (?, ?, 'Auto', 1, ?, ?, ?)
                    """,
                    (session_id, res.action_id.value if hasattr(res.action_id, 'value') else str(res.action_id), res.applied_state or "Applied", "SUCCESS" if res.success else "FAILED", now_str)
                )

    def mark_actions_rolled_back(self, session_id: str, action_ids: List[ActionID]) -> None:
        now_str = datetime.now(timezone.utc).isoformat()
        with self._connection() as conn:
            for act_id in action_ids:
                conn.execute(
                    "UPDATE applied_actions SET status = 'ROLLED_BACK', rolled_back_at = ? WHERE session_id = ? AND action_id = ?",
                    (now_str, session_id, act_id.value)
                )

    def get_latest_session_id(self) -> Optional[str]:
        with self._connection() as conn:
            row = conn.execute("SELECT session_id FROM sessions ORDER BY created_at DESC LIMIT 1").fetchone()
            return row["session_id"] if row else None

    def get_session_history(self) -> List[Dict[str, Any]]:
        with self._connection() as conn:
            rows = conn.execute("SELECT * FROM sessions ORDER BY created_at DESC").fetchall()
            sessions = []
            for r in rows:
                sid = r["session_id"]
                actions = conn.execute("SELECT * FROM applied_actions WHERE session_id = ?", (sid,)).fetchall()
                sessions.append({
                    "session_id": sid,
                    "created_at": r["created_at"],
                    "status": r["status"],
                    "restore_point_created": bool(r["restore_point_created"]),
                    "actions": [dict(a) for a in actions]
                })
            return sessions
