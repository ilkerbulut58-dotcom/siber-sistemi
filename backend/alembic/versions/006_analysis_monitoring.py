"""Phase 7D: Analysis engines + continuous monitoring."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "006_analysis_monitoring"
down_revision: Union[str, None] = "005_phase7_tr_remediation"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("findings", sa.Column("correlation_key", sa.String(length=120), nullable=True))
    op.add_column("findings", sa.Column("risk_score", sa.Float(), nullable=True))
    op.add_column("findings", sa.Column("cvss_score", sa.Float(), nullable=True))
    op.add_column(
        "findings",
        sa.Column("source_tools", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.add_column("findings", sa.Column("verification_status", sa.String(length=30), nullable=True))
    op.add_column("findings", sa.Column("verification_notes", sa.Text(), nullable=True))
    op.create_index("ix_findings_correlation_key", "findings", ["correlation_key"])

    op.create_table(
        "scan_schedules",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("domain_id", sa.Uuid(), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("target_url", sa.String(length=500), nullable=False),
        sa.Column("scan_profile", sa.String(length=50), nullable=False, server_default="safe"),
        sa.Column("interval_hours", sa.Integer(), nullable=False, server_default="24"),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("last_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("next_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_scan_job_id", sa.Uuid(), nullable=True),
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
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["domain_id"], ["domains.id"]),
        sa.ForeignKeyConstraint(["last_scan_job_id"], ["scan_jobs.id"]),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_scan_schedules_org", "scan_schedules", ["organization_id"])
    op.create_index("ix_scan_schedules_next_run", "scan_schedules", ["next_run_at"])

    op.create_table(
        "monitoring_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("schedule_id", sa.Uuid(), nullable=True),
        sa.Column("scan_job_id", sa.Uuid(), nullable=False),
        sa.Column("previous_scan_job_id", sa.Uuid(), nullable=True),
        sa.Column("event_type", sa.String(length=50), nullable=False),
        sa.Column("finding_id", sa.Uuid(), nullable=True),
        sa.Column("correlation_key", sa.String(length=120), nullable=True),
        sa.Column("details", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["finding_id"], ["findings.id"]),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.ForeignKeyConstraint(["previous_scan_job_id"], ["scan_jobs.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["scan_job_id"], ["scan_jobs.id"]),
        sa.ForeignKeyConstraint(["schedule_id"], ["scan_schedules.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_monitoring_events_org", "monitoring_events", ["organization_id"])
    op.create_index("ix_monitoring_events_schedule", "monitoring_events", ["schedule_id"])


def downgrade() -> None:
    op.drop_index("ix_monitoring_events_schedule", table_name="monitoring_events")
    op.drop_index("ix_monitoring_events_org", table_name="monitoring_events")
    op.drop_table("monitoring_events")
    op.drop_index("ix_scan_schedules_next_run", table_name="scan_schedules")
    op.drop_index("ix_scan_schedules_org", table_name="scan_schedules")
    op.drop_table("scan_schedules")
    op.drop_index("ix_findings_correlation_key", table_name="findings")
    op.drop_column("findings", "verification_notes")
    op.drop_column("findings", "verification_status")
    op.drop_column("findings", "source_tools")
    op.drop_column("findings", "cvss_score")
    op.drop_column("findings", "risk_score")
    op.drop_column("findings", "correlation_key")
