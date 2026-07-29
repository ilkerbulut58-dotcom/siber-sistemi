"""Operator helper: provision expert security test tenant (dry-run by default)."""

from __future__ import annotations

import argparse
import sys
from datetime import UTC, datetime

EXPERT_TENANT_TEMPLATE = {
    "tenant_type": "expert_security_test",
    "is_pilot": True,
    "pilot_active_scan_allowed": False,
    "expert_test_quota": 10,
    "pilot_scan_quota": None,
    "scans_disabled": False,
    "recommended_role": "security_analyst",
    "organization_membership_role": "security_analyst",
    "allowed_profiles": ["safe"],
    "deep_enabled": False,
    "code_enabled": False,
    "full_active_enabled": False,
    "domain_verification_required": True,
    "platform_admin": False,
    "scan_concurrency_limit": 1,
    "notes": (
        "Expert (security_analyst org role) can add/verify own domains via self-service API. "
        "Manual active-scan approval remains admin-only. Deep/code/full_active disabled unless "
        "operator sets pilot_active_scan_allowed after written approval."
    ),
}


def _validate_args(args: argparse.Namespace) -> list[str]:
    errors: list[str] = []
    if not args.email or "@" not in args.email:
        errors.append("expert email is required")
    if not args.display_name:
        errors.append("display name is required")
    if not args.operator:
        errors.append("operator identity is required")
    if not args.start_date or not args.end_date:
        errors.append("pilot start and end dates are required")
    if args.start_date and args.end_date and args.end_date < args.start_date:
        errors.append("pilot end date must be on or after start date")
    if not args.confirm and not args.dry_run:
        errors.append("pass --confirm EXPERT_TENANT_CREATE to create (otherwise use --dry-run)")
    if args.confirm != "EXPERT_TENANT_CREATE":
        errors.append("confirmation token must be exactly EXPERT_TENANT_CREATE")
    return errors


def build_plan(args: argparse.Namespace) -> dict:
    return {
        **EXPERT_TENANT_TEMPLATE,
        "email": args.email,
        "display_name": args.display_name,
        "operator": args.operator,
        "pilot_start_date": args.start_date,
        "pilot_end_date": args.end_date,
        "initial_domains": args.domains or [],
        "created_at": datetime.now(UTC).isoformat(),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare expert security test tenant")
    parser.add_argument("--email", help="Expert user email")
    parser.add_argument("--display-name", help="Expert display name")
    parser.add_argument("--operator", help="Operator/admin identity performing provisioning")
    parser.add_argument("--start-date", help="Pilot start date YYYY-MM-DD")
    parser.add_argument("--end-date", help="Pilot end date YYYY-MM-DD")
    parser.add_argument("--domains", nargs="*", default=[], help="Optional pre-approved domains")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print provisioning plan only (default when --confirm omitted)",
    )
    parser.add_argument(
        "--confirm",
        help="Must be EXPERT_TENANT_CREATE to perform provisioning",
    )
    args = parser.parse_args()

    if args.dry_run or not args.confirm:
        print("Expert test tenant template:")
        for key, value in EXPERT_TENANT_TEMPLATE.items():
            print(f"  {key}: {value}")
        if args.email:
            plan = build_plan(args)
            print("\nDry-run plan:")
            for key, value in plan.items():
                print(f"  {key}: {value}")
        print("\nTo create when expert email is known:")
        print(
            "  python scripts/prepare_expert_test_tenant.py "
            "--email EXPERT@EXAMPLE.COM --display-name 'Expert Name' "
            "--operator 'operator@company.com' --start-date 2026-08-01 --end-date 2026-08-31 "
            "--confirm EXPERT_TENANT_CREATE"
        )
        return

    errors = _validate_args(args)
    if errors:
        for err in errors:
            print(f"ERROR: {err}", file=sys.stderr)
        sys.exit(1)

    plan = build_plan(args)
    print("Provisioning expert tenant is not automated in closed pilot.")
    print("Use platform admin invite/API with this plan:")
    for key, value in plan.items():
        print(f"  {key}: {value}")
    print("\nDo not grant platform_admin. Set role=security_analyst.")


if __name__ == "__main__":
    main()
