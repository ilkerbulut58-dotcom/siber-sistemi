"""Target site intelligence profiles for web scans."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "012_target_site_profiles"
down_revision: Union[str, None] = "011_support_grants"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "target_site_profiles",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("scan_job_id", sa.Uuid(), nullable=False),
        sa.Column("target_url", sa.String(length=500), nullable=False),
        sa.Column("hostname", sa.String(length=255), nullable=False),
        sa.Column("profile", sa.JSON(), nullable=False),
        sa.Column(
            "collected_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["scan_job_id"], ["scan_jobs.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("scan_job_id"),
    )
    op.create_index(
        op.f("ix_target_site_profiles_organization_id"),
        "target_site_profiles",
        ["organization_id"],
    )
    op.create_index(
        op.f("ix_target_site_profiles_scan_job_id"),
        "target_site_profiles",
        ["scan_job_id"],
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_target_site_profiles_scan_job_id"), table_name="target_site_profiles")
    op.drop_index(op.f("ix_target_site_profiles_organization_id"), table_name="target_site_profiles")
    op.drop_table("target_site_profiles")
