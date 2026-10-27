"""002_criteria_templates_and_cadre_roles

Revision ID: 002_criteria_templates_and_cadre_roles
Revises: 001_initial_schema
Create Date: 2026-10-25 15:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = '002_criteria_templates_and_cadre_roles'
down_revision: Union[str, None] = '001_initial_schema'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 0. Widen alembic_version.version_num to support revision IDs longer than 32 characters
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.alter_column(
            'alembic_version',
            'version_num',
            existing_type=sa.String(length=32),
            type_=sa.String(length=128),
            existing_nullable=False,
        )

    # 1. evaluation_templates
    op.create_table(
        'evaluation_templates',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('code', sa.String(length=50), unique=True, nullable=False, index=True),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('version', sa.Integer(), server_default='1', nullable=False),
        sa.Column('total_max_score', sa.Numeric(precision=5, scale=2), server_default='100.00', nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
    )

    # 2. template_criteria
    op.create_table(
        'template_criteria',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('template_id', sa.String(length=36), sa.ForeignKey('evaluation_templates.id', ondelete='CASCADE'), nullable=False),
        sa.Column('code', sa.String(length=50), nullable=False),
        sa.Column('section_code', sa.String(length=50), nullable=False),
        sa.Column('section_title', sa.String(length=255), nullable=False),
        sa.Column('section_max_score', sa.Numeric(precision=5, scale=2), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('max_score', sa.Numeric(precision=5, scale=2), nullable=False),
        sa.Column('requires_evidence', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('evidence_notes', sa.Text(), nullable=True),
        sa.Column('allowed_input_roles', sa.JSON(), nullable=True),
        sa.Column('rule_config', sa.JSON(), nullable=True),
        sa.Column('sort_order', sa.Integer(), server_default='1', nullable=False),
        sa.UniqueConstraint('template_id', 'code', name='uq_template_criterion_code')
    )

    # 3. user_positions (Quản lý chức vụ cán bộ theo học kỳ do Admin xác nhận)
    op.create_table(
        'user_positions',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('user_id', sa.String(length=36), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('term', sa.String(length=50), nullable=False),
        sa.Column('position_title', sa.String(length=100), nullable=False),
        sa.Column('organization', sa.String(length=255), nullable=False),
        sa.Column('is_confirmed', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('confirmed_by', sa.String(length=36), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
    )

    # 4. Add template_code to campaigns
    op.add_column('campaigns', sa.Column('template_code', sa.String(length=50), server_default='LEGACY_DEMO', nullable=True))

    # 5. Add section and rule columns to criteria
    op.add_column('criteria', sa.Column('section_code', sa.String(length=50), nullable=True))
    op.add_column('criteria', sa.Column('section_title', sa.String(length=255), nullable=True))
    op.add_column('criteria', sa.Column('section_max_score', sa.Numeric(precision=5, scale=2), nullable=True))
    op.add_column('criteria', sa.Column('evidence_notes', sa.Text(), nullable=True))
    op.add_column('criteria', sa.Column('allowed_input_roles', sa.JSON(), nullable=True))
    op.add_column('criteria', sa.Column('rule_config', sa.JSON(), nullable=True))

    # 6. Add academic_gpa to claims
    op.add_column('claims', sa.Column('academic_gpa', sa.Numeric(precision=4, scale=2), nullable=True))

    if bind.dialect.name == "postgresql":
        for table in ["evaluation_templates", "template_criteria", "user_positions"]:
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
    op.drop_column('claims', 'academic_gpa')
    op.drop_column('criteria', 'rule_config')
    op.drop_column('criteria', 'allowed_input_roles')
    op.drop_column('criteria', 'evidence_notes')
    op.drop_column('criteria', 'section_max_score')
    op.drop_column('criteria', 'section_title')
    op.drop_column('criteria', 'section_code')
    op.drop_column('campaigns', 'template_code')
    op.drop_table('user_positions')
    op.drop_table('template_criteria')
    op.drop_table('evaluation_templates')
