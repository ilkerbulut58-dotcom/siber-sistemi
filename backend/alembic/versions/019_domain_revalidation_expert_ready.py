"""Domain revalidation fields and expert tenant metadata."""

from alembic import op
import sqlalchemy as sa

revision = "019_domain_revalidation_expert"
down_revision = "018_active_scan_backfill"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "domains",
        sa.Column("verification_expires_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "domains",
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "domains",
        sa.Column("revoked_by", sa.Uuid(), nullable=True),
    )
    op.add_column(
        "domains",
        sa.Column("verification_failure_reason", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "domains",
        sa.Column("allow_subdomains", sa.Boolean(), server_default=sa.text("false"), nullable=False),
    )
    op.create_foreign_key(
        "fk_domains_revoked_by_users",
        "domains",
        "users",
        ["revoked_by"],
        ["id"],
    )
    op.add_column(
        "organizations",
        sa.Column("tenant_type", sa.String(length=50), nullable=True),
    )
    op.add_column(
        "organizations",
        sa.Column("expert_test_quota", sa.Integer(), nullable=True),
    )

    op.execute(
        """
        UPDATE domains
        SET verification_expires_at = verified_at + interval '30 days'
        WHERE is_verified = true AND verified_at IS NOT NULL
        """
    )


def downgrade() -> None:
    op.drop_column("organizations", "expert_test_quota")
    op.drop_column("organizations", "tenant_type")
    op.drop_constraint("fk_domains_revoked_by_users", "domains", type_="foreignkey")
    op.drop_column("domains", "allow_subdomains")
    op.drop_column("domains", "verification_failure_reason")
    op.drop_column("domains", "revoked_by")
    op.drop_column("domains", "revoked_at")
    op.drop_column("domains", "verification_expires_at")
