"""Phase 13 controlled closed pilot tenant fields."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "017_phase13_pilot_tenant"
down_revision: str | None = "016_phase12_domain_scan_auth"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "organizations",
        sa.Column("is_pilot", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "organizations",
        sa.Column("pilot_starts_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "organizations",
        sa.Column("pilot_ends_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "organizations",
        sa.Column("pilot_scan_quota", sa.Integer(), nullable=True),
    )
    op.add_column(
        "organizations",
        sa.Column("pilot_notes", sa.Text(), nullable=True),
    )
    op.add_column(
        "organizations",
        sa.Column("scans_disabled", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "organizations",
        sa.Column(
            "pilot_active_scan_allowed",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
    )


def downgrade() -> None:
    op.drop_column("organizations", "pilot_active_scan_allowed")
    op.drop_column("organizations", "scans_disabled")
    op.drop_column("organizations", "pilot_notes")
    op.drop_column("organizations", "pilot_scan_quota")
    op.drop_column("organizations", "pilot_ends_at")
    op.drop_column("organizations", "pilot_starts_at")
    op.drop_column("organizations", "is_pilot")
