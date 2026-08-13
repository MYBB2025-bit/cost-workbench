"""add task_job table

Revision ID: 8a2f1c9d4e07
Revises: 147c5fbdc141
Create Date: 2026-08-13 12:50:00.000000

"""
from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '8a2f1c9d4e07'
down_revision: Union[str, Sequence[str], None] = '147c5fbdc141'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'task_job',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('job_uuid', sa.String(length=64), nullable=False),
        sa.Column('task_type', sa.String(length=64), nullable=False),
        sa.Column('status', sa.String(length=32), nullable=True),
        sa.Column('progress', sa.Integer(), nullable=True),
        sa.Column('total', sa.Integer(), nullable=True),
        sa.Column('processed', sa.Integer(), nullable=True),
        sa.Column('result', sa.JSON(), nullable=True),
        sa.Column('error', sa.Text(), nullable=True),
        sa.Column('created_by', sa.BigInteger(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('finished_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_task_job_job_uuid', 'task_job', ['job_uuid'], unique=True)
    op.create_index('ix_task_job_task_type', 'task_job', ['task_type'])


def downgrade() -> None:
    op.drop_index('ix_task_job_task_type', table_name='task_job')
    op.drop_index('ix_task_job_job_uuid', table_name='task_job')
    op.drop_table('task_job')
