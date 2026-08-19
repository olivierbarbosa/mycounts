"""Nature d'un compte.

**Auteur unique** de la question « ce compte fait-il partie de l'argent du quotidien ? ».

La distinction n'est pas décorative. Mélanger un livret au compte courant fait croire à
une aisance qui n'existe pas : le solde de l'accueil annoncerait 4 000 € alors que 3 500
sont mis de côté, et la décision de dépenser se prendrait sur un chiffre faux.
"""

from __future__ import annotations

from enum import StrEnum


class TypeCompte(StrEnum):
    COURANT = "courant"
    """Argent du quotidien. Entre dans les soldes affichés sur l'accueil."""

    EPARGNE = "epargne"
    """Argent mis de côté. Compté à part, jamais dans le solde du quotidien.

    Un compte d'épargne reste un compte du foyer : il a des opérations, un solde, et il
    s'alimente par virement. Ce qui change est l'écran qui le totalise.
    """
