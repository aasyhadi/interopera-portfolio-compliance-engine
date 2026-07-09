from __future__ import annotations
import json, sqlite3, hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

class AuditLog:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.path)
        self.conn.execute("PRAGMA foreign_keys=ON")
        self._init()

    def _init(self) -> None:
        self.conn.executescript("""
        CREATE TABLE IF NOT EXISTS audit_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            occurred_at TEXT NOT NULL,
            event_type TEXT NOT NULL,
            run_id TEXT NOT NULL,
            data_json TEXT NOT NULL,
            data_hash TEXT NOT NULL,
            prev_hash TEXT,
            chain_hash TEXT NOT NULL
        );
        CREATE TRIGGER IF NOT EXISTS audit_no_update
        BEFORE UPDATE ON audit_events
        BEGIN
            SELECT RAISE(ABORT, 'audit_events is append-only: UPDATE forbidden');
        END;
        CREATE TRIGGER IF NOT EXISTS audit_no_delete
        BEFORE DELETE ON audit_events
        BEGIN
            SELECT RAISE(ABORT, 'audit_events is append-only: DELETE forbidden');
        END;
        """)
        self.conn.commit()

    def append(self, event_type: str, run_id: str, data: Mapping[str, Any]) -> None:
        data_json = json.dumps(data, sort_keys=True, separators=(",", ":"))
        data_hash = hashlib.sha256(data_json.encode()).hexdigest()
        row = self.conn.execute("SELECT chain_hash FROM audit_events ORDER BY id DESC LIMIT 1").fetchone()
        prev_hash = row[0] if row else None
        chain_hash = hashlib.sha256(((prev_hash or "") + data_hash).encode()).hexdigest()
        self.conn.execute(
            "INSERT INTO audit_events(occurred_at,event_type,run_id,data_json,data_hash,prev_hash,chain_hash) VALUES(?,?,?,?,?,?,?)",
            (datetime.now(timezone.utc).isoformat(), event_type, run_id, data_json, data_hash, prev_hash, chain_hash),
        )
        self.conn.commit()

    def verify_append_only_triggers(self) -> dict[str, str]:
        try:
            self.conn.execute("UPDATE audit_events SET event_type=event_type WHERE id=-1")
            return {"update_trigger": "FAILED"}
        except sqlite3.DatabaseError as e:
            update = str(e)
        try:
            self.conn.execute("DELETE FROM audit_events WHERE id=-1")
            return {"delete_trigger": "FAILED"}
        except sqlite3.DatabaseError as e:
            delete = str(e)
        return {"update_trigger": update, "delete_trigger": delete}
