"""001_initial_schema

Revision ID: 001_initial_schema
Revises: 
Create Date: 2026-10-24 20:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '001_initial_schema'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. users
    op.create_table(
        'users',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('username', sa.String(length=100), unique=True, nullable=False, index=True),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('full_name', sa.String(length=255), nullable=False),
        sa.Column('role', sa.String(length=20), nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
    )

    # 2. classes
    op.create_table(
        'classes',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('code', sa.String(length=50), unique=True, nullable=False, index=True),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
    )

    # 3. class_members
    op.create_table(
        'class_members',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('class_id', sa.String(length=36), sa.ForeignKey('classes.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_id', sa.String(length=36), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('member_role', sa.String(length=20), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.UniqueConstraint('class_id', 'user_id', 'member_role', name='uq_class_user_role')
    )

    # 4. campaigns
    op.create_table(
        'campaigns',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('class_id', sa.String(length=36), sa.ForeignKey('classes.id', ondelete='CASCADE'), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('term', sa.String(length=50), nullable=False),
        sa.Column('status', sa.String(length=20), server_default='DRAFT', nullable=False),
        sa.Column('open_at', sa.DateTime(), nullable=False),
        sa.Column('submission_deadline_at', sa.DateTime(), nullable=False),
        sa.Column('supplement_period_hours', sa.Integer(), server_default='48', nullable=False),
        sa.Column('appeal_period_hours', sa.Integer(), server_default='72', nullable=False),
        sa.Column('reminder_after_hours', sa.Integer(), server_default='48', nullable=False),
        sa.Column('max_info_rounds', sa.Integer(), server_default='2', nullable=False),
        sa.Column('max_proof_rounds', sa.Integer(), server_default='2', nullable=False),
        sa.Column('opened_at', sa.DateTime(), nullable=True),
        sa.Column('published_at', sa.DateTime(), nullable=True),
        sa.Column('finalized_at', sa.DateTime(), nullable=True),
        sa.Column('created_by', sa.String(length=36), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
    )

    # 5. criteria
    op.create_table(
        'criteria',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('campaign_id', sa.String(length=36), sa.ForeignKey('campaigns.id', ondelete='CASCADE'), nullable=False),
        sa.Column('code', sa.String(length=50), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('max_score', sa.Numeric(precision=5, scale=2), nullable=False),
        sa.Column('requires_evidence', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('sort_order', sa.Integer(), server_default='1', nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.UniqueConstraint('campaign_id', 'code', name='uq_campaign_criterion_code')
    )

    # 6. cases
    op.create_table(
        'cases',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('campaign_id', sa.String(length=36), sa.ForeignKey('campaigns.id', ondelete='CASCADE'), nullable=False),
        sa.Column('student_id', sa.String(length=36), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('status', sa.String(length=30), server_default='DRAFT', nullable=False),
        sa.Column('info_round', sa.Integer(), server_default='0', nullable=False),
        sa.Column('proof_round', sa.Integer(), server_default='0', nullable=False),
        sa.Column('claimed_total', sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column('proposed_total', sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column('final_total', sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column('submitted_at', sa.DateTime(), nullable=True),
        sa.Column('published_at', sa.DateTime(), nullable=True),
        sa.Column('appeal_deadline_at', sa.DateTime(), nullable=True),
        sa.Column('acceptance_source', sa.String(length=30), nullable=True),
        sa.Column('version', sa.Integer(), server_default='1', nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.UniqueConstraint('campaign_id', 'student_id', name='uq_campaign_student_case')
    )

    # 7. claims
    op.create_table(
        'claims',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('case_id', sa.String(length=36), sa.ForeignKey('cases.id', ondelete='CASCADE'), nullable=False),
        sa.Column('criterion_id', sa.String(length=36), sa.ForeignKey('criteria.id', ondelete='CASCADE'), nullable=False),
        sa.Column('self_score', sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column('student_note', sa.Text(), nullable=True),
        sa.Column('approved_score', sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column('bcs_reason', sa.Text(), nullable=True),
        sa.Column('reviewed_by', sa.String(length=36), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.UniqueConstraint('case_id', 'criterion_id', name='uq_case_criterion_claim')
    )

    # 8. evidence_files
    op.create_table(
        'evidence_files',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('claim_id', sa.String(length=36), sa.ForeignKey('claims.id', ondelete='CASCADE'), nullable=False),
        sa.Column('storage_key', sa.String(length=255), unique=True, nullable=False),
        sa.Column('original_name', sa.String(length=255), nullable=False),
        sa.Column('mime_type', sa.String(length=100), nullable=False),
        sa.Column('size_bytes', sa.BigInteger(), nullable=False),
        sa.Column('sha256', sa.String(length=64), nullable=False),
        sa.Column('uploaded_by', sa.String(length=36), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('uploaded_at', sa.DateTime(), nullable=False),
        sa.Column('version_no', sa.Integer(), server_default='1', nullable=False),
        sa.Column('is_current', sa.Boolean(), server_default='true', nullable=False),
    )

    # 9. supplement_requests
    op.create_table(
        'supplement_requests',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('case_id', sa.String(length=36), sa.ForeignKey('cases.id', ondelete='CASCADE'), nullable=False),
        sa.Column('kind', sa.String(length=20), nullable=False),
        sa.Column('criterion_id', sa.String(length=36), sa.ForeignKey('criteria.id', ondelete='SET NULL'), nullable=True),
        sa.Column('reason', sa.Text(), nullable=False),
        sa.Column('round_no', sa.Integer(), nullable=False),
        sa.Column('requested_by', sa.String(length=36), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('requested_at', sa.DateTime(), nullable=False),
        sa.Column('deadline_at', sa.DateTime(), nullable=False),
        sa.Column('fulfilled_at', sa.DateTime(), nullable=True),
    )

    # 10. meetings
    op.create_table(
        'meetings',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('campaign_id', sa.String(length=36), sa.ForeignKey('campaigns.id', ondelete='CASCADE'), nullable=False),
        sa.Column('kind', sa.String(length=20), nullable=False),
        sa.Column('held_at', sa.DateTime(), nullable=False),
        sa.Column('note', sa.Text(), nullable=True),
        sa.Column('recorded_by', sa.String(length=36), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.UniqueConstraint('campaign_id', 'kind', name='uq_campaign_meeting_kind')
    )

    # 11. appeals
    op.create_table(
        'appeals',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('case_id', sa.String(length=36), sa.ForeignKey('cases.id', ondelete='CASCADE'), nullable=False),
        sa.Column('criterion_id', sa.String(length=36), sa.ForeignKey('criteria.id', ondelete='CASCADE'), nullable=False),
        sa.Column('student_reason', sa.Text(), nullable=False),
        sa.Column('status', sa.String(length=20), server_default='OPEN', nullable=False),
        sa.Column('resolution', sa.String(length=20), nullable=True),
        sa.Column('new_score', sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column('bcs_reason', sa.Text(), nullable=True),
        sa.Column('submitted_at', sa.DateTime(), nullable=False),
        sa.Column('resolved_at', sa.DateTime(), nullable=True),
        sa.Column('resolved_by', sa.String(length=36), sa.ForeignKey('users.id'), nullable=True),
        sa.UniqueConstraint('case_id', 'criterion_id', name='uq_case_criterion_appeal')
    )

    # 12. score_snapshots
    op.create_table(
        'score_snapshots',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('case_id', sa.String(length=36), sa.ForeignKey('cases.id', ondelete='CASCADE'), nullable=False),
        sa.Column('kind', sa.String(length=20), nullable=False),
        sa.Column('per_criterion_json', sa.JSON(), nullable=False),
        sa.Column('total', sa.Numeric(precision=5, scale=2), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('created_by', sa.String(length=36), sa.ForeignKey('users.id'), nullable=True),
        sa.UniqueConstraint('case_id', 'kind', name='uq_case_snapshot_kind')
    )

    # 13. notifications
    op.create_table(
        'notifications',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('user_id', sa.String(length=36), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('case_id', sa.String(length=36), sa.ForeignKey('cases.id', ondelete='CASCADE'), nullable=True),
        sa.Column('type', sa.String(length=50), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('body', sa.Text(), nullable=False),
        sa.Column('dedup_key', sa.String(length=255), unique=True, nullable=False),
        sa.Column('read_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
    )

    # 14. audit_events
    op.create_table(
        'audit_events',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('actor_user_id', sa.String(length=36), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('campaign_id', sa.String(length=36), sa.ForeignKey('campaigns.id', ondelete='CASCADE'), nullable=False),
        sa.Column('case_id', sa.String(length=36), sa.ForeignKey('cases.id', ondelete='CASCADE'), nullable=True),
        sa.Column('action', sa.String(length=100), nullable=False),
        sa.Column('before_json', sa.JSON(), nullable=True),
        sa.Column('after_json', sa.JSON(), nullable=True),
        sa.Column('request_id', sa.String(length=64), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
    )

    # 15. sessions
    op.create_table(
        'sessions',
        sa.Column('id', sa.String(length=64), primary_key=True),
        sa.Column('user_id', sa.String(length=36), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('csrf_hash', sa.String(length=128), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table('sessions')
    op.drop_table('audit_events')
    op.drop_table('notifications')
    op.drop_table('score_snapshots')
    op.drop_table('appeals')
    op.drop_table('meetings')
    op.drop_table('supplement_requests')
    op.drop_table('evidence_files')
    op.drop_table('claims')
    op.drop_table('cases')
    op.drop_table('criteria')
    op.drop_table('campaigns')
    op.drop_table('class_members')
    op.drop_table('classes')
    op.drop_table('users')
