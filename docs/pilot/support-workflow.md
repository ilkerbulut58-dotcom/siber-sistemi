# Pilot Support Workflow

1. Customer opens support channel (email/ticket — configure operationally).
2. Support verifies pilot tenant ID and domain verification status.
3. For scan failures: check audit log, scan error_log, worker health (`/api/v1/health/ready`).
4. For false positives: customer submits finding feedback; triage does not alter benchmarks.
5. Platform admin may grant time-limited support access via support grants API.
6. Close ticket with resolution code and optional pilot notes update.

SLA: best-effort during closed pilot; no production SLA until general availability.
