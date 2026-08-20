"""Réglages des enveloppes : usage, rollover, priorité, contribution.

Ajoute ce qui manquait au lot E1 pour que la préparation mensuelle puisse être écrite.
Le point qui commande le reste est `rollover` : ce que devient le solde d'une enveloppe
quand une nouvelle période s'ouvre. Sans réponse à cette question, `place = max(0, cible −
actuel)` n'a pas de sens — il suppose déjà de savoir ce que vaut « actuel » au premier jour
du mois.

Les quatre colonnes portent un `server_default` non par commodité mais par nécessité :
elles arrivent sur une table qui contient déjà des lignes, et `rollover` vaut `report`
pour elles — le seul mode qui ne fasse disparaître aucun argent réservé chez quelqu'un qui
n'a rien demandé.

Revision ID: efe3ce18d323
Revises: 9af113325c74
Create Date: 2026-08-20 19:00:38.900430
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = 'efe3ce18d323'
down_revision: str | None = '9af113325c74'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column('enveloppe', sa.Column('usage', sa.String(length=16), server_default='fonctionnement', nullable=False))
    op.add_column('enveloppe', sa.Column('rollover', sa.String(length=16), server_default='report', nullable=False))
    op.add_column('enveloppe', sa.Column('priorite', sa.Integer(), server_default='0', nullable=False))
    op.add_column('enveloppe', sa.Column('contribution_mensuelle_centimes', sa.BigInteger(), nullable=True))
    # Une contribution est une somme qu'on PRÉVOIT de mettre : négative, elle produirait
    # une recommandation de retirer de l'argent à chaque période, sans que rien ne le dise.
    op.create_check_constraint(op.f('ck_enveloppe_ck_enveloppe_contribution_positive'), 'enveloppe', 'contribution_mensuelle_centimes is null or contribution_mensuelle_centimes > 0')


def downgrade() -> None:
    op.drop_constraint(op.f('ck_enveloppe_ck_enveloppe_contribution_positive'), 'enveloppe', type_='check')
    op.drop_column('enveloppe', 'contribution_mensuelle_centimes')
    op.drop_column('enveloppe', 'priorite')
    op.drop_column('enveloppe', 'rollover')
    op.drop_column('enveloppe', 'usage')
