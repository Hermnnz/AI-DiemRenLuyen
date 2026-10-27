"""Record delivery and receipt of finalized campaign scores.

Revision ID: 006_final_handoffs
Revises: 005_bcs_evidence_decisions
"""

from alembic import op
import sqlalchemy as sa


revision = "006_final_handoffs"
down_revision = "005_bcs_evidence_decisions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "final_handoffs",
        sa.Column("campaign_id", sa.String(length=36), sa.ForeignKey("campaigns.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("snapshot_sha256", sa.String(length=64), nullable=False),
        sa.Column("sent_by", sa.String(length=36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("sent_at", sa.DateTime(), nullable=False),
        sa.Column("received_by", sa.String(length=36), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("received_at", sa.DateTime(), nullable=True),
    )
    if op.get_bind().dialect.name == "postgresql":
        op.execute("ALTER TABLE final_handoffs ENABLE ROW LEVEL SECURITY")
        op.execute("""
            DO $$ BEGIN
                IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN
                    REVOKE ALL ON TABLE final_handoffs FROM anon;
                END IF;
                IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
                    REVOKE ALL ON TABLE final_handoffs FROM authenticated;
                END IF;
            END $$;
        """)


def downgrade() -> None:
    op.drop_table("final_handoffs")
