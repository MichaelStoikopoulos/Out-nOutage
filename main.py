"""Out-nOutage: detects and logs internet outages.

Usage:
    python main.py run              Start monitoring (run this at login/startup)
    python main.py status           Show current connectivity + session info
    python main.py report [scope]   Show stats: today | session | all | days
"""

import argparse

from src import dashboard, monitor, report


def main():
    parser = argparse.ArgumentParser(description="Out-nOutage: internet outage detector")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("run", help="Start monitoring (foreground; run this at startup)")
    sub.add_parser("status", help="Show current connectivity status")

    dash_p = sub.add_parser("dashboard", help="Open a live local web dashboard")
    dash_p.add_argument("--port", type=int, default=8787)
    dash_p.add_argument("--no-open", action="store_true", help="Don't auto-open a browser tab")

    report_p = sub.add_parser("report", help="Show outage stats")
    report_p.add_argument(
        "scope",
        nargs="?",
        default="today",
        choices=["today", "session", "all", "days"],
        help="today (default): calendar day. session: since monitor last started "
             "(≈ since computer turned on, if installed at logon). all: everything ever recorded. "
             "days: per-day breakdown for the last 14 days.",
    )

    args = parser.parse_args()

    if args.command == "run":
        monitor.run()
    elif args.command == "status":
        report.print_status()
    elif args.command == "report":
        report.print_report(args.scope)
    elif args.command == "dashboard":
        dashboard.run(port=args.port, open_browser=not args.no_open)


if __name__ == "__main__":
    main()
