"""add timeframe column  to OHLC and Predictions models

Revision ID: ff12241c533b
Revises: 9587a97c3eae
Create Date: 2025-09-10 16:28:25.221638

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ff12241c533b'
down_revision: Union[str, Sequence[str], None] = '9587a97c3eae'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    # add 'timeframe' column to OHLC
    op.add_column('ohlc', sa.Column('timeframe', sa.String(), nullable=False, server_default='1d'))
    op.create_index('ix_ohlc_timeframe', 'ohlc', ['timeframe'])

    # add 'timeframe' column to Predictions
    op.add_column('predictions', sa.Column('timeframe', sa.String(), nullable=False, server_default='1d'))
    op.create_index('ix_predictions_timeframe', 'predictions', ['timeframe'])


def downgrade():
    # remove columns in downgrade
    op.drop_index('ix_ohlc_timeframe', table_name='ohlc')
    op.drop_column('ohlc', 'timeframe')

    op.drop_index('ix_predictions_timeframe', table_name='predictions')
    op.drop_column('predictions', 'timeframe')
