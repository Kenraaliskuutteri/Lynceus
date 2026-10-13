from alembic import op
import sqlalchemy as sa


revision = '0001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('alert_events',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('server_id', sa.String(), nullable=False),
    sa.Column('metric', sa.String(), nullable=False),
    sa.Column('value', sa.Float(), nullable=False),
    sa.Column('threshold', sa.Float(), nullable=False),
    sa.Column('status', sa.String(), nullable=False),
    sa.Column('triggered_at', sa.DateTime(), nullable=False),
    sa.Column('resolved_at', sa.DateTime(), nullable=True),
    sa.Column('acknowledged_at', sa.DateTime(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('alert_events', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_alert_events_server_id'), ['server_id'], unique=False)

    op.create_table('metric_logs',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('server_id', sa.String(), nullable=False),
    sa.Column('timestamp', sa.DateTime(), nullable=False),
    sa.Column('cpu_usage', sa.Float(), nullable=False),
    sa.Column('ram_usage', sa.Float(), nullable=False),
    sa.Column('disk_usage', sa.Float(), nullable=False),
    sa.Column('network_rx_kb', sa.Float(), nullable=False),
    sa.Column('network_tx_kb', sa.Float(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('metric_logs', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_metric_logs_server_id'), ['server_id'], unique=False)

    op.create_table('metric_rollups',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('server_id', sa.String(), nullable=False),
    sa.Column('bucket_start', sa.DateTime(), nullable=False),
    sa.Column('samples', sa.Integer(), nullable=False),
    sa.Column('cpu_avg', sa.Float(), nullable=False),
    sa.Column('cpu_max', sa.Float(), nullable=False),
    sa.Column('ram_avg', sa.Float(), nullable=False),
    sa.Column('ram_max', sa.Float(), nullable=False),
    sa.Column('disk_avg', sa.Float(), nullable=False),
    sa.Column('disk_max', sa.Float(), nullable=False),
    sa.Column('rx_avg', sa.Float(), nullable=False),
    sa.Column('rx_max', sa.Float(), nullable=False),
    sa.Column('tx_avg', sa.Float(), nullable=False),
    sa.Column('tx_max', sa.Float(), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('server_id', 'bucket_start', name='uq_rollup_server_bucket')
    )
    with op.batch_alter_table('metric_rollups', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_metric_rollups_bucket_start'), ['bucket_start'], unique=False)
        batch_op.create_index(batch_op.f('ix_metric_rollups_server_id'), ['server_id'], unique=False)

    op.create_table('servers',
    sa.Column('id', sa.String(), nullable=False),
    sa.Column('hostname', sa.String(), nullable=False),
    sa.Column('ip_address', sa.String(), nullable=False),
    sa.Column('last_seen', sa.DateTime(), nullable=True),
    sa.Column('cpu_threshold', sa.Float(), nullable=True),
    sa.Column('ram_threshold', sa.Float(), nullable=True),
    sa.Column('disk_threshold', sa.Float(), nullable=True),
    sa.Column('offline_threshold_seconds', sa.Integer(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('users',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('username', sa.String(), nullable=False),
    sa.Column('password_hash', sa.String(), nullable=False),
    sa.Column('role', sa.String(), nullable=False),
    sa.Column('failed_attempts', sa.Integer(), nullable=False),
    sa.Column('locked_until', sa.DateTime(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_users_username'), ['username'], unique=True)

    op.create_table('refresh_tokens',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('token_hash', sa.String(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('expires_at', sa.DateTime(), nullable=False),
    sa.Column('revoked_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('refresh_tokens', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_refresh_tokens_token_hash'), ['token_hash'], unique=True)
        batch_op.create_index(batch_op.f('ix_refresh_tokens_user_id'), ['user_id'], unique=False)


def downgrade():
    with op.batch_alter_table('refresh_tokens', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_refresh_tokens_user_id'))
        batch_op.drop_index(batch_op.f('ix_refresh_tokens_token_hash'))

    op.drop_table('refresh_tokens')
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_users_username'))

    op.drop_table('users')
    op.drop_table('servers')
    with op.batch_alter_table('metric_rollups', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_metric_rollups_server_id'))
        batch_op.drop_index(batch_op.f('ix_metric_rollups_bucket_start'))

    op.drop_table('metric_rollups')
    with op.batch_alter_table('metric_logs', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_metric_logs_server_id'))

    op.drop_table('metric_logs')
    with op.batch_alter_table('alert_events', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_alert_events_server_id'))

    op.drop_table('alert_events')