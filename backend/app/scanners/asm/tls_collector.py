"""Passive TLS certificate inventory."""

from __future__ import annotations

import logging
import socket
import ssl
from datetime import UTC, datetime

logger = logging.getLogger(__name__)


def collect_tls_info(hostname: str, port: int = 443) -> dict[str, object]:
    context = ssl.create_default_context()
    info: dict[str, object] = {
        "hostname": hostname,
        "port": port,
        "valid": False,
    }

    try:
        with socket.create_connection((hostname, port), timeout=10) as sock, context.wrap_socket(
            sock, server_hostname=hostname
        ) as ssock:
            cert = ssock.getpeercert()
            info["valid"] = True
            info["subject"] = dict(x[0] for x in cert.get("subject", ()))
            info["issuer"] = dict(x[0] for x in cert.get("issuer", ()))
            info["version"] = cert.get("version")
            info["san"] = cert.get("subjectAltName", [])
            not_after = cert.get("notAfter")
            if not_after:
                expiry = datetime.strptime(not_after, "%b %d %H:%M:%S %Y %Z").replace(tzinfo=UTC)
                info["not_after"] = expiry.isoformat()
                info["days_until_expiry"] = (expiry - datetime.now(UTC)).days
            info["protocol"] = ssock.version()
    except ssl.SSLError as exc:
        info["error"] = f"SSL error: {exc}"
    except OSError as exc:
        info["error"] = str(exc)
    except Exception as exc:
        logger.debug("TLS collection failed for %s: %s", hostname, exc)
        info["error"] = str(exc)

    return info
