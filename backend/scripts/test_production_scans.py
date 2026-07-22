"""Production API test for deep and code quick scans."""

import asyncio
import json
import sys
import time
import urllib.error
import urllib.request

BASE = "https://siber.cloudnira.com"


def api(method: str, path: str, body: dict | None = None, token: str | None = None) -> dict:
    url = f"{BASE}{path}"
    data = json.dumps(body).encode() if body is not None else None
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        payload = exc.read().decode()
        raise RuntimeError(f"{method} {path} -> {exc.code}: {payload}") from exc


def wait_scan(token: str, org_id: str, scan_id: str, timeout: int = 120) -> dict:
    deadline = time.time() + timeout
    while time.time() < deadline:
        listing = api("GET", f"/api/v1/organizations/{org_id}/scans", token=token)
        for scan in listing["data"]:
            if scan["id"] == scan_id:
                if scan["status"] in ("completed", "failed", "cancelled"):
                    return scan
        time.sleep(3)
    raise TimeoutError(f"Scan {scan_id} did not finish in {timeout}s")


def run_profile(token: str, profile: str, target: str) -> None:
    result = api(
        "POST",
        "/api/v1/quick-scan",
        {
            "target_url": target,
            "scan_profile": profile,
            "authorization_accepted": True,
        },
        token=token,
    )
    scan = result["data"]["scan"]
    org_id = result["data"]["organization_id"]
    print(f"{profile}: queued scan {scan['id']}")
    final = wait_scan(token, org_id, scan["id"])
    print(
        f"{profile}: status={final['status']} profile={final['scan_profile']} "
        f"findings={final['findings_count']}"
    )
    if final["status"] != "completed":
        raise SystemExit(f"{profile} scan failed: {final.get('error_log')}")


def main() -> None:
    target = sys.argv[1] if len(sys.argv) > 1 else "https://turbridge.de"
    login = api(
        "POST",
        "/api/v1/auth/login",
        {"email": "admin@admin.com", "password": "admin"},
    )
    token = login["data"]["tokens"]["access_token"]
    run_profile(token, "deep", target)
    run_profile(token, "code", target)
    print("PRODUCTION_SCAN_OK")


if __name__ == "__main__":
    main()
