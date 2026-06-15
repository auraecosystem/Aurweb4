"""add MaintainerSinceTS to PackageBase

Revision ID: 9f0e9f9c3f8a
Revises: 38e5b9982eea
Create Date: 2026-06-15 00:00:00.000000

"""

from alembic import op
from sqlalchemy.exc import OperationalError

from aurweb.models.package_base import PackageBase

# revision identifiers, used by Alembic.
revision = "9f0e9f9c3f8a"
down_revision = "f2701a76f4a9"
branch_labels = None
depends_on = None

table = PackageBase.__table__


def upgrade():
    try:
        op.add_column(table.name, table.c.MaintainerSinceTS)
    except OperationalError:
        print("column 'MaintainerSinceTS' already exists, skipping migration")


def downgrade():
    op.drop_column(table.name, "MaintainerSinceTS")
