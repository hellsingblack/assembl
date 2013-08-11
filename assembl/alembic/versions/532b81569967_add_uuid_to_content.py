"""add uuid to Content

Revision ID: 532b81569967
Revises: 2e1a77e61fb3
Create Date: 2013-08-09 19:52:42.532290

"""

# revision identifiers, used by Alembic.
revision = '532b81569967'
down_revision = '2e1a77e61fb3'

import uuid
from alembic import context, op
import sqlalchemy as sa
import transaction


from assembl import models as m
from assembl.lib import config
from assembl.lib.types import UUID

db = m.DBSession


def upgrade(pyramid_env):
    with context.begin_transaction():
        op.add_column('content', sa.Column(
            'uuid',
            UUID,
            default=uuid.uuid4))
        op.add_column(
            'mailbox',
            sa.Column(
                'mailing_address',
                sa.String(255),
                nullable=True))

    with transaction.manager:
        pass


def downgrade(pyramid_env):
    with context.begin_transaction():
        op.drop_column('content', 'uuid')
        op.drop_column('mailbox', 'mailing_list_address')
