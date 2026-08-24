"""Interdire le rejeu d'un code TOTP dans sa fenêtre de validité.

Revision ID: f2c48b6a91de
Revises: d5a90e3c71b8
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "f2c48b6a91de"
down_revision = "d5a90e3c71b8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "utilisateur", sa.Column("dernier_compteur_totp", sa.BigInteger(), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("utilisateur", "dernier_compteur_totp")
