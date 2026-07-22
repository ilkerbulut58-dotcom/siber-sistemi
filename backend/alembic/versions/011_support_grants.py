"""Timed platform support access grants."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "011_support_grants"
down_revision: Union[str, None] = "010_platform_managed_workspaces"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "organization_support_grants",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("granted_to_user_id", sa.Uuid(), nullable=False),
        sa.Column("granted_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_by_user_id", sa.Uuid(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["granted_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["granted_to_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.ForeignKeyConstraint(["revoked_by_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_support_grants_org_user",
        "organization_support_grants",
        ["organization_id", "granted_to_user_id"],
    )
    op.create_index(
        op.f("ix_organization_support_grants_expires_at"),
        "organization_support_grants",
        ["expires_at"],
    )
    op.create_index(
        op.f("ix_organization_support_grants_granted_to_user_id"),
        "organization_support_grants",
        ["granted_to_user_id"],
    )
    op.create_index(
        op.f("ix_organization_support_grants_organization_id"),
        "organization_support_grants",
        ["organization_id"],
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_organization_support_grants_organization_id"),
        table_name="organization_support_grants",
    )
    op.drop_index(
        op.f("ix_organization_support_grants_granted_to_user_id"),
        table_name="organization_support_grants",
    )
    op.drop_index(
        op.f("ix_organization_support_grants_expires_at"),
        table_name="organization_support_grants",
    )
    op.drop_index("ix_support_grants_org_user", table_name="organization_support_grants")
    op.drop_table("organization_support_grants")
