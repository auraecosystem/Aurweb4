"""add CoMaintainerSinceTS to PackageComaintainers

Revision ID: 4f3d2a1b9c8e
Revises: 9f0e9f9c3f8a
Create Date: 2026-06-15 00:00:01.000000

"""

from alembic import op
from sqlalchemy.exc import OperationalError

from aurweb.models.package_comaintainer import PackageComaintainer

# revision identifiers, used by Alembic.
revision = "4f3d2a1b9c8e"
down_revision = "9f0e9f9c3f8a"
branch_labels = None
depends_on = None

table = PackageComaintainer.__table__


def upgrade():
    try:
        op.add_column(table.name, table.c.CoMaintainerSinceTS)
    except OperationalError:
        print("column 'CoMaintainerSinceTS' already exists, skipping migration")


def downgrade():
    op.drop_column(table.name, "CoMaintainerSinceTS")
