"""Add explicit academic term dates for deterministic evidence date checks.

Revision ID: 004_campaign_term_window
Revises: 003_ai_review_runs
"""

from alembic import op
import sqlalchemy as sa


revision = "004_campaign_term_window"
down_revision = "003_ai_review_runs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("campaigns", sa.Column("term_start_on", sa.Date(), nullable=True))
    op.add_column("campaigns", sa.Column("term_end_on", sa.Date(), nullable=True))


def downgrade() -> None:
    op.drop_column("campaigns", "term_end_on")
    op.drop_column("campaigns", "term_start_on")
