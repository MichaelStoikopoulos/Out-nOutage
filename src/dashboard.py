"""Local web dashboard: a tiny stdlib HTTP server over the outage database.

Runs on localhost only. No external dependencies, no CDN assets in the
page it serves -- an internet-outage tool that needed the internet to
render its own dashboard would be a bit much.
"""

import json
import webbrowser
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from src import checker, db
from src.monitor import format_duration

TEMPLATE_PATH = Path(__file__).resolve().parent / "dashboard.html"


def _summarize(rows):
    count = len(rows)
    total = sum(r[2] for r in rows)
    longest = max((r[2] for r in rows), default=0)
    return {"count": count, "total_downtime": total, "longest": longest}


def _outage_dict(row):
    start_ts, end_ts, duration = row
    return {
        "start": start_ts,
        "end": end_ts,
        "duration_seconds": duration,
        "duration_label": format_duration(duration),
    }


def build_data():
    db.init_db()
    now = datetime.now()
    up = checker.is_connected()

    start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_rows = db.get_outages_since(start_of_day)

    session_start = db.get_last_session_start()
    session_rows = db.get_outages_since(session_start) if session_start else []

    all_rows = db.get_all_outages()

    day_rows = db.get_outages_grouped_by_day(limit_days=14)
    days = [
        {"day": day, "count": count, "downtime": total or 0.0}
        for day, count, total in reversed(day_rows)
    ]

    pending = db.load_pending_outage()

    session_summary = _summarize(session_rows)
    if session_start:
        elapsed = (now - session_start).total_seconds()
        session_summary["uptime_pct"] = (
            100 * (1 - session_summary["total_downtime"] / elapsed) if elapsed > 0 else 100.0
        )
        session_summary["started_at"] = session_start.isoformat(timespec="seconds")
    else:
        session_summary["uptime_pct"] = 100.0
        session_summary["started_at"] = None

    return {
        "generated_at": now.isoformat(timespec="seconds"),
        "status": "up" if up else "down",
        "pending_outage": (
            {
                "since": pending.isoformat(timespec="seconds"),
                "elapsed_seconds": (now - pending).total_seconds(),
            }
            if pending
            else None
        ),
        "today": {
            **_summarize(today_rows),
            "date": start_of_day.strftime("%Y-%m-%d"),
        },
        "session": session_summary,
        "all_time": _summarize(all_rows),
        "days": days,
        "recent_outages": [_outage_dict(r) for r in reversed(all_rows[-25:])],
    }


class Handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            self._serve_html()
        elif self.path.startswith("/api/data"):
            self._serve_json()
        else:
            self.send_error(404)

    def _serve_html(self):
        body = TEMPLATE_PATH.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _serve_json(self):
        body = json.dumps(build_data()).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)


def run(host="127.0.0.1", port=8787, open_browser=True):
    server = ThreadingHTTPServer((host, port), Handler)
    url = f"http://{host}:{port}/"
    print(f"Out-nOutage dashboard running at {url} (Ctrl+C to stop)")
    if open_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
