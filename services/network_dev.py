"""
Helpers for LAN / Wi-Fi local QA (laptop + phone on same network).
"""

from __future__ import annotations

import re
import socket

# Origins: http(s)://host:port on localhost or private RFC1918 ranges.
LAN_ORIGIN_REGEX = (
    r"^https?://"
    r"(localhost|127\.0\.0\.1"
    r"|192\.168\.\d{1,3}\.\d{1,3}"
    r"|10\.\d{1,3}\.\d{1,3}\.\d{1,3}"
    r"|172\.(?:1[6-9]|2\d|3[0-1])\.\d{1,3}\.\d{1,3})"
    r"(?::\d+)?$"
)

VERCEL_ORIGIN_REGEX = r"^https://.*\.vercel\.app$"

COMBINED_DEV_CORS_REGEX = f"(?:{VERCEL_ORIGIN_REGEX}|{LAN_ORIGIN_REGEX})"


def get_lan_ipv4() -> str | None:
    """Best-effort LAN IPv4 (typically Wi-Fi), not 127.0.0.1."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            if ip and not ip.startswith("127."):
                return ip
    except OSError:
        pass

    try:
        import netifaces  # optional dependency — not required
    except ImportError:
        netifaces = None

    if netifaces:
        for iface in netifaces.interfaces():
            addrs = netifaces.ifaddresses(iface).get(netifaces.AF_INET, [])
            for entry in addrs:
                ip = entry.get("addr")
                if ip and re.match(r"^192\.168\.|^10\.|^172\.(1[6-9]|2\d|3[0-1])\.", ip):
                    return ip
    return None


def format_lan_urls(
    *,
    frontend_port: int = 5173,
    backend_port: int = 8000,
) -> dict[str, str]:
    ip = get_lan_ipv4() or "YOUR_LAN_IP"
    return {
        "ip": ip,
        "frontend": f"http://{ip}:{frontend_port}",
        "backend": f"http://{ip}:{backend_port}",
        "frontend_local": f"http://localhost:{frontend_port}",
        "backend_local": f"http://localhost:{backend_port}",
    }
