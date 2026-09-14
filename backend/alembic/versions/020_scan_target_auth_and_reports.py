"""Predefined scan targets, assignments, DNS exempt flag, scan auth source, legacy revert."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSON

revision = "020_scan_target_auth"
down_revision = "019_domain_revalidation_expert"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "predefined_scan_targets",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("hostname", sa.String(length=255), nullable=False),
        sa.Column("display_name", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("default_scan_profile", sa.String(length=50), server_default="safe", nullable=False),
        sa.Column("notes", sa.String(length=500), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("hostname"),
    )
    op.create_table(
        "scan_target_assignments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("predefined_target_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("assigned_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("allowed_profiles", JSON, server_default="[]", nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_by_user_id", sa.Uuid(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["assigned_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.ForeignKeyConstraint(["predefined_target_id"], ["predefined_scan_targets.id"]),
        sa.ForeignKeyConstraint(["revoked_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_scan_target_assignments_user_id", "scan_target_assignments", ["user_id"])
    op.create_index(
        "ix_scan_target_assignments_organization_id", "scan_target_assignments", ["organization_id"]
    )

    op.add_column(
        "users",
        sa.Column("dns_verification_exempt", sa.Boolean(), server_default=sa.text("false"), nullable=False),
    )
    op.add_column(
        "scan_jobs",
        sa.Column("authorization_source", sa.String(length=50), nullable=True),
    )

    # Do not treat relax/test auto-verify as valid for new scans.
    op.execute(
        """
        UPDATE domains
        SET is_verified = false,
            active_scan_allowed = false,
            verification_method = NULL,
            verification_expires_at = NULL
        WHERE verification_method IN ('pilot_relax', 'test_skip')
           OR (is_verified = true AND verification_method IS NULL AND verified_at IS NOT NULL)
        """
    )

    for host, label in (
        ("turbridge.de", "turbridge.de (test)"),
        ("wolkeshopping.de", "wolkeshopping.de (test)"),
    ):
        op.execute(
            f"""
            INSERT INTO predefined_scan_targets (id, hostname, display_name, is_active, default_scan_profile, notes)
            SELECT gen_random_uuid(), '{host}', '{label}', true, 'safe',
                   'Operator predefined test target; assign per user in platform admin.'
            WHERE NOT EXISTS (SELECT 1 FROM predefined_scan_targets WHERE hostname = '{host}')
            """
        )


def downgrade() -> None:
    op.drop_column("scan_jobs", "authorization_source")
    op.drop_column("users", "dns_verification_exempt")
    op.drop_index("ix_scan_target_assignments_organization_id", table_name="scan_target_assignments")
    op.drop_index("ix_scan_target_assignments_user_id", table_name="scan_target_assignments")
    op.drop_table("scan_target_assignments")
    op.drop_table("predefined_scan_targets")
