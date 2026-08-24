"""Contraindre les portées des compteurs d'authentification.

Revision ID: c74b81e2a603
Revises: ab703f49d821
"""

from __future__ import annotations

from alembic import op

revision = "c74b81e2a603"
down_revision = "ab703f49d821"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_check_constraint(
        "ck_tentative_connexion_portee",
        "tentative_connexion",
        "portee in ('identifiant', 'couple', 'origine', 'action')",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_tentative_connexion_portee",
        "tentative_connexion",
        type_="check",
    )
