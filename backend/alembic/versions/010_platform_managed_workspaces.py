"""Platform-managed workspaces for operator-led security assessments."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "010_platform_managed_workspaces"
down_revision: Union[str, None] = "009_mobile_security"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "organizations",
        sa.Column(
            "is_managed_workspace",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.create_index(
        "ix_organizations_managed_workspace",
        "organizations",
        ["is_managed_workspace"],
    )


def downgrade() -> None:
    op.drop_index("ix_organizations_managed_workspace", table_name="organizations")
    op.drop_column("organizations", "is_managed_workspace")
