"""Propriétaire du foyer

Qui détient le droit de gérer les membres et de détruire le foyer. Jusqu'ici personne :
l'écran parlait d'« admin » là où le modèle n'avait aucun rôle, si bien que la suppression
d'un espace joint n'avait pas de titulaire possible.

Le rattrapage donne le foyer à son membre le PLUS ANCIEN. C'est celui qu'a créé
`scripts/creer_premier_compte.py` — les suivants sont entrés par invitation, donc à sa
demande. Un foyer qui sortirait de cette migration sans propriétaire serait un foyer que
plus personne ne peut administrer : le backfill est écrit pour n'en laisser aucun.

Revision ID: a1c7e4b90f22
Revises: 06db5cb0ed21
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "a1c7e4b90f22"
down_revision = "06db5cb0ed21"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "utilisateur",
        sa.Column("est_proprietaire", sa.Boolean(), nullable=False, server_default="false"),
    )

    # Le membre le plus ancien de CHAQUE foyer, y compris ceux à plusieurs membres.
    # `distinct on` est la forme PostgreSQL du « premier de chaque groupe » ; un
    # `min(cree_le)` obligerait à re-joindre pour retrouver l'identifiant, et deux comptes
    # créés dans la même transaction partagent la même `cree_le`. L'identifiant départage.
    op.execute(
        sa.text(
            """
            update utilisateur
               set est_proprietaire = true
             where id in (
                   select distinct on (foyer_id) id
                     from utilisateur
                    order by foyer_id, cree_le, id
                   )
            """
        )
    )

    op.create_index(
        "uq_un_seul_proprietaire_par_foyer",
        "utilisateur",
        ["foyer_id"],
        unique=True,
        postgresql_where=sa.text("est_proprietaire"),
    )


def downgrade() -> None:
    op.drop_index("uq_un_seul_proprietaire_par_foyer", table_name="utilisateur")
    op.drop_column("utilisateur", "est_proprietaire")
