"""Derived-result storage. Raw uploads are not kept after a run completes."""

from __future__ import annotations

import json
import os
import sqlite3
import threading
import time
import uuid
from datetime import datetime, timezone
from typing import Any

JOB_TTL_S = int(os.environ.get("JANUS_JOB_TTL_S", str(30 * 60)))
MAX_JOBS = int(os.environ.get("JANUS_MAX_JOBS", "8"))


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


class RunStore:
    def create(self, record: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError

    def get(self, run_id: str) -> dict[str, Any] | None:
        raise NotImplementedError

    def update(self, run_id: str, **fields: Any) -> dict[str, Any]:
        raise NotImplementedError

    def list(self) -> list[dict[str, Any]]:
        raise NotImplementedError

    def drop_raw(self, run_id: str) -> None:
        raise NotImplementedError

    def purge(self) -> None:
        raise NotImplementedError


class MemoryStore(RunStore):
    def __init__(self) -> None:
        self._runs: dict[str, dict[str, Any]] = {}
        self._lock = threading.Lock()

    def create(self, record: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            run_id = record.get("id") or f"run_{uuid.uuid4().hex[:12]}"
            record["id"] = run_id
            record.setdefault("created_at", now())
            record.setdefault("updated_at", record["created_at"])
            record.setdefault("created_by", "local-user")
            record.setdefault("created_ts", time.time())
            self._runs[run_id] = record
            self._purge_locked()
            return record

    def get(self, run_id: str) -> dict[str, Any] | None:
        with self._lock:
            self._purge_locked()
            rec = self._runs.get(run_id)
            return None if rec is None else dict(rec)

    def update(self, run_id: str, **fields: Any) -> dict[str, Any]:
        with self._lock:
            rec = self._runs[run_id]
            rec.update(fields)
            rec["updated_at"] = now()
            return dict(rec)

    def list(self) -> list[dict[str, Any]]:
        with self._lock:
            self._purge_locked()
            rows = []
            for rec in self._runs.values():
                rows.append({k: rec.get(k) for k in ("id", "name", "status", "mode", "created_at", "updated_at", "conclusion")})
            rows.sort(key=lambda r: r.get("created_at") or "", reverse=True)
            return rows

    def drop_raw(self, run_id: str) -> None:
        with self._lock:
            rec = self._runs.get(run_id)
            if not rec:
                return
            for key in ("estimator", "holdout", "holdout_raw", "wrapped", "model_bytes", "holdout_bytes"):
                rec.pop(key, None)

    def purge(self) -> None:
        with self._lock:
            self._purge_locked()

    def _purge_locked(self) -> None:
        cutoff = time.time() - JOB_TTL_S
        dead = [k for k, r in self._runs.items() if r.get("created_ts", time.time()) < cutoff]
        for k in dead:
            self._runs.pop(k, None)
        while len(self._runs) > MAX_JOBS:
            oldest = min(self._runs, key=lambda k: self._runs[k].get("created_ts", 0))
            self._runs.pop(oldest, None)


class SQLiteStore(RunStore):
    def __init__(self, path: str) -> None:
        self.path = path
        self._mem = MemoryStore()
        self._init()

    def _conn(self) -> sqlite3.Connection:
        con = sqlite3.connect(self.path)
        con.execute(
            "CREATE TABLE IF NOT EXISTS runs (id TEXT PRIMARY KEY, created_at TEXT, payload TEXT)"
        )
        return con

    def _init(self) -> None:
        with self._conn() as con:
            pass

    def create(self, record: dict[str, Any]) -> dict[str, Any]:
        rec = self._mem.create(record)
        self._persist(rec)
        return rec

    def get(self, run_id: str) -> dict[str, Any] | None:
        rec = self._mem.get(run_id)
        if rec:
            return rec
        with self._conn() as con:
            row = con.execute("SELECT payload FROM runs WHERE id=?", (run_id,)).fetchone()
        if not row:
            return None
        rec = json.loads(row[0])
        self._mem.create(rec)
        return rec

    def update(self, run_id: str, **fields: Any) -> dict[str, Any]:
        rec = self._mem.update(run_id, **fields)
        self._persist(rec)
        return rec

    def list(self) -> list[dict[str, Any]]:
        listed = self._mem.list()
        if listed:
            return listed
        with self._conn() as con:
            rows = con.execute("SELECT payload FROM runs ORDER BY created_at DESC").fetchall()
        return [{k: json.loads(r[0]).get(k) for k in ("id", "name", "status", "mode", "created_at", "updated_at", "conclusion")} for r in rows]

    def drop_raw(self, run_id: str) -> None:
        self._mem.drop_raw(run_id)
        rec = self._mem.get(run_id)
        if rec:
            self._persist(rec)

    def purge(self) -> None:
        self._mem.purge()

    def _persist(self, rec: dict[str, Any]) -> None:
        safe = {k: v for k, v in rec.items() if k not in {"estimator", "holdout", "holdout_raw", "wrapped", "model_bytes", "holdout_bytes"}}
        with self._conn() as con:
            con.execute(
                "INSERT OR REPLACE INTO runs(id, created_at, payload) VALUES (?,?,?)",
                (rec["id"], rec.get("created_at"), json.dumps(safe, default=str)),
            )


def build_store() -> RunStore:
    path = os.environ.get("JANUS_DB_PATH")
    if path:
        return SQLiteStore(path)
    return MemoryStore()
