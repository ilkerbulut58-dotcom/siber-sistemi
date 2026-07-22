"""Realistic benchmark automation_support and framework_refs."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "014_realistic_benchmark"
down_revision: Union[str, None] = "013_benchmark_lab"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "expected_findings",
        sa.Column(
            "automation_support",
            sa.String(length=30),
            nullable=False,
            server_default="supported",
        ),
    )
    op.add_column(
        "expected_findings",
        sa.Column("framework_refs", sa.JSON(), nullable=True),
    )
    op.create_check_constraint(
        "ck_expected_findings_automation_support",
        "expected_findings",
        sa.text(
            "automation_support IN ('supported', 'partially_supported', "
            "'manual_only', 'unsupported')"
        ),
    )


def downgrade() -> None:
    op.drop_constraint("ck_expected_findings_automation_support", "expected_findings", type_="check")
    op.drop_column("expected_findings", "framework_refs")
    op.drop_column("expected_findings", "automation_support")
