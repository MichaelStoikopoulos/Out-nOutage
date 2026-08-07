"""Background monitoring loop: polls connectivity and records outages."""

import logging
import time
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path

from src import checker, db, netinfo

LOG_PATH = Path(__file__).resolve().parent.parent / "data" / "monitor.log"

CHECK_INTERVAL = 5          # seconds between checks while up
RECHECK_WHILE_DOWN = 5      # seconds between checks while confirmed down
CONFIRM_RETRIES = 3         # extra checks before declaring an outage (avoids blips)
CONFIRM_DELAY = 2           # seconds between confirmation checks


def _setup_logging():
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    handlers = [
        RotatingFileHandler(LOG_PATH, maxBytes=1_000_000, backupCount=3, encoding="utf-8"),
        logging.StreamHandler(),
    ]
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=handlers,
    )


def format_duration(seconds):
    seconds = int(seconds)
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    parts = []
    if h:
        parts.append(f"{h}h")
    if m:
        parts.append(f"{m}m")
    parts.append(f"{s}s")
    return " ".join(parts)


def run():
    _setup_logging()
    db.init_db()
    session_id = db.start_session()
    logging.info("Out-nOutage monitor started (session #%s)", session_id)

    # Recover from a crash/reboot that happened mid-outage.
    pending = db.load_pending_outage()
    if pending:
        state_up = False
        down_since = pending["down_since"]
        current_kind = pending["kind"]
        current_gateway = pending["gateway_ip"]
        logging.warning(
            "Resuming after restart: outage was already in progress since %s (%s)",
            down_since.isoformat(),
            netinfo.describe(current_kind, current_gateway),
        )
    else:
        state_up = True
        down_since = None
        current_kind = None
        current_gateway = None

    while True:
        ok = checker.is_connected()
        now = datetime.now()

        if ok:
            if not state_up:
                duration = (now - down_since).total_seconds()
                db.record_outage(down_since, now, duration, kind=current_kind, gateway_ip=current_gateway)
                db.clear_pending_outage()
                logging.warning(
                    "Internet restored after %s (outage started %s, cause: %s)",
                    format_duration(duration),
                    down_since.isoformat(timespec="seconds"),
                    netinfo.describe(current_kind, current_gateway),
                )
                state_up = True
                down_since = None
                current_kind = None
                current_gateway = None
            time.sleep(CHECK_INTERVAL)
        else:
            if state_up:
                confirmed_down = True
                for _ in range(CONFIRM_RETRIES):
                    time.sleep(CONFIRM_DELAY)
                    if checker.is_connected():
                        confirmed_down = False
                        break
                if confirmed_down:
                    state_up = False
                    down_since = now
                    current_kind, current_gateway = netinfo.classify_outage()
                    db.save_pending_outage(down_since, current_kind, current_gateway)
                    logging.warning(
                        "Internet outage detected starting %s (%s)",
                        down_since.isoformat(timespec="seconds"),
                        netinfo.describe(current_kind, current_gateway),
                    )
                else:
                    time.sleep(CHECK_INTERVAL)
            else:
                time.sleep(RECHECK_WHILE_DOWN)


if __name__ == "__main__":
    run()
