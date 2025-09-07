"""add chat tables

Revision ID: 002
Revises: 001
Create Date: 2025-09-05 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.execute('CREATE TYPE chat_room_type AS ENUM (\'direct\', \'group\', \'support\', \'broadcast\')')
    op.execute('CREATE TYPE chat_participant_role AS ENUM (\'admin\', \'moderator\', \'member\')')
    op.execute('CREATE TYPE chat_message_type AS ENUM (\'text\', \'image\', \'file\', \'system\')')

    op.create_table('chat_rooms',
        sa.Column('id', UUID(), nullable=False),
        sa.Column('tenant_id', UUID(), nullable=False),
        sa.Column('type', sa.Enum('direct', 'group', 'support', 'broadcast', name='chat_room_type'), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('metadata', JSONB(), nullable=False, server_default='{}'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_table('chat_room_participants',
        sa.Column('id', UUID(), nullable=False),
        sa.Column('room_id', UUID(), nullable=False),
        sa.Column('user_id', UUID(), nullable=False),
        sa.Column('role', sa.Enum('admin', 'moderator', 'member', name='chat_participant_role'), nullable=False),
        sa.Column('joined_at', sa.DateTime(), nullable=False),
        sa.Column('last_read_at', sa.DateTime(), nullable=False),
        sa.Column('is_muted', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('settings', JSONB(), nullable=False, server_default='{}'),
        sa.ForeignKeyConstraint(['room_id'], ['chat_rooms.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('room_id', 'user_id', name='uq_room_participant')
    )

    op.create_table('chat_messages',
        sa.Column('id', UUID(), nullable=False),
        sa.Column('room_id', UUID(), nullable=False),
        sa.Column('user_id', UUID(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('content_type', sa.Enum('text', 'image', 'file', 'system', name='chat_message_type'), nullable=False),
        sa.Column('metadata', JSONB(), nullable=False, server_default='{}'),
        sa.Column('parent_id', UUID(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['parent_id'], ['chat_messages.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['room_id'], ['chat_rooms.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_table('chat_message_reactions',
        sa.Column('id', UUID(), nullable=False),
        sa.Column('message_id', UUID(), nullable=False),
        sa.Column('user_id', UUID(), nullable=False),
        sa.Column('emoji', sa.String(length=32), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['message_id'], ['chat_messages.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('message_id', 'user_id', 'emoji', name='uq_message_user_emoji')
    )

    op.create_table('chat_message_receipts',
        sa.Column('id', UUID(), nullable=False),
        sa.Column('message_id', UUID(), nullable=False),
        sa.Column('user_id', UUID(), nullable=False),
        sa.Column('received_at', sa.DateTime(), nullable=False),
        sa.Column('read_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['message_id'], ['chat_messages.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('message_id', 'user_id', name='uq_message_receipt')
    )

    op.create_index('ix_chat_messages_room_created',
                    'chat_messages',
                    ['room_id', 'created_at'],
                    unique=False)

def downgrade() -> None:
    op.drop_index('ix_chat_messages_room_created', table_name='chat_messages')
    op.drop_table('chat_message_receipts')
    op.drop_table('chat_message_reactions')
    op.drop_table('chat_messages')
    op.drop_table('chat_room_participants')
    op.drop_table('chat_rooms')
    op.execute('DROP TYPE chat_message_type')
    op.execute('DROP TYPE chat_participant_role')
    op.execute('DROP TYPE chat_room_type')