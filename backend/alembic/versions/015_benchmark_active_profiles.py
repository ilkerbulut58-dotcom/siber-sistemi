"""Add hidden benchmark-active scan profiles for isolated lab runs."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "015_benchmark_active_profiles"
down_revision: Union[str, None] = "014_realistic_benchmark"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        sa.text(
            """
            INSERT INTO scan_profiles (id, name, display_name, description, is_active, tools)
            SELECT gen_random_uuid(), 'benchmark-active-web', 'Benchmark Active Web',
                   'Isolated Juice Shop active benchmark profile (system lab only).',
                   true, '{"tools":["zap","nuclei"]}'::json
            WHERE NOT EXISTS (
                SELECT 1 FROM scan_profiles WHERE name = 'benchmark-active-web'
            )
            """
        )
    )
    op.execute(
        sa.text(
            """
            INSERT INTO scan_profiles (id, name, display_name, description, is_active, tools)
            SELECT gen_random_uuid(), 'benchmark-active-api', 'Benchmark Active API',
                   'Isolated crAPI active benchmark profile (system lab only).',
                   true, '{"tools":["zap","nuclei"]}'::json
            WHERE NOT EXISTS (
                SELECT 1 FROM scan_profiles WHERE name = 'benchmark-active-api'
            )
            """
        )
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            """
            DELETE FROM scan_profiles
            WHERE name IN ('benchmark-active-web', 'benchmark-active-api')
            """
        )
    )
