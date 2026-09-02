"""placements hors reserve

Revision ID: 7b3e9c2a5d41
Revises: e18c7d41a2b0
Create Date: 2026-09-02 14:10:00.000000

Troisième nature de compte, `placement` : PEA, PEA-PME, PEE, compte-titres, assurance vie
et PER sortent de la réserve d'épargne disponible. Leur solde par compte ne bouge pas d'un
centime ; seule la colonne que les totaux lisent change.

Le reclassement est EXPLICITE, par clé de produit, et recopie la liste du catalogue
(`domain/comptes.py`) au jour de cette migration. Une migration ne lit jamais le domaine
vivant : le catalogue évoluera, et cette migration doit rejouer demain exactement ce
qu'elle a fait aujourd'hui.

Le retour arrière remet ces comptes en `epargne`, où ils étaient. Deux produits nés avec
ce lot (`pee`, `autre_placement`) n'existent pas dans l'ancien catalogue, dont la lecture
LÈVE sur une clé inconnue : ils retombent sur `autre_epargne`, le seul produit de l'ancien
catalogue qui dise vrai sur leur comportement d'alors. Le libellé se perd, pas l'argent.
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = '7b3e9c2a5d41'
down_revision: str | None = 'e18c7d41a2b0'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

PRODUITS_PLACES = ("pea", "pea_pme", "pee", "compte_titres", "assurance_vie", "per", "autre_placement")
"""Clés de produit reclassées. Figées ici, volontairement — voir l'en-tête."""

PRODUITS_INCONNUS_AVANT = ("pee", "autre_placement")
"""Produits nés avec ce lot, sans équivalent dans le catalogue précédent."""


def _liste(cles: Sequence[str]) -> str:
    return ", ".join(f"'{cle}'" for cle in cles)


def upgrade() -> None:
    # Seuls les comptes que l'ancien catalogue classait « épargne » changent : un PEA
    # marqué autrement par un script ancien n'est pas notre affaire ici, et le toucher
    # serait un second reclassement que personne n'a décrit.
    op.execute(
        "update compte set type_compte = 'placement' "
        f"where produit in ({_liste(PRODUITS_PLACES)}) and type_compte = 'epargne'"
    )
    op.create_check_constraint(
        'ck_compte_type_connu',
        'compte',
        "type_compte in ('courant', 'epargne', 'placement')",
    )


def downgrade() -> None:
    op.drop_constraint('ck_compte_type_connu', 'compte', type_='check')
    op.execute(
        f"update compte set produit = 'autre_epargne' where produit in ({_liste(PRODUITS_INCONNUS_AVANT)})"
    )
    # Tous les placements, pas seulement ceux de la liste : après retour arrière, la
    # colonne n'admet plus que deux valeurs, et une troisième laissée là serait invisible
    # de tous les totaux.
    op.execute("update compte set type_compte = 'epargne' where type_compte = 'placement'")
