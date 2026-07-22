"""Phase 9A: Finding security hardening — risk breakdown + asset typing."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "008_finding_security_hardening"
down_revision: Union[str, None] = "007_phase9_asm"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "findings",
        sa.Column("risk_breakdown", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.add_column(
        "findings",
        sa.Column("risk_model_version", sa.String(length=20), nullable=True),
    )
    op.add_column(
        "findings",
        sa.Column("asset_type", sa.String(length=30), nullable=False, server_default="web"),
    )
    op.add_column(
        "findings",
        sa.Column("platform", sa.String(length=20), nullable=True),
    )
    op.add_column(
        "findings",
        sa.Column("masvs_category", sa.String(length=80), nullable=True),
    )
    op.add_column(
        "findings",
        sa.Column("affected_component", sa.String(length=500), nullable=True),
    )
    op.add_column(
        "findings",
        sa.Column("mobile_application_id", sa.Uuid(), nullable=True),
    )
    op.create_index("ix_findings_asset_type", "findings", ["asset_type"])
    op.create_index("ix_findings_mobile_application_id", "findings", ["mobile_application_id"])


def downgrade() -> None:
    op.drop_index("ix_findings_mobile_application_id", table_name="findings")
    op.drop_index("ix_findings_asset_type", table_name="findings")
    op.drop_column("findings", "mobile_application_id")
    op.drop_column("findings", "affected_component")
    op.drop_column("findings", "masvs_category")
    op.drop_column("findings", "platform")
    op.drop_column("findings", "asset_type")
    op.drop_column("findings", "risk_model_version")
    op.drop_column("findings", "risk_breakdown")
