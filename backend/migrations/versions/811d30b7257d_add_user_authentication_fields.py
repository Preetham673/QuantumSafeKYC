"""Add user authentication fields

Revision ID: 811d30b7257d
Revises: e3047d02b14c
Create Date: 2026-08-28 10:43:47.266238

"""

from alembic import op
import sqlalchemy as sa


# --------------------------------------------------
# Revision identifiers
# --------------------------------------------------

revision = "811d30b7257d"
down_revision = "e3047d02b14c"
branch_labels = None
depends_on = None


# --------------------------------------------------
# Upgrade
# --------------------------------------------------

def upgrade():

    # Add password_hash as nullable because existing
    # users do not have passwords yet.
    with op.batch_alter_table("users", schema=None) as batch_op:

        batch_op.add_column(
            sa.Column(
                "password_hash",
                sa.String(length=255),
                nullable=True,
            )
        )

        # Existing users need a valid role.
        # server_default temporarily populates
        # existing rows with HOLDER.
        batch_op.add_column(
            sa.Column(
                "role",
                sa.String(length=30),
                nullable=False,
                server_default="HOLDER",
            )
        )

    # Remove the temporary database-level default.
    # The SQLAlchemy model still has:
    # default="HOLDER"
    with op.batch_alter_table("users", schema=None) as batch_op:

        batch_op.alter_column(
            "role",
            server_default=None,
        )


# --------------------------------------------------
# Downgrade
# --------------------------------------------------

def downgrade():

    with op.batch_alter_table("users", schema=None) as batch_op:

        batch_op.drop_column("role")

        batch_op.drop_column("password_hash")