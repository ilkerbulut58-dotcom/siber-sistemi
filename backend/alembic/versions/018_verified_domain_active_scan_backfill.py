"""Backfill active_scan_allowed for domains verified before auto-approval."""

from __future__ import annotations

from alembic import op

revision: str = "018_active_scan_backfill"
down_revision: str | None = "017_phase13_pilot_tenant"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE domains
        SET active_scan_allowed = true
        WHERE is_verified = true
          AND active_scan_allowed = false
        """
    )


def downgrade() -> None:
    pass
