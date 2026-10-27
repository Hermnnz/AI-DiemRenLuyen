"""Record BCS feedback on AI evidence assessments for quality evaluation.

Revision ID: 007_bcs_ai_feedbacks
Revises: 006_final_handoffs
"""

from alembic import op
import sqlalchemy as sa


revision = "007_bcs_ai_feedbacks"
down_revision = "006_final_handoffs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "bcs_ai_feedbacks",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("evidence_file_id", sa.String(length=36), sa.ForeignKey("evidence_files.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("file_sha256", sa.String(length=64), nullable=False),
        sa.Column("file_version_no", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("case_id", sa.String(length=36), sa.ForeignKey("cases.id", ondelete="CASCADE"), nullable=False),
        sa.Column("criterion_id", sa.String(length=36), sa.ForeignKey("criteria.id", ondelete="CASCADE"), nullable=False),
        sa.Column("criterion_code", sa.String(length=50), nullable=False),
        sa.Column("bcs_decision", sa.String(length=24), nullable=False),
        sa.Column("bcs_reason", sa.Text(), nullable=False),
        sa.Column("reviewed_by", sa.String(length=36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("reviewed_at", sa.DateTime(), nullable=False),
        sa.Column("ai_run_id", sa.String(length=36), sa.ForeignKey("ai_review_runs.id", ondelete="SET NULL"), nullable=True),
        sa.Column("ai_model", sa.String(length=100), nullable=True),
        sa.Column("ai_prompt_version", sa.String(length=100), nullable=True),
        sa.Column("ai_verdict", sa.String(length=30), nullable=True),
        sa.Column("ai_reason", sa.Text(), nullable=True),
        sa.Column("ai_assessment_json", sa.JSON(), nullable=True),
        sa.Column("matching_status", sa.String(length=30), nullable=False),
        sa.Column("discrepancy_status", sa.String(length=30), nullable=False),
        sa.Column("ground_truth_status", sa.String(length=30), server_default="UNVERIFIED", nullable=False),
        sa.Column("ground_truth_label", sa.String(length=30), nullable=True),
        sa.Column("verification_reason", sa.Text(), nullable=True),
        sa.Column("verified_by", sa.String(length=36), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("verified_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint("bcs_decision IN ('ACCEPT', 'REQUEST_SUPPLEMENT', 'REJECT_ITEM', 'HOLD')", name="ck_feedback_bcs_decision"),
        sa.CheckConstraint("ground_truth_status IN ('UNVERIFIED', 'VERIFIED')", name="ck_feedback_ground_truth_status"),
        sa.CheckConstraint("ground_truth_label IS NULL OR ground_truth_label IN ('SUPPORTED', 'FLAGGED', 'UNKNOWN')", name="ck_feedback_ground_truth_label"),
    )
    op.create_index("ix_bcs_ai_feedbacks_evidence_file_id", "bcs_ai_feedbacks", ["evidence_file_id"])
    op.create_index("ix_bcs_ai_feedbacks_case_id", "bcs_ai_feedbacks", ["case_id"])
    op.create_index("ix_bcs_ai_feedbacks_discrepancy_status", "bcs_ai_feedbacks", ["discrepancy_status"])
    op.create_index("ix_bcs_ai_feedbacks_ground_truth_status", "bcs_ai_feedbacks", ["ground_truth_status"])

    if op.get_bind().dialect.name == "postgresql":
        op.execute("ALTER TABLE bcs_ai_feedbacks ENABLE ROW LEVEL SECURITY")
        op.execute("""
            DO $$ BEGIN
                IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN
                    REVOKE ALL ON TABLE bcs_ai_feedbacks FROM anon;
                END IF;
                IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
                    REVOKE ALL ON TABLE bcs_ai_feedbacks FROM authenticated;
                END IF;
            END $$;
        """)


def downgrade() -> None:
    op.drop_index("ix_bcs_ai_feedbacks_ground_truth_status", table_name="bcs_ai_feedbacks")
    op.drop_index("ix_bcs_ai_feedbacks_discrepancy_status", table_name="bcs_ai_feedbacks")
    op.drop_index("ix_bcs_ai_feedbacks_case_id", table_name="bcs_ai_feedbacks")
    op.drop_index("ix_bcs_ai_feedbacks_evidence_file_id", table_name="bcs_ai_feedbacks")
    op.drop_table("bcs_ai_feedbacks")
