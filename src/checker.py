"""Connectivity checking primitives."""

import socket

# Well-known, highly-available hosts, hit by IP so a broken DNS resolver
# (itself a common outage symptom) doesn't produce a false "down" reading.
DEFAULT_TARGETS = [
    ("1.1.1.1", 443),   # Cloudflare
    ("8.8.8.8", 443),   # Google
    ("9.9.9.9", 443),   # Quad9
]


def is_connected(timeout=3.0, targets=DEFAULT_TARGETS):
    """Return True if any target host is reachable via a raw TCP connect."""
    for host, port in targets:
        try:
            with socket.create_connection((host, port), timeout=timeout):
                return True
        except OSError:
            continue
    return False
