"""Représentation des montants monétaires.

Auteur **unique** de la règle « un montant est un entier de centimes ». Aucun autre
module ne convertit une saisie utilisateur en montant, et aucun n'utilise `float` :
`0.1 + 0.2` reste le bug le plus cher de l'informatique de gestion.
"""

from __future__ import annotations

import re
from typing import Final, NewType

Cents = NewType("Cents", int)
"""Montant en centimes d'euro, signé.

Négatif = sortie d'argent, positif = entrée. Stocké en `BIGINT`. Le `NewType` existe
pour que mypy refuse qu'un entier quelconque (un identifiant, un nombre de jours) se
retrouve là où un montant est attendu.
"""

DEVISE: Final = "EUR"
"""Devise unique du projet.

Le multi-devises est hors périmètre. S'il arrive un jour, le taux devra être stocké
**avec** l'opération : recalculer un historique au taux du jour réécrit le passé.
"""

_ESPACES: Final = re.compile(r"[\s  ]")
_SAISIE: Final = re.compile(
    r"^(?P<signe>[-+])?(?P<entier>\d{1,15})(?:[.,](?P<decimales>\d{1,2}))?$"
)


class MontantInvalide(ValueError):
    """Une saisie qui ne décrit pas un montant exploitable."""


def parse_montant(saisie: str) -> Cents:
    """Convertit une saisie utilisateur en centimes, sans jamais passer par un flottant.

    Accepte la virgule et le point comme séparateur décimal, les espaces de milliers
    (y compris insécables) et un symbole `€` optionnel.

    Refuse — plutôt que d'arrondir en silence — toute saisie à plus de deux décimales :
    un arrondi que l'utilisateur n'a pas demandé est un écart qu'il ne pourra pas
    expliquer. C'est un refus délibéré, pas une limitation.

    >>> parse_montant("12,50")
    1250
    >>> parse_montant("-1 234.5 €")
    -123450
    """
    texte = _ESPACES.sub("", saisie).replace("€", "")
    if not texte:
        raise MontantInvalide("Montant vide.")

    correspondance = _SAISIE.fullmatch(texte)
    if correspondance is None:
        raise MontantInvalide(
            f"Montant illisible : {saisie!r}. Attendu par exemple « 12,50 » ou « -1 234.50 »."
        )

    decimales = correspondance["decimales"] or ""
    centimes = int(correspondance["entier"]) * 100 + int(decimales.ljust(2, "0") or "0")
    if correspondance["signe"] == "-":
        centimes = -centimes
    return Cents(centimes)
