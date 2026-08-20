"""Clé d'import sur les opérations.

Permet de reconnaître une ligne de relevé déjà importée, et donc de réimporter un mois qui
chevauche le précédent sans dupliquer l'argent. `NULL` pour les opérations saisies à la
main, qui ne viennent d'aucun fichier.

La colonne est indexée : l'import compare chaque ligne du fichier à l'historique entier,
et un import de deux cents lignes ferait sinon deux cents balayages de table.

Pourquoi une clé COMPOSÉE et non la référence bancaire, qu'un relevé fournit pourtant :
mesuré sur un export réel de 198 opérations, elle est vide 31 fois et partagée par deux
achats différents du même jour. Le détail est dans `domain/import_releve.py`.

Revision ID: 9b2bb0cecd19
Revises: efe3ce18d323
Create Date: 2026-08-20 20:22:51.288822
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = '9b2bb0cecd19'
down_revision: str | None = 'efe3ce18d323'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column('operation', sa.Column('cle_import', sa.String(length=200), nullable=True))
    op.create_index(op.f('ix_operation_cle_import'), 'operation', ['cle_import'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_operation_cle_import'), table_name='operation')
    op.drop_column('operation', 'cle_import')
