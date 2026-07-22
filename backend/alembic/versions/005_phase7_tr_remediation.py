"""Phase 7: Turkish remediation guides and Plesk paths."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "005_phase7_tr_remediation"
down_revision: Union[str, None] = "004_phase6_finding_history"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("findings", sa.Column("risk_explanation", sa.Text(), nullable=True))
    op.add_column(
        "findings",
        sa.Column("remediation_steps", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.add_column(
        "findings",
        sa.Column("config_file_paths", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.add_column("findings", sa.Column("config_snippet", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("findings", "config_snippet")
    op.drop_column("findings", "config_file_paths")
    op.drop_column("findings", "remediation_steps")
    op.drop_column("findings", "risk_explanation")
