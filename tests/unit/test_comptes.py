"""Catalogue des produits : trois natures, et le LEP du bon côté.

Le test central est `un PEA est un placement, un LEP une épargne disponible` : c'est la
mesure qui peut rendre la réponse inverse. Avant le lot V1-FIN-A1, les deux se comptaient
pareil, et les enveloppes découpaient un PEA comme un livret.
"""

from __future__ import annotations

import pytest
from mycounts.domain.comptes import CATALOGUE, PAR_CLE, TypeCompte, produit

PLACEMENTS = ("pea", "pea_pme", "pee", "compte_titres", "assurance_vie", "per", "autre_placement")
EPARGNES_DISPONIBLES = ("livret_a", "ldds", "lep", "livret_jeune", "pel", "cel", "autre_epargne")


def test_un_pea_est_un_placement_un_lep_une_epargne_disponible() -> None:
    assert produit("pea").type_compte == TypeCompte.PLACEMENT
    assert produit("lep").type_compte == TypeCompte.EPARGNE


@pytest.mark.parametrize("cle", PLACEMENTS)
def test_les_placements_sont_hors_reserve(cle: str) -> None:
    assert produit(cle).type_compte == TypeCompte.PLACEMENT


@pytest.mark.parametrize("cle", EPARGNES_DISPONIBLES)
def test_les_livrets_restent_une_epargne_disponible(cle: str) -> None:
    assert produit(cle).type_compte == TypeCompte.EPARGNE


def test_chaque_nature_a_un_produit_autre() -> None:
    """« Autre » laisse choisir le comportement à la main : il en faut un par nature, sans
    quoi un produit absent du catalogue n'aurait aucun moyen d'être un placement."""
    natures_des_autres = {
        p.type_compte for p in CATALOGUE if p.cle.startswith("autre_")
    }
    assert natures_des_autres == set(TypeCompte)


def test_les_cles_sont_uniques() -> None:
    assert len(PAR_CLE) == len(CATALOGUE)


def test_un_produit_inconnu_leve() -> None:
    with pytest.raises(ValueError, match="inconnu"):
        produit("livret_martien")
