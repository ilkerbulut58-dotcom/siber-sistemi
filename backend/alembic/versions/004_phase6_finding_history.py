"""Phase 6: finding history, AI fields, test mode support."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "004_phase6_finding_history"
down_revision: Union[str, None] = "003_phase5_findings"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("findings", sa.Column("reviewer_notes", sa.Text(), nullable=True))
    op.add_column("findings", sa.Column("ai_summary", sa.Text(), nullable=True))
    op.add_column("findings", sa.Column("ai_remediation", sa.Text(), nullable=True))
    op.add_column("findings", sa.Column("ai_confidence_label", sa.String(length=50), nullable=True))

    op.create_table(
        "finding_history",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("finding_id", sa.Uuid(), nullable=False),
        sa.Column("scan_job_id", sa.Uuid(), nullable=True),
        sa.Column("event_type", sa.String(length=50), nullable=False),
        sa.Column("details", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["finding_id"], ["findings.id"]),
        sa.ForeignKeyConstraint(["scan_job_id"], ["scan_jobs.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_finding_history_finding_id", "finding_history", ["finding_id"])


def downgrade() -> None:
    op.drop_table("finding_history")
    op.drop_column("findings", "ai_confidence_label")
    op.drop_column("findings", "ai_remediation")
    op.drop_column("findings", "ai_summary")
    op.drop_column("findings", "reviewer_notes")
