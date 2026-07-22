"""Passive CDN / WAF detection from response headers."""

from __future__ import annotations

CDN_WAF_SIGNATURES: list[tuple[str, str, tuple[str, ...]]] = [
    ("cdn", "Cloudflare", ("cf-ray", "cf-cache-status", "server: cloudflare")),
    ("cdn", "AWS CloudFront", ("x-amz-cf-id", "x-amz-cf-pop", "via: cloudfront")),
    ("cdn", "Fastly", ("x-served-by", "x-fastly-request-id", "fastly")),
    ("cdn", "Akamai", ("x-akamai-transformed", "akamai")),
    ("waf", "Cloudflare WAF", ("cf-ray",)),
    ("waf", "AWS WAF", ("x-amzn-waf",)),
    ("waf", "Sucuri", ("x-sucuri-id", "x-sucuri-cache")),
    ("waf", "Imperva/Incapsula", ("x-iinfo", "x-cdn")),
]


def detect_cdn_waf(headers: dict[str, str]) -> list[dict[str, str]]:
    detected: list[dict[str, str]] = []
    seen: set[str] = set()
    header_blob = " ".join(f"{k}: {v}" for k, v in headers.items()).lower()

    for kind, name, signals in CDN_WAF_SIGNATURES:
        for signal in signals:
            if ":" in signal:
                key, value = signal.split(":", 1)
                if headers.get(key.strip(), "").lower().find(value.strip()) >= 0:
                    if name not in seen:
                        detected.append({"type": kind, "name": name, "signal": signal})
                        seen.add(name)
                    break
            elif signal.lower() in header_blob or signal.lower() in headers:
                if name not in seen:
                    detected.append({"type": kind, "name": name, "signal": signal})
                    seen.add(name)
                break

    return detected
