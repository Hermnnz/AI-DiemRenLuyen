"""Add durable AI review runs and two ordered step records.

Revision ID: 003_ai_review_runs
Revises: 002_criteria_templates_and_cadre_roles
"""

from alembic import op
import sqlalchemy as sa


revision = "003_ai_review_runs"
down_revision = "002_criteria_templates_and_cadre_roles"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ai_review_runs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("case_id", sa.String(36), sa.ForeignKey("cases.id", ondelete="CASCADE"), nullable=False),
        sa.Column("requested_by", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("case_version", sa.Integer(), nullable=False),
        sa.Column("rubric_version", sa.String(100), nullable=False),
        sa.Column("evidence_fingerprint", sa.String(64), nullable=False),
        sa.Column("idempotency_key", sa.String(64), nullable=False, unique=True),
        sa.Column("snapshot_json", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(20), server_default="QUEUED", nullable=False),
        sa.Column("attempt_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("lease_until", sa.DateTime(), nullable=True),
        sa.Column("provider", sa.String(100), nullable=True),
        sa.Column("model", sa.String(100), nullable=True),
        sa.Column("prompt_version", sa.String(50), nullable=True),
        sa.Column("result_json", sa.JSON(), nullable=True),
        sa.Column("error_code", sa.String(100), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_ai_review_runs_case_id", "ai_review_runs", ["case_id"])
    op.create_table(
        "ai_agent_steps",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("run_id", sa.String(36), sa.ForeignKey("ai_review_runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("kind", sa.String(30), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(20), server_default="PENDING", nullable=False),
        sa.Column("output_json", sa.JSON(), nullable=True),
        sa.Column("error_code", sa.String(100), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("run_id", "kind", name="uq_ai_run_step_kind"),
    )
    op.create_index("ix_ai_agent_steps_run_id", "ai_agent_steps", ["run_id"])

    if op.get_bind().dialect.name == "postgresql":
        for table in ["ai_review_runs", "ai_agent_steps"]:
            op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
            op.execute(f"""
                DO $$ BEGIN
                    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN
                        REVOKE ALL ON TABLE {table} FROM anon;
                    END IF;
                    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
                        REVOKE ALL ON TABLE {table} FROM authenticated;
                    END IF;
                END $$;
            """)


def downgrade() -> None:
    op.drop_index("ix_ai_agent_steps_run_id", table_name="ai_agent_steps")
    op.drop_table("ai_agent_steps")
    op.drop_index("ix_ai_review_runs_case_id", table_name="ai_review_runs")
    op.drop_table("ai_review_runs")
