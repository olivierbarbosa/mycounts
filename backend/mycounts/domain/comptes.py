"""Nature d'un compte.

**Auteur unique** de la question « ce compte fait-il partie de l'argent du quotidien ? ».

La distinction n'est pas décorative. Mélanger un livret au compte courant fait croire à
une aisance qui n'existe pas : le solde de l'accueil annoncerait 4 000 € alors que 3 500
sont mis de côté, et la décision de dépenser se prendrait sur un chiffre faux.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Final


class TypeCompte(StrEnum):
    COURANT = "courant"
    """Argent du quotidien. Entre dans les soldes affichés sur l'accueil."""

    EPARGNE = "epargne"
    """Argent mis de côté. Compté à part, jamais dans le solde du quotidien.

    Un compte d'épargne reste un compte du foyer : il a des opérations, un solde, et il
    s'alimente par virement. Ce qui change est l'écran qui le totalise.
    """


@dataclass(frozen=True)
class ProduitBancaire:
    """Un produit tel qu'il existe chez les banques françaises."""

    cle: str
    libelle: str
    type_compte: TypeCompte
    """Comportement du produit vis-à-vis des calculs.

    C'est la SEULE chose que les agrégats lisent. Le produit, lui, ne sert qu'à nommer :
    un Livret A et un PEL se comptent exactement pareil, et si demain un produit devait se
    compter autrement, ce serait par cette colonne — jamais par un test sur son nom.
    """


# Catalogue des produits courants en France.
#
# Il est FERMÉ et vit ici, dans le domaine : c'est lui qui décide qu'un PEA ne compte pas
# dans le solde du quotidien. Le déporter dans l'interface ferait de l'écran l'auteur
# d'une règle de calcul.
#
# Ce qu'il ne prétend PAS être : exhaustif. Les produits rares, les comptes professionnels
# et les livrets maison des banques en ligne n'y sont pas — d'où « Autre », qui laisse
# choisir le comportement à la main plutôt que de forcer un nom faux.
CATALOGUE: Final[tuple[ProduitBancaire, ...]] = (
    ProduitBancaire("compte_courant", "Compte courant", TypeCompte.COURANT),
    ProduitBancaire("compte_joint", "Compte joint", TypeCompte.COURANT),
    ProduitBancaire("livret_a", "Livret A", TypeCompte.EPARGNE),
    ProduitBancaire("ldds", "LDDS — développement durable", TypeCompte.EPARGNE),
    ProduitBancaire("lep", "LEP — épargne populaire", TypeCompte.EPARGNE),
    ProduitBancaire("livret_jeune", "Livret Jeune", TypeCompte.EPARGNE),
    ProduitBancaire("livret_bancaire", "Livret bancaire fiscalisé", TypeCompte.EPARGNE),
    ProduitBancaire("pel", "PEL — épargne logement", TypeCompte.EPARGNE),
    ProduitBancaire("cel", "CEL — compte épargne logement", TypeCompte.EPARGNE),
    ProduitBancaire("compte_a_terme", "Compte à terme", TypeCompte.EPARGNE),
    ProduitBancaire("pea", "PEA — plan d'épargne en actions", TypeCompte.EPARGNE),
    ProduitBancaire("pea_pme", "PEA-PME", TypeCompte.EPARGNE),
    ProduitBancaire("compte_titres", "Compte-titres ordinaire", TypeCompte.EPARGNE),
    ProduitBancaire("assurance_vie", "Assurance vie", TypeCompte.EPARGNE),
    ProduitBancaire("per", "PER — plan d'épargne retraite", TypeCompte.EPARGNE),
    ProduitBancaire("especes", "Espèces", TypeCompte.COURANT),
    # Deux entrées et non une avec un réglage à part : le comportement se DÉDUIT du
    # produit, toujours. Laisser le client l'envoyer en plus créerait deux façons de dire
    # la même chose, qui finiraient par se contredire.
    ProduitBancaire("autre_courant", "Autre — argent du quotidien", TypeCompte.COURANT),
    ProduitBancaire("autre_epargne", "Autre — mis de côté", TypeCompte.EPARGNE),
)

PAR_CLE: Final[dict[str, ProduitBancaire]] = {produit.cle: produit for produit in CATALOGUE}


def produit(cle: str) -> ProduitBancaire:
    """Produit du catalogue, ou lève.

    Lever plutôt que retomber sur « Autre » : une clé inconnue vient d'une donnée corrompue
    ou d'un catalogue amputé, et deviner alors le comportement d'un compte reviendrait à
    déplacer de l'argent d'une colonne à l'autre sans que personne ne le demande.
    """
    if cle not in PAR_CLE:
        raise ValueError(f"Produit bancaire inconnu : {cle!r}.")
    return PAR_CLE[cle]
