import os
import sqlite3
import json
from typing import Optional

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "cata.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS payments (
    job_id TEXT PRIMARY KEY,
    paid INTEGER NOT NULL DEFAULT 0,
    ts REAL,
    info TEXT
);
"""


def _get_conn():
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = _get_conn()
    with conn:
        conn.executescript(SCHEMA)
    conn.close()


def mark_paid(job_id: str, info: Optional[dict] = None):
    conn = _get_conn()
    with conn:
        conn.execute(
            "INSERT OR REPLACE INTO payments (job_id, paid, ts, info) VALUES (?, 1, ?, ?)",
            (job_id, float(__import__("time").time()), json.dumps(info or {}))
        )
    conn.close()


def is_paid(job_id: str) -> bool:
    conn = _get_conn()
    cur = conn.execute("SELECT paid FROM payments WHERE job_id = ?", (job_id,))
    row = cur.fetchone()
    conn.close()
    return bool(row and row["paid"]) 


def get_payment(job_id: str):
    conn = _get_conn()
    cur = conn.execute("SELECT job_id, paid, ts, info FROM payments WHERE job_id = ?", (job_id,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return None
    return {"job_id": row["job_id"], "paid": bool(row["paid"]), "ts": row["ts"], "info": json.loads(row["info"] or "{}")}
