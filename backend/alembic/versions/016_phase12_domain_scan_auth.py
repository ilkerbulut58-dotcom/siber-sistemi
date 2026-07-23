"""Phase 12 domain scan authorization fields."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "016_phase12_domain_scan_auth"
down_revision: str | None = "015_benchmark_active_profiles"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "domains",
        sa.Column("active_scan_allowed", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "domains",
        sa.Column("admin_approved_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "domains",
        sa.Column("admin_approved_by", sa.Uuid(), nullable=True),
    )
    op.add_column(
        "domains",
        sa.Column("verification_method", sa.String(length=50), nullable=True),
    )
    op.create_foreign_key(
        "fk_domains_admin_approved_by_users",
        "domains",
        "users",
        ["admin_approved_by"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_domains_admin_approved_by_users", "domains", type_="foreignkey")
    op.drop_column("domains", "verification_method")
    op.drop_column("domains", "admin_approved_by")
    op.drop_column("domains", "admin_approved_at")
    op.drop_column("domains", "active_scan_allowed")
