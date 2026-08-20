"""Correspondances d'import : ce que le foyer a retenu d'un rangement précédent.

Un export bancaire réel de 198 opérations arrive sans aucune catégorie du foyer. Sans
mémoire d'un import à l'autre, il faudrait ranger 198 lignes à la main à chaque fois — et
personne ne le fait deux fois.

L'unicité par (foyer, genre, valeur) n'est pas une précaution de forme : sans elle, deux
apprentissages contradictoires cohabiteraient et le rangement dépendrait de l'ordre des
lignes en base.

Revision ID: 0ff4a2a9d1d9
Revises: 9b2bb0cecd19
Create Date: 2026-08-20 20:49:34.505282
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = '0ff4a2a9d1d9'
down_revision: str | None = '9b2bb0cecd19'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table('correspondance_import',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('foyer_id', sa.UUID(), nullable=False),
    sa.Column('genre', sa.String(length=24), nullable=False),
    sa.Column('valeur', sa.String(length=140), nullable=False),
    sa.Column('categorie_id', sa.UUID(), nullable=False),
    sa.Column('cree_le', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['categorie_id'], ['categorie.id'], name=op.f('fk_correspondance_import_categorie_id_categorie'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['foyer_id'], ['foyer.id'], name=op.f('fk_correspondance_import_foyer_id_foyer'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_correspondance_import')),
    sa.UniqueConstraint('foyer_id', 'genre', 'valeur', name='uq_correspondance_import_par_foyer')
    )


def downgrade() -> None:
    op.drop_table('correspondance_import')
