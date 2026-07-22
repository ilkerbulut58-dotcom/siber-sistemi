"""Detection Quality & Benchmark Lab."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "013_benchmark_lab"
down_revision: Union[str, None] = "012_target_site_profiles"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "organizations",
        sa.Column("is_system_scope", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.create_table(
        "benchmark_targets",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("target_type", sa.String(20), nullable=False),
        sa.Column("target_reference", sa.String(1000), nullable=False),
        sa.Column("environment", sa.String(50), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("metadata", sa.JSON()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_index(op.f("ix_benchmark_targets_name"), "benchmark_targets", ["name"])
    op.create_index(op.f("ix_benchmark_targets_target_type"), "benchmark_targets", ["target_type"])
    op.create_table(
        "expected_findings",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("benchmark_target_id", sa.Uuid(), nullable=False),
        sa.Column("expected_key", sa.String(255), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("category", sa.String(255)),
        sa.Column("severity", sa.String(20), nullable=False),
        sa.Column("affected_location", sa.String(1000)),
        sa.Column("description", sa.Text()),
        sa.Column("detection_required", sa.Boolean(), nullable=False),
        sa.Column("accepted_alternative_keys", sa.JSON()),
        sa.Column("expected_risk_score", sa.Float()),
        sa.Column("expected_ai_review_status", sa.String(50)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["benchmark_target_id"], ["benchmark_targets.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_expected_findings_benchmark_target_id"), "expected_findings", ["benchmark_target_id"])
    op.create_index(op.f("ix_expected_findings_expected_key"), "expected_findings", ["expected_key"])
    op.create_table(
        "benchmark_runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("benchmark_target_id", sa.Uuid(), nullable=False),
        sa.Column("scan_id", sa.Uuid()),
        sa.Column("mobile_application_id", sa.Uuid()),
        sa.Column("app_version", sa.String(100)),
        sa.Column("git_commit", sa.String(80)),
        sa.Column("scan_profile", sa.String(50)),
        sa.Column("fixture_set", sa.String(100), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("duration_seconds", sa.Float()),
        sa.Column("scanner_versions", sa.JSON()),
        sa.Column("error_log", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["benchmark_target_id"], ["benchmark_targets.id"]),
        sa.ForeignKeyConstraint(["scan_id"], ["scan_jobs.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_benchmark_runs_benchmark_target_id"), "benchmark_runs", ["benchmark_target_id"])
    op.create_index(op.f("ix_benchmark_runs_scan_id"), "benchmark_runs", ["scan_id"])
    op.create_index(op.f("ix_benchmark_runs_git_commit"), "benchmark_runs", ["git_commit"])
    op.create_table(
        "benchmark_results",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("benchmark_run_id", sa.Uuid(), nullable=False),
        sa.Column("expected_count", sa.Integer(), nullable=False),
        sa.Column("true_positive_count", sa.Integer(), nullable=False),
        sa.Column("false_negative_count", sa.Integer(), nullable=False),
        sa.Column("false_positive_count", sa.Integer(), nullable=False),
        sa.Column("duplicate_count", sa.Integer(), nullable=False),
        sa.Column("scanner_error_count", sa.Integer(), nullable=False),
        sa.Column("precision", sa.Float(), nullable=False),
        sa.Column("recall", sa.Float(), nullable=False),
        sa.Column("f1_score", sa.Float(), nullable=False),
        sa.Column("breakdown", sa.JSON()),
        sa.Column("previous_delta", sa.JSON()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["benchmark_run_id"], ["benchmark_runs.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("benchmark_run_id"),
    )
    op.create_index(op.f("ix_benchmark_results_benchmark_run_id"), "benchmark_results", ["benchmark_run_id"])
    op.create_table(
        "benchmark_finding_matches",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("benchmark_run_id", sa.Uuid(), nullable=False),
        sa.Column("expected_finding_id", sa.Uuid()),
        sa.Column("finding_id", sa.Uuid()),
        sa.Column("classification", sa.String(30), nullable=False),
        sa.Column("match_reason", sa.String(255)),
        sa.Column("details", sa.JSON()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["benchmark_run_id"], ["benchmark_runs.id"]),
        sa.ForeignKeyConstraint(["expected_finding_id"], ["expected_findings.id"]),
        sa.ForeignKeyConstraint(["finding_id"], ["findings.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_benchmark_finding_matches_benchmark_run_id"), "benchmark_finding_matches", ["benchmark_run_id"])
    op.create_index(op.f("ix_benchmark_finding_matches_expected_finding_id"), "benchmark_finding_matches", ["expected_finding_id"])
    op.create_index(op.f("ix_benchmark_finding_matches_finding_id"), "benchmark_finding_matches", ["finding_id"])


def downgrade() -> None:
    op.drop_table("benchmark_finding_matches")
    op.drop_table("benchmark_results")
    op.drop_table("benchmark_runs")
    op.drop_table("expected_findings")
    op.drop_table("benchmark_targets")
    op.drop_column("organizations", "is_system_scope")
