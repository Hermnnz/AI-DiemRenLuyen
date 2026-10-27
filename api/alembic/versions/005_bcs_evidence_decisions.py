"""Record explicit BCS decisions for individual evidence files.

Revision ID: 005_bcs_evidence_decisions
Revises: 004_campaign_term_window
"""

from alembic import op
import sqlalchemy as sa


revision = "005_bcs_evidence_decisions"
down_revision = "004_campaign_term_window"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "bcs_evidence_decisions",
        sa.Column("evidence_file_id", sa.String(length=36), sa.ForeignKey("evidence_files.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("decision", sa.String(length=24), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("reviewed_by", sa.String(length=36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("reviewed_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint("decision IN ('ACCEPT', 'REQUEST_SUPPLEMENT', 'REJECT_ITEM', 'HOLD')", name="ck_bcs_evidence_decision"),
    )
    if op.get_bind().dialect.name == "postgresql":
        op.execute("ALTER TABLE bcs_evidence_decisions ENABLE ROW LEVEL SECURITY")
        op.execute("""
            DO $$ BEGIN
                IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN
                    REVOKE ALL ON TABLE bcs_evidence_decisions FROM anon;
                END IF;
                IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
                    REVOKE ALL ON TABLE bcs_evidence_decisions FROM authenticated;
                END IF;
            END $$;
        """)


def downgrade() -> None:
    op.drop_table("bcs_evidence_decisions")
