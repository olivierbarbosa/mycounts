"""Limiter les échecs de connexion par identifiant et origine pseudonymisés.

Revision ID: ab703f49d821
Revises: f2c48b6a91de
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "ab703f49d821"
down_revision = "f2c48b6a91de"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "tentative_connexion",
        sa.Column("empreinte", sa.String(length=64), nullable=False),
        sa.Column("portee", sa.String(length=16), nullable=False),
        sa.Column("fenetre_debut", sa.DateTime(timezone=True), nullable=False),
        sa.Column("echecs", sa.Integer(), nullable=False),
        sa.CheckConstraint("echecs > 0", name="ck_tentative_connexion_echecs_positifs"),
        sa.PrimaryKeyConstraint("empreinte", "portee", "fenetre_debut"),
    )
    op.create_index(
        "ix_tentative_connexion_fenetre", "tentative_connexion", ["fenetre_debut"]
    )


def downgrade() -> None:
    op.drop_index("ix_tentative_connexion_fenetre", table_name="tentative_connexion")
    op.drop_table("tentative_connexion")
