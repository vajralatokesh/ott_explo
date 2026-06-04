"""Init Schema

Revision ID: dcacf664b954
Revises: 
Create Date: 2026-05-21 01:32:33.791911

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'dcacf664b954'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # 1. users table FIRST (profiles depends on it)
    op.create_table('users',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('username', sa.String(length=80), nullable=False),
    sa.Column('password_hash', sa.String(length=255), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_users_username'), ['username'], unique=True)

    # 2. profiles with user_id FK
    op.create_table('profiles',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=100), nullable=False),
    sa.Column('avatar', sa.String(length=255), nullable=False),
    sa.Column('is_kids', sa.Boolean(), nullable=True),
    sa.Column('pin_hash', sa.String(length=255), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('profiles', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_profiles_user_id'), ['user_id'], unique=False)

    # 3. watchlist
    op.create_table('watchlist',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('profile_id', sa.Integer(), nullable=False),
    sa.Column('content_id', sa.String(length=50), nullable=False),
    sa.Column('content_type', sa.String(length=20), nullable=False),
    sa.Column('title', sa.String(length=255), nullable=False),
    sa.Column('poster', sa.String(length=500), nullable=True),
    sa.Column('added_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['profile_id'], ['profiles.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('profile_id', 'content_id', 'content_type', name='uq_profile_content')
    )
    with op.batch_alter_table('watchlist', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_watchlist_content_id'), ['content_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_watchlist_profile_id'), ['profile_id'], unique=False)

    # 4. continue_watching
    op.create_table('continue_watching',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('profile_id', sa.Integer(), nullable=False),
    sa.Column('content_id', sa.String(length=50), nullable=False),
    sa.Column('content_type', sa.String(length=20), nullable=False),
    sa.Column('title', sa.String(length=255), nullable=False),
    sa.Column('poster', sa.String(length=500), nullable=True),
    sa.Column('progress', sa.Integer(), nullable=True),
    sa.Column('duration', sa.Integer(), nullable=True),
    sa.Column('season', sa.Integer(), nullable=True),
    sa.Column('episode', sa.Integer(), nullable=True),
    sa.Column('updated_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['profile_id'], ['profiles.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('profile_id', 'content_id', 'content_type', name='uq_profile_continue')
    )
    with op.batch_alter_table('continue_watching', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_continue_watching_content_id'), ['content_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_continue_watching_profile_id'), ['profile_id'], unique=False)

    # 5. recently_watched
    op.create_table('recently_watched',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('profile_id', sa.Integer(), nullable=False),
    sa.Column('content_id', sa.String(length=50), nullable=False),
    sa.Column('content_type', sa.String(length=20), nullable=False),
    sa.Column('title', sa.String(length=255), nullable=False),
    sa.Column('poster', sa.String(length=500), nullable=True),
    sa.Column('watched_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['profile_id'], ['profiles.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('recently_watched', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_recently_watched_profile_id'), ['profile_id'], unique=False)

    # 6. search_history
    op.create_table('search_history',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('profile_id', sa.Integer(), nullable=False),
    sa.Column('query', sa.String(length=255), nullable=False),
    sa.Column('searched_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['profile_id'], ['profiles.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('search_history', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_search_history_profile_id'), ['profile_id'], unique=False)


def downgrade():
    op.drop_table('search_history')
    op.drop_table('recently_watched')
    op.drop_table('continue_watching')
    op.drop_table('watchlist')
    op.drop_table('profiles')
    op.drop_table('users')
