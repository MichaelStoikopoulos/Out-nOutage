"""CLI stats reporting over recorded outages."""

from datetime import datetime, timedelta

from src import checker, db
from src.monitor import format_duration


def _summarize(rows):
    count = len(rows)
    total = sum(r[2] for r in rows)
    longest = max((r[2] for r in rows), default=0)
    return count, total, longest


def _print_rows(rows):
    if not rows:
        print("  (no outages recorded)")
        return
    for start_ts, end_ts, duration in rows:
        start = datetime.fromisoformat(start_ts)
        print(f"  - {start.strftime('%Y-%m-%d %H:%M:%S')}  length={format_duration(duration)}")


def print_report(scope="today"):
    db.init_db()

    if scope == "today":
        start_of_day = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        rows = db.get_outages_since(start_of_day)
        print(f"Today's outages ({start_of_day.strftime('%Y-%m-%d')}):")
        _print_rows(rows)
        count, total, longest = _summarize(rows)
        print(f"\nCount: {count}   Total downtime: {format_duration(total)}   Longest: {format_duration(longest)}")

    elif scope == "session":
        session_start = db.get_last_session_start()
        if session_start is None:
            print("No monitoring session recorded yet. Run 'python main.py run' first.")
            return
        rows = db.get_outages_since(session_start)
        elapsed = (datetime.now() - session_start).total_seconds()
        print(f"Since monitor started ({session_start.strftime('%Y-%m-%d %H:%M:%S')}, {format_duration(elapsed)} ago):")
        _print_rows(rows)
        count, total, longest = _summarize(rows)
        uptime_pct = 100 * (1 - (total / elapsed)) if elapsed > 0 else 100
        print(
            f"\nCount: {count}   Total downtime: {format_duration(total)}   "
            f"Longest: {format_duration(longest)}   Uptime: {uptime_pct:.2f}%"
        )

    elif scope == "all":
        rows = db.get_all_outages()
        print("All recorded outages:")
        _print_rows(rows)
        count, total, longest = _summarize(rows)
        print(f"\nCount: {count}   Total downtime: {format_duration(total)}   Longest: {format_duration(longest)}")

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

    session_start = db.get_last_session_start()
    if session_start:
        elapsed = (datetime.now() - session_start).total_seconds()
        print(f"Monitor running since: {session_start.strftime('%Y-%m-%d %H:%M:%S')} ({format_duration(elapsed)} ago)")
    else:
        print("Monitor has not been started yet (no session recorded).")

    pending = db.load_pending_outage()
    if pending:
        ongoing = (datetime.now() - pending).total_seconds()
        print(f"Outage IN PROGRESS since {pending.strftime('%Y-%m-%d %H:%M:%S')} ({format_duration(ongoing)} so far)")
