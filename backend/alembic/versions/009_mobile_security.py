"""Phase 9B: Mobile Application Security foundation."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "009_mobile_security"
down_revision: Union[str, None] = "008_finding_security_hardening"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "mobile_applications",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("platform", sa.String(length=20), nullable=False, server_default="android"),
        sa.Column("application_name", sa.String(length=255), nullable=True),
        sa.Column("package_name", sa.String(length=255), nullable=True),
        sa.Column("version_name", sa.String(length=100), nullable=True),
        sa.Column("version_code", sa.String(length=50), nullable=True),
        sa.Column("environment", sa.String(length=30), nullable=False, server_default="staging"),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("stored_filename", sa.String(length=255), nullable=False),
        sa.Column("file_size", sa.BigInteger(), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("upload_status", sa.String(length=30), nullable=False, server_default="uploaded"),
        sa.Column("analysis_status", sa.String(length=30), nullable=False, server_default="queued"),
        sa.Column("security_score", sa.Float(), nullable=True),
        sa.Column("findings_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("analysis_summary", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("error_log", sa.Text(), nullable=True),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        sa.Column("analyzed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("celery_task_id", sa.String(length=255), nullable=True),
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
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_mobile_applications_org", "mobile_applications", ["organization_id"])
    op.create_index("ix_mobile_applications_sha256", "mobile_applications", ["organization_id", "sha256"])
    op.create_foreign_key(
        "fk_findings_mobile_application_id",
        "findings",
        "mobile_applications",
        ["mobile_application_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.alter_column("findings", "scan_job_id", existing_type=sa.Uuid(), nullable=True)


def downgrade() -> None:
    op.alter_column("findings", "scan_job_id", existing_type=sa.Uuid(), nullable=False)
    op.drop_constraint("fk_findings_mobile_application_id", "findings", type_="foreignkey")
    op.drop_index("ix_mobile_applications_sha256", table_name="mobile_applications")
    op.drop_index("ix_mobile_applications_org", table_name="mobile_applications")
    op.drop_table("mobile_applications")
