# Out-nOutage

Detects internet outages on your computer and logs when they happened and
how long they lasted, so you can see stats like outage count per day and
total downtime.

No external dependencies — just Python 3.

## How it works

A background loop checks connectivity every 5 seconds by opening a raw TCP
connection to a few well-known IPs (Cloudflare, Google, Quad9 — hit by IP so
a broken DNS resolver doesn't cause a false alarm). A single failure isn't
enough to count as an outage: it does a few quick confirmation checks first
to filter out momentary blips. Once a real outage is confirmed, it records
the start time; when connectivity returns, it records the end time and
duration to a local SQLite database (`data/outages.db`). If the monitor
process itself gets killed or the machine reboots mid-outage, it picks the
outage back up on restart instead of losing it.

When an outage starts, it also checks whether your **default gateway**
(your router) is still reachable, to tell apart two different problems:

- **Local network** — the router itself doesn't respond. Likely Wi-Fi,
  ethernet cable, or the router/modem.
- **ISP / upstream** — the router responds fine, but nothing beyond it does.
  Likely your internet provider's side, not your equipment.

Each outage gets tagged with one of these (or "unknown" if the gateway
couldn't be determined), shown in `report`, `status`, and the dashboard.

## Usage

Run in the foreground to try it out:

```
python main.py run
```

Leave that running, then in another terminal:

```
python main.py status           # current connectivity + how long the monitor has been up
python main.py report today     # outages today, with timestamps and lengths
python main.py report session   # outages since the monitor last started
python main.py report all       # every outage ever recorded
python main.py report days      # per-day breakdown for the last 14 days
```

## Running automatically since your computer turns on

To get outage counts that are meaningful ("outages today since I turned my
PC on"), install a Startup-folder shortcut that launches it at logon:

```
powershell -ExecutionPolicy Bypass -File install.ps1
```

This runs `main.py run` in the background via `pythonw.exe` (no console
window) every time you log in, and also starts it immediately. (It uses the
Startup folder rather than Task Scheduler because Task Scheduler is locked
down to admins on some machines, including the one this was built on.)

To remove it:

```
powershell -ExecutionPolicy Bypass -File uninstall.ps1
```

## Data

- `data/outages.db` — SQLite database of recorded outages and monitor sessions
- `data/monitor.log` — rolling log of monitor activity (outage start/end events)

Both are gitignored; they're local state, not something to commit.
