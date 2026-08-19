"""États d'une opération et calcul des soldes.

**Auteur unique** de la question « cet état compte-t-il dans ce total ? ».

C'est le troisième état qui crée le risque : à chaque nouvel agrégat, on oublie de dire
ce qu'il fait des opérations à confirmer, et l'oubli est silencieux. La table
`CONTRIBUTIONS` ci-dessous est donc **exhaustive par construction** — il n'y a aucune
branche par défaut, et un test parcourt le produit cartésien {états} × {agrégats} pour
refuser toute combinaison non déclarée.
"""

from __future__ import annotations

import datetime as dt
from collections.abc import Iterable
from dataclasses import dataclass
from enum import StrEnum
from typing import Final

from mycounts.domain.montants import Cents


class EtatOperation(StrEnum):
    """Cycle de vie d'une opération.

    `prevue` → `a_confirmer` → `confirmee`. Une saisie manuelle naît directement
    `confirmee` : l'utilisateur vient de la constater.
    """

    PREVUE = "prevue"
    """Échéance future, pas encore matérialisée. Aucune trace en banque."""

    A_CONFIRMER = "a_confirmer"
    """Matérialisée automatiquement à sa date, mais aucun humain ne l'a vue passer.

    Sans import bancaire, c'est la seule chose qui distingue « le prélèvement était
    prévu » de « le prélèvement a eu lieu, au montant prévu ».
    """

    CONFIRMEE = "confirmee"
    """Constatée par une personne. C'est la seule qui entre dans le solde réel."""


class Agregat(StrEnum):
    SOLDE_REEL = "solde_reel"
    """Ce que la banque devrait afficher. Sert au rapprochement."""

    SOLDE_A_CONFIRMER = "solde_a_confirmer"
    """Ce qui est parti sans avoir été vérifié. Doit tendre vers zéro."""

    SOLDE_PROJETE = "solde_projete"
    """Ce qui est affiché par défaut : réel + à confirmer + échéances de la fenêtre."""

    DEPENSES_DE_PERIODE = "depenses_de_periode"
    """Base des plafonds par catégorie (lot 4)."""


class Signe(StrEnum):
    """Quels mouvements un agrégat retient.

    Deuxième dimension de la table, oubliée dans la première version : `depenses_de_periode`
    additionnait aussi les revenus et renvoyait un solde positif. Sur un plafond, il
    n'aurait jamais alerté — l'exact contraire de sa raison d'être. Voir ERREURS.md #013.
    """

    TOUS = "tous"
    SORTIES = "sorties"
    """Montants strictement négatifs."""

    ENTREES = "entrees"
    """Montants strictement positifs."""


class Borne(StrEnum):
    """Jusqu'où un agrégat regarde dans le temps."""

    AUJOURD_HUI = "aujourd_hui"
    """N'inclut que les opérations déjà datées d'aujourd'hui ou avant.

    Réservée au solde réel, qui doit correspondre à ce que la banque affiche
    aujourd'hui — c'est la grandeur qui sert au rapprochement.
    """

    FIN_DE_FENETRE = "fin_de_fenetre"
    """Inclut aussi ce qui est daté jusqu'à la fin de la période budgétaire."""


# Table exhaustive. `None` signifie explicitement « ne contribue pas » — c'est une
# déclaration, pas un oubli. Ajouter un état ou un agrégat sans compléter cette table
# fait échouer `test_la_table_est_exhaustive`.
CONTRIBUTIONS: Final[dict[Agregat, dict[EtatOperation, Borne | None]]] = {
    Agregat.SOLDE_REEL: {
        EtatOperation.CONFIRMEE: Borne.AUJOURD_HUI,
        EtatOperation.A_CONFIRMER: None,
        EtatOperation.PREVUE: None,
    },
    Agregat.SOLDE_A_CONFIRMER: {
        EtatOperation.CONFIRMEE: None,
        EtatOperation.A_CONFIRMER: Borne.AUJOURD_HUI,
        EtatOperation.PREVUE: None,
    },
    Agregat.SOLDE_PROJETE: {
        # Tout ce qui est daté dans la fenêtre compte, quel que soit l'état. Une première
        # version bornait les opérations confirmées à aujourd'hui : une dépense constatée
        # et datée de demain disparaissait alors du réel ET du projeté — de l'argent
        # invisible sur tous les écrans jusqu'à sa date. Voir ERREURS.md #010.
        EtatOperation.CONFIRMEE: Borne.FIN_DE_FENETRE,
        EtatOperation.A_CONFIRMER: Borne.FIN_DE_FENETRE,
        EtatOperation.PREVUE: Borne.FIN_DE_FENETRE,
    },
    Agregat.DEPENSES_DE_PERIODE: {
        # Une dépense constatée appartient à sa période, même datée de quelques jours en
        # avant. Une échéance seulement PRÉVUE, non : un plafond qui compterait ce qui
        # n'a pas encore eu lieu serait dépassé dès le premier jour de la période.
        EtatOperation.CONFIRMEE: Borne.FIN_DE_FENETRE,
        EtatOperation.A_CONFIRMER: Borne.FIN_DE_FENETRE,
        EtatOperation.PREVUE: None,
    },
}


# Signe retenu par agrégat. Exhaustive comme CONTRIBUTIONS, et vérifiée par un test :
# un agrégat ajouté sans ligne ici lèverait un KeyError plutôt que de sommer n'importe quoi.
SIGNE_RETENU: Final[dict[Agregat, Signe]] = {
    Agregat.SOLDE_REEL: Signe.TOUS,
    Agregat.SOLDE_A_CONFIRMER: Signe.TOUS,
    Agregat.SOLDE_PROJETE: Signe.TOUS,
    # « Dépenses » veut dire dépenses : une paie encaissée dans la période ne réduit pas
    # la consommation d'un plafond de courses.
    Agregat.DEPENSES_DE_PERIODE: Signe.SORTIES,
}


# Troisième dimension de la table : les soldes d'ouverture comptent dans les soldes mais
# pas dans les dépenses. Un découvert de départ n'est pas une dépense du mois — l'y
# inclure ferait sauter tous les plafonds dès la création du compte.
INCLUT_OUVERTURES: Final[dict[Agregat, bool]] = {
    Agregat.SOLDE_REEL: True,
    Agregat.SOLDE_A_CONFIRMER: True,
    Agregat.SOLDE_PROJETE: True,
    Agregat.DEPENSES_DE_PERIODE: False,
}


@dataclass(frozen=True)
class OperationCalcul:
    """Vue minimale d'une opération pour les calculs.

    Volontairement détachée du modèle SQLAlchemy : le domaine se teste sans base, et une
    colonne ajoutée en base ne change rien ici.
    """

    montant: Cents
    date_operation: dt.date
    etat: EtatOperation
    est_ouverture: bool = False


def contribue(agregat: Agregat, etat: EtatOperation) -> Borne | None:
    """Borne temporelle avec laquelle `etat` entre dans `agregat`, ou None.

    Lève `KeyError` si la combinaison n'est pas déclarée : mieux vaut un plantage
    immédiat qu'un total silencieusement faux.
    """
    return CONTRIBUTIONS[agregat][etat]


def calculer(
    agregat: Agregat,
    operations: Iterable[OperationCalcul],
    *,
    aujourd_hui: dt.date,
    fin_de_fenetre: dt.date,
) -> Cents:
    """Somme des opérations qui contribuent à `agregat`, en centimes.

    `fin_de_fenetre` est la fin de la période budgétaire courante. Elle n'est utilisée
    que par les agrégats dont la table dit qu'ils regardent au-delà d'aujourd'hui.
    """
    if fin_de_fenetre < aujourd_hui:
        raise ValueError("La fin de fenêtre ne peut pas précéder le jour courant.")

    signe = SIGNE_RETENU[agregat]
    inclut_ouvertures = INCLUT_OUVERTURES[agregat]
    total = 0
    for operation in operations:
        borne = contribue(agregat, operation.etat)
        if borne is None:
            continue
        if operation.est_ouverture and not inclut_ouvertures:
            continue
        if signe is Signe.SORTIES and operation.montant >= 0:
            continue
        if signe is Signe.ENTREES and operation.montant <= 0:
            continue
        limite = aujourd_hui if borne is Borne.AUJOURD_HUI else fin_de_fenetre
        if operation.date_operation <= limite:
            total += operation.montant
    return Cents(total)
