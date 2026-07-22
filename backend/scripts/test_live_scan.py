"""Manual E2E scan test against a live URL."""

import asyncio
import sys

from app.scanners.orchestrator import run_scan_for_profile


async def main() -> None:
    target = sys.argv[1] if len(sys.argv) > 1 else "https://turbridge.de"
    profile = sys.argv[2] if len(sys.argv) > 2 else "deep"

    print(f"Running {profile} scan on {target}...")
    findings = await run_scan_for_profile(target, profile)
    print(f"Status: OK — {len(findings)} findings")
    tools = {}
    for f in findings:
        tools[f.source_tool] = tools.get(f.source_tool, 0) + 1
    print("By tool:", tools)
    for f in findings[:15]:
        print(f"  [{f.severity}] {f.source_rule_id}: {f.title[:80]}")


if __name__ == "__main__":
    asyncio.run(main())
