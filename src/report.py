"""CLI stats reporting over recorded outages."""

from datetime import datetime

from src import checker, db, netinfo
from src.monitor import format_duration

_KIND_TAGS = {
    "local": "local network",
    "upstream": "ISP / upstream",
    "unknown": "unknown cause",
}


def _kind_tag(kind):
    return _KIND_TAGS.get(kind, "unknown cause")


def _summarize(rows):
    count = len(rows)
    total = sum(r[2] for r in rows)
    longest = max((r[2] for r in rows), default=0)
    kind_counts = {"local": 0, "upstream": 0, "unknown": 0}
    for row in rows:
        kind = row[3] if len(row) > 3 else "unknown"
        kind_counts[kind] = kind_counts.get(kind, 0) + 1
    return count, total, longest, kind_counts


def _print_rows(rows):
    if not rows:
        print("  (no outages recorded)")
        return
    for row in rows:
        start_ts, end_ts, duration, kind = row
        start = datetime.fromisoformat(start_ts)
        print(f"  - {start.strftime('%Y-%m-%d %H:%M:%S')}  length={format_duration(duration)}  [{_kind_tag(kind)}]")


def _print_summary_line(count, total, longest, kind_counts):
    print(
        f"\nCount: {count}   Total downtime: {format_duration(total)}   Longest: {format_duration(longest)}"
    )
    print(
        f"By cause -> local network: {kind_counts['local']}   "
        f"ISP/upstream: {kind_counts['upstream']}   unknown: {kind_counts['unknown']}"
    )


def print_report(scope="today"):
    db.init_db()

    if scope == "today":
        start_of_day = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        rows = db.get_outages_since(start_of_day)
        print(f"Today's outages ({start_of_day.strftime('%Y-%m-%d')}):")
        _print_rows(rows)
        _print_summary_line(*_summarize(rows))

    elif scope == "session":
        session_start = db.get_last_session_start()
        if session_start is None:
            print("No monitoring session recorded yet. Run 'python main.py run' first.")
            return
        rows = db.get_outages_since(session_start)
        elapsed = (datetime.now() - session_start).total_seconds()
        print(f"Since monitor started ({session_start.strftime('%Y-%m-%d %H:%M:%S')}, {format_duration(elapsed)} ago):")
        _print_rows(rows)
        count, total, longest, kind_counts = _summarize(rows)
        uptime_pct = 100 * (1 - (total / elapsed)) if elapsed > 0 else 100
        _print_summary_line(count, total, longest, kind_counts)
        print(f"Uptime: {uptime_pct:.2f}%")

    elif scope == "all":
        rows = db.get_all_outages()
        print("All recorded outages:")
        _print_rows(rows)
        _print_summary_line(*_summarize(rows))

    elif scope == "days":
        rows = db.get_outages_grouped_by_day(limit_days=14)
        print("Outages per day (most recent 14 days):")
        if not rows:
            print("  (no outages recorded)")
        for day, count, total in rows:
            print(f"  {day}: {count} outage(s), {format_duration(total)} downtime")

    else:
        raise ValueError(f"Unknown scope: {scope}")


def print_status():
    db.init_db()
    up = checker.is_connected()
    print(f"Connectivity: {'UP' if up else 'DOWN'}")

    gateway = netinfo.get_default_gateway()
    if gateway:
        reachable = netinfo.is_host_reachable(gateway)
        print(f"Default gateway: {gateway} ({'reachable' if reachable else 'NOT reachable'})")
    else:
        print("Default gateway: could not be determined")

    session_start = db.get_last_session_start()
    if session_start:
        elapsed = (datetime.now() - session_start).total_seconds()
        print(f"Monitor running since: {session_start.strftime('%Y-%m-%d %H:%M:%S')} ({format_duration(elapsed)} ago)")
    else:
        print("Monitor has not been started yet (no session recorded).")

    pending = db.load_pending_outage()
    if pending:
        ongoing = (datetime.now() - pending["down_since"]).total_seconds()
        print(
            f"Outage IN PROGRESS since {pending['down_since'].strftime('%Y-%m-%d %H:%M:%S')} "
            f"({format_duration(ongoing)} so far) -- {_kind_tag(pending['kind'])}"
        )
