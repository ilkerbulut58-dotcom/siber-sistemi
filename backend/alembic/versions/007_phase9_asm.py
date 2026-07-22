"""Phase 9: Attack Surface Management (ASM)."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "007_phase9_asm"
down_revision: Union[str, None] = "006_analysis_monitoring"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "asm_discovery_jobs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("domain_id", sa.Uuid(), nullable=False),
        sa.Column("initiated_by", sa.Uuid(), nullable=False),
        sa.Column("target_url", sa.String(length=500), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="queued"),
        sa.Column("error_log", sa.Text(), nullable=True),
        sa.Column("assets_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("summary", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("celery_task_id", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["domain_id"], ["domains.id"]),
        sa.ForeignKeyConstraint(["initiated_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_asm_discovery_jobs_org", "asm_discovery_jobs", ["organization_id"])
    op.create_index("ix_asm_discovery_jobs_domain", "asm_discovery_jobs", ["domain_id"])
    op.create_index("ix_asm_discovery_jobs_status", "asm_discovery_jobs", ["status"])

    op.create_table(
        "assets",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("domain_id", sa.Uuid(), nullable=False),
        sa.Column("discovery_job_id", sa.Uuid(), nullable=True),
        sa.Column("parent_asset_id", sa.Uuid(), nullable=True),
        sa.Column("asset_type", sa.String(length=30), nullable=False),
        sa.Column("identifier", sa.String(length=500), nullable=False),
        sa.Column("url", sa.String(length=1000), nullable=True),
        sa.Column("fingerprint", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="active"),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("exposure_score", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("risk_score", sa.Float(), nullable=True),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("last_scanned_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["discovery_job_id"], ["asm_discovery_jobs.id"]),
        sa.ForeignKeyConstraint(["domain_id"], ["domains.id"]),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.ForeignKeyConstraint(["parent_asset_id"], ["assets.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_assets_org_project", "assets", ["organization_id", "project_id"])
    op.create_index("ix_assets_fingerprint", "assets", ["fingerprint"], unique=True)
    op.create_index("ix_assets_type", "assets", ["asset_type"])
    op.create_index("ix_assets_identifier", "assets", ["identifier"])

    op.add_column("findings", sa.Column("asset_id", sa.Uuid(), nullable=True))
    op.create_foreign_key("fk_findings_asset_id", "findings", "assets", ["asset_id"], ["id"])
    op.create_index("ix_findings_asset_id", "findings", ["asset_id"])


def downgrade() -> None:
    op.drop_index("ix_findings_asset_id", table_name="findings")
    op.drop_constraint("fk_findings_asset_id", "findings", type_="foreignkey")
    op.drop_column("findings", "asset_id")
    op.drop_table("assets")
    op.drop_table("asm_discovery_jobs")
