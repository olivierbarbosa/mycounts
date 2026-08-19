"""Tests des montants.

Les deux témoins de fin de fichier sont les seuls qui échouent réellement si un `float`
réapparaît dans la conversion. Ils ont été calibrés contre les implémentations fautives,
pas supposés : voir ERREURS.md #002.
"""

from __future__ import annotations

import pytest
from mycounts.domain.montants import MontantInvalide, parse_montant


@pytest.mark.parametrize(
    ("saisie", "attendu"),
    [
        ("0", 0),
        ("12", 1200),
        ("12,5", 1250),
        ("12,50", 1250),
        ("12.50", 1250),
        ("1 234,56", 123456),
        ("1 234,56", 123456),  # espace insécable, tel que collé depuis un relevé
        ("12,50 €", 1250),
        ("-45,90", -4590),
        ("+45,90", 4590),
        ("0,01", 1),
        ("0,10", 10),
    ],
)
def test_saisies_acceptees(saisie: str, attendu: int) -> None:
    assert parse_montant(saisie) == attendu


@pytest.mark.parametrize(
    "saisie",
    [
        "",
        "   ",
        "abc",
        "12,505",  # trois décimales : refusé, jamais arrondi en silence
        "12,,5",
        "12-5",
        "1e3",
        "--5",
        "12,5,5",
    ],
)
def test_saisies_refusees(saisie: str) -> None:
    with pytest.raises(MontantInvalide):
        parse_montant(saisie)


# --- Témoins anti-flottant -------------------------------------------------------
#
# Ces deux tests ont été calibrés en implémentant réellement les versions fautives et en
# mesurant lesquelles ils rejettent. Un test « 0,10 + 0,20 == 0,30 » ne convient PAS :
# les deux implémentations fautives ci-dessous le passent (mesuré, ERREURS.md #002).


def test_temoin_balayage_exhaustif() -> None:
    """Tout montant de 0,00 à 199,99 se convertit exactement.

    Rejette `int(float(x) * 100)` : cette implémentation se trompe sur 1 145 des 20 000
    montants balayés (0,29 · 0,57 · 1,13 · 2,01 …), parce que 0.29 * 100 vaut
    28.999999999999996 en binaire et que la troncature emporte le centime.
    """
    for euros in range(200):
        for centimes in range(100):
            assert parse_montant(f"{euros},{centimes:02d}") == euros * 100 + centimes


def test_temoin_grand_montant() -> None:
    """Un montant au-delà de 2^53 centimes reste exact.

    Rejette `round(float(x) * 100)`, qui survit au balayage ci-dessus mais casse ici :
    au-delà de 2^53 (9 007 199 254 740 992) un entier n'est plus représentable
    exactement en float64, et le résultat perd un centime — 9999999999999998 au lieu de
    9999999999999999.

    Ce montant est irréaliste pour un budget de foyer, et c'est assumé : le rôle de ce
    test n'est pas de couvrir un cas d'usage mais de fermer la porte à la seule
    implémentation fautive que le test précédent laisse passer.
    """
    assert parse_montant("99999999999999,99") == 9999999999999999
