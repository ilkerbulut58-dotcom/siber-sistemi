"""Passive DNS record collection."""

from __future__ import annotations

import logging

import dns.exception
import dns.resolver

logger = logging.getLogger(__name__)

RECORD_TYPES = ("A", "AAAA", "CNAME", "MX", "TXT", "NS")


def collect_dns_records(hostname: str) -> dict[str, list[str]]:
    records: dict[str, list[str]] = {}
    resolver = dns.resolver.Resolver()
    resolver.lifetime = 8.0

    for rtype in RECORD_TYPES:
        try:
            answers = resolver.resolve(hostname, rtype)
            values: list[str] = []
            for answer in answers:
                if rtype == "MX":
                    values.append(str(answer.exchange).rstrip("."))
                elif rtype == "TXT":
                    strings = getattr(answer, "strings", None)
                    if strings:
                        text = b"".join(strings).decode("utf-8", errors="replace")
                    else:
                        text = str(answer).strip('"')
                    values.append(text.strip())
                else:
                    values.append(str(answer).rstrip('"'))
            if values:
                records[rtype] = values
        except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN, dns.exception.Timeout):
            continue
        except Exception as exc:
            logger.debug("DNS %s lookup failed for %s: %s", rtype, hostname, exc)

    return records
