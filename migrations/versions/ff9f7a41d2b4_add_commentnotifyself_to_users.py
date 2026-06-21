"""Add CommentNotifySelf to User

Revision ID: ff9f7a41d2b4
Revises: f2701a76f4a9
Create Date: 2026-04-11 00:00:00.000000

"""

from alembic import op
from sqlalchemy.exc import OperationalError

from aurweb.models.user import User

# revision identifiers, used by Alembic.
revision = "ff9f7a41d2b4"
down_revision = "f2701a76f4a9"
branch_labels = None
depends_on = None

table = User.__table__


def upgrade():
    try:
        op.add_column(table.name, table.c.CommentNotifySelf)
    except OperationalError:
        print(
            f"Column CommentNotifySelf already exists in '{table.name}',"
            f" skipping migration."
        )


def downgrade():
    op.drop_column(table.name, "CommentNotifySelf")
