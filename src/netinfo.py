"""Classify an outage as local-network vs upstream/ISP.

The idea: when the internet drops, check whether your own default gateway
(router) is still reachable.
  - Gateway unreachable  -> the problem is on your side (Wi-Fi, router, cable)
  - Gateway reachable    -> your local network is fine; the problem is
                             somewhere beyond your router (ISP / upstream)
"""

import os
import re
import socket
import subprocess

PING_TIMEOUT_MS = 1500
_NO_WINDOW = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0

KIND_LOCAL = "local"
KIND_UPSTREAM = "upstream"
KIND_UNKNOWN = "unknown"

KIND_LABELS = {
    KIND_LOCAL: "local network (router/Wi-Fi unreachable)",
    KIND_UPSTREAM: "ISP / upstream (router OK, internet beyond it isn't)",
    KIND_UNKNOWN: "unknown (couldn't determine gateway)",
}


def get_default_gateway():
    """Best-effort lookup of the current default gateway IP."""
    gateway = _gateway_via_powershell()
    if gateway:
        return gateway
    return _gateway_via_ipconfig()


def _gateway_via_powershell():
    try:
        result = subprocess.run(
            [
                "powershell", "-NoProfile", "-NonInteractive", "-Command",
                "(Get-NetRoute -DestinationPrefix '0.0.0.0/0' -ErrorAction SilentlyContinue "
                "| Sort-Object -Property RouteMetric | Select-Object -First 1 -ExpandProperty NextHop)",
            ],
            capture_output=True, text=True, timeout=5, creationflags=_NO_WINDOW,
        )
        gw = result.stdout.strip()
        if gw and gw != "0.0.0.0":
            return gw
    except Exception:
        pass
    return None


def _gateway_via_ipconfig():
    try:
        result = subprocess.run(
            ["ipconfig"], capture_output=True, text=True, timeout=5, creationflags=_NO_WINDOW,
        )
    except Exception:
        return None
    for line in result.stdout.splitlines():
        if "Default Gateway" in line:
            match = re.search(r":\s*([\d.]+)\s*$", line)
            if match:
                return match.group(1)
    return None


def is_host_reachable(host, timeout_ms=PING_TIMEOUT_MS):
    if not host:
        return False
    if _ping(host, timeout_ms):
        return True
    # Some routers/firewalls drop ICMP even when they're perfectly reachable;
    # fall back to a TCP probe on the ports a router's admin UI usually listens on.
    for port in (80, 443):
        try:
            with socket.create_connection((host, port), timeout=timeout_ms / 1000):
                return True
        except OSError:
            continue
    return False


def _ping(host, timeout_ms):
    try:
        result = subprocess.run(
            ["ping", "-n", "1", "-w", str(timeout_ms), host],
            capture_output=True, text=True, timeout=(timeout_ms / 1000) + 2, creationflags=_NO_WINDOW,
        )
        return result.returncode == 0
    except Exception:
        return False


def classify_outage():
    """Return (kind, gateway_ip)."""
    gateway = get_default_gateway()
    if not gateway:
        return KIND_UNKNOWN, None
    if is_host_reachable(gateway):
        return KIND_UPSTREAM, gateway
    return KIND_LOCAL, gateway


def describe(kind, gateway_ip):
    label = KIND_LABELS.get(kind, kind)
    if gateway_ip:
        return f"{label}, gateway {gateway_ip}"
    return label
