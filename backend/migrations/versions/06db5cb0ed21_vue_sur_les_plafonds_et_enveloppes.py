"""La vue rejoint la clé des plafonds et des enveloppes.

Catégories communes aux deux périmètres, budgets SÉPARÉS : décidé par Olivier le 21 août
2026. Le budget courses du foyer n'est pas le sien, et les deux doivent pouvoir coexister
sur la même catégorie.

Les lignes existantes deviennent PERSONNELLES. C'est le seul choix sûr : elles ont toutes
été posées avant que la vue foyer n'existe, et les attribuer au foyer exposerait à tous les
membres des budgets que chacun avait fixés pour lui.

Un index partiel s'ajoute pour la vue foyer, que la contrainte d'unicité ordinaire ne peut
pas exprimer : un plafond de foyer appartient au FOYER et non à qui l'a posé, si bien que
deux membres qui en fixent un sur la même catégorie parlent du même. L'unicité doit donc y
ignorer `utilisateur_id`.

Revision ID: 06db5cb0ed21
Revises: 0ff4a2a9d1d9
Create Date: 2026-08-21 02:07:44.166430
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = '06db5cb0ed21'
down_revision: str | None = '0ff4a2a9d1d9'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column('enveloppe', sa.Column('vue', sa.String(length=16), server_default='personnelle', nullable=False))
    op.drop_constraint(op.f('uq_enveloppe_nom_par_foyer'), 'enveloppe', type_='unique')
    op.create_unique_constraint('uq_enveloppe_nom_par_foyer', 'enveloppe', ['foyer_id', 'nom', 'vue'])
    op.add_column('plafond', sa.Column('vue', sa.String(length=16), server_default='personnelle', nullable=False))
    op.drop_constraint(op.f('uq_plafond_par_categorie_et_personne'), 'plafond', type_='unique')
    op.create_unique_constraint('uq_plafond_par_categorie_et_personne', 'plafond', ['utilisateur_id', 'categorie_id', 'vue'])

    # Un plafond de foyer est unique PAR CATÉGORIE, qui que soit son auteur. Sans cet
    # index, deux membres pourraient en poser chacun un sur « Courses » et l'écran en
    # afficherait deux, sans que rien ne dise lequel fait foi.
    op.create_index(
        "uq_plafond_de_foyer_par_categorie",
        "plafond",
        ["categorie_id"],
        unique=True,
        postgresql_where=sa.text("vue = 'foyer'"),
    )

    # Même raison pour une enveloppe de foyer : son nom l'identifie dans le foyer entier.
    op.create_index(
        "uq_enveloppe_de_foyer_par_nom",
        "enveloppe",
        ["foyer_id", "nom"],
        unique=True,
        postgresql_where=sa.text("vue = 'foyer'"),
    )


def downgrade() -> None:
    op.drop_constraint('uq_plafond_par_categorie_et_personne', 'plafond', type_='unique')
    op.create_unique_constraint(op.f('uq_plafond_par_categorie_et_personne'), 'plafond', ['utilisateur_id', 'categorie_id'], postgresql_nulls_not_distinct=False)
    op.drop_column('plafond', 'vue')
    op.drop_constraint('uq_enveloppe_nom_par_foyer', 'enveloppe', type_='unique')
    op.create_unique_constraint(op.f('uq_enveloppe_nom_par_foyer'), 'enveloppe', ['foyer_id', 'nom'], postgresql_nulls_not_distinct=False)
    op.drop_column('enveloppe', 'vue')
