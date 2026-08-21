"""Avatar de profil, dans sa propre table.

Une table plutôt qu'une colonne sur `utilisateur` : une image pèse mille fois la ligne qui
la porterait, et chaque lecture de session la traînerait pour un affichage qui n'en a
besoin qu'une fois.

Revision ID: c3f81a5d47e9
Revises: a1c7e4b90f22
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "c3f81a5d47e9"
down_revision = "a1c7e4b90f22"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "avatar",
        # Clé primaire ET étrangère : une personne a au plus un avatar, et c'est la base
        # qui le garantit. Le dire dans le code seul laisserait une seconde ligne
        # apparaître le jour d'un envoi concurrent, et la lecture en choisirait une au
        # hasard.
        sa.Column(
            "utilisateur_id",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("utilisateur.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("contenu", sa.LargeBinary(), nullable=False),
        sa.Column("type_mime", sa.String(length=40), nullable=False),
        sa.Column(
            "modifie_le",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_table("avatar")
