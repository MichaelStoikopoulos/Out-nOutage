"""SQLite storage for outages and monitoring sessions."""

import json
import sqlite3
from datetime import datetime
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DB_PATH = DATA_DIR / "outages.db"
PENDING_PATH = DATA_DIR / "pending_outage.txt"


def get_conn():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    conn = get_conn()
    conn.execute(
        """CREATE TABLE IF NOT EXISTS outages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            start_ts TEXT NOT NULL,
            end_ts TEXT NOT NULL,
            duration_seconds REAL NOT NULL,
            kind TEXT NOT NULL DEFAULT 'unknown',
            gateway_ip TEXT
        )"""
    )
    conn.execute(
        """CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            start_ts TEXT NOT NULL
        )"""
    )
    # Migrate databases created before the local-vs-upstream classification existed.
    cols = {row[1] for row in conn.execute("PRAGMA table_info(outages)")}
    if "kind" not in cols:
        conn.execute("ALTER TABLE outages ADD COLUMN kind TEXT NOT NULL DEFAULT 'unknown'")
    if "gateway_ip" not in cols:
        conn.execute("ALTER TABLE outages ADD COLUMN gateway_ip TEXT")
    conn.commit()
    conn.close()


def start_session():
    conn = get_conn()
    cur = conn.execute(
        "INSERT INTO sessions (start_ts) VALUES (?)",
        (datetime.now().isoformat(timespec="seconds"),),
    )
    conn.commit()
    session_id = cur.lastrowid
    conn.close()
    return session_id


def get_last_session_start():
    conn = get_conn()
    row = conn.execute("SELECT start_ts FROM sessions ORDER BY id DESC LIMIT 1").fetchone()
    conn.close()
    return datetime.fromisoformat(row[0]) if row else None


def record_outage(start, end, duration, kind="unknown", gateway_ip=None):
    conn = get_conn()
    conn.execute(
        "INSERT INTO outages (start_ts, end_ts, duration_seconds, kind, gateway_ip) VALUES (?, ?, ?, ?, ?)",
        (start.isoformat(timespec="seconds"), end.isoformat(timespec="seconds"), duration, kind, gateway_ip),
    )
    conn.commit()
    conn.close()


def get_outages_since(dt):
    conn = get_conn()
    rows = conn.execute(
        "SELECT start_ts, end_ts, duration_seconds, kind FROM outages WHERE start_ts >= ? ORDER BY start_ts",
        (dt.isoformat(timespec="seconds"),),
    ).fetchall()
    conn.close()
    return rows


def get_all_outages():
    conn = get_conn()
    rows = conn.execute(
        "SELECT start_ts, end_ts, duration_seconds, kind FROM outages ORDER BY start_ts"
    ).fetchall()
    conn.close()
    return rows


def get_outages_grouped_by_day(limit_days=14):
    conn = get_conn()
    rows = conn.execute(
        """SELECT substr(start_ts, 1, 10) AS day, COUNT(*), SUM(duration_seconds)
           FROM outages GROUP BY day ORDER BY day DESC LIMIT ?""",
        (limit_days,),
    ).fetchall()
    conn.close()
    return rows


# --- Crash-recovery for an outage that was still in progress when the
# monitor process died (or the machine rebooted) ---------------------------

def save_pending_outage(down_since, kind="unknown", gateway_ip=None):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "down_since": down_since.isoformat(timespec="seconds"),
        "kind": kind,
        "gateway_ip": gateway_ip,
    }
    PENDING_PATH.write_text(json.dumps(payload))


def load_pending_outage():
    if not PENDING_PATH.exists():
        return None
    text = PENDING_PATH.read_text().strip()
    if not text:
        return None
    try:
        payload = json.loads(text)
        return {
            "down_since": datetime.fromisoformat(payload["down_since"]),
            "kind": payload.get("kind", "unknown"),
            "gateway_ip": payload.get("gateway_ip"),
        }
    except (json.JSONDecodeError, KeyError, ValueError):
        # Pending file from before this format existed (plain ISO timestamp).
        return {"down_since": datetime.fromisoformat(text), "kind": "unknown", "gateway_ip": None}


def clear_pending_outage():
    if PENDING_PATH.exists():
        PENDING_PATH.unlink()
