"""Statistiques de dépense, et repérage des motifs qui échappent à l'attention.

**Ce que ce module fait.** Il répond à « où va mon argent », par catégorie et par
commerçant, sur la période et comparé à la précédente. Puis il signale un petit nombre de
MOTIFS chiffrés — un poste qui a beaucoup augmenté, des petites dépenses répétées au même
endroit, des abonnements dont le coût annuel se voit mal quand on le paie par douzièmes.

**Ce qu'il ne fait PAS, et c'est une décision, pas une limite technique.**

Il ne dit jamais qu'une dépense est *inutile*. Il n'en sait rien, et personne ne peut le
savoir à sa place : une livraison de repas peut être un caprice ou le seul dîner possible
d'une semaine de garde. Un outil qui juge se trompe, et un outil de budget qui se trompe
en jugeant est un outil qu'on cesse d'ouvrir.

Ce qu'il fait à la place est plus utile et vérifiable : il rend visibles des totaux que
l'addition mentale rate. « Quinze commandes à 18 € font 270 € » est un fait ; « tu commandes
trop » est une opinion, et elle n'a pas sa place dans un calcul.

**Il ne nomme aucune marque.** Une liste de commerçants en dur — Deliveroo, Uber, et le
reste — serait fausse dès qu'on change de pays ou d'habitudes, et daterait l'application
plus sûrement qu'une couleur. Le regroupement se fait sur le LIBELLÉ tel que l'utilisateur
l'écrit, normalisé, ce qui attrape ses propres habitudes sans qu'on ait à les deviner.

**Aucun modèle de langage.** Le garde-fou nº 3 refuse toute dépendance LLM dans ce projet,
et rien ici n'en aurait besoin : ce sont des sommes, des tris et des seuils, tous
explicables en une phrase à qui demande pourquoi une ligne s'affiche.
"""

from __future__ import annotations

import unicodedata
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from enum import StrEnum
from typing import Final

from mycounts.domain.montants import Cents


@dataclass(frozen=True)
class DepenseCalcul:
    """Vue minimale d'une dépense pour les statistiques.

    Le montant est POSITIF ici, contrairement aux opérations : ce module ne calcule que
    des dépenses, et un signe qui ne varie jamais est un signe qui finit par être oublié
    dans une comparaison.
    """

    libelle: str
    montant: Cents
    categorie: str | None
    """`None` pour « sans catégorie ». Jamais masqué : c'est souvent le plus gros poste,
    et le cacher donnerait une répartition fausse."""


@dataclass(frozen=True)
class PosteDeDepense:
    categorie: str | None
    montant: Cents
    part: int
    """Pourcentage du total, tronqué. Sur le TOTAL des dépenses, jamais sur le plus gros
    poste — rapportées au plus gros, toutes les parts changeraient en supprimant celui-ci."""

    montant_precedent: Cents | None
    """Le même poste sur la période précédente, ou `None` s'il n'existait pas."""

    @property
    def variation(self) -> int | None:
        """Variation en pourcentage, ou `None` si la comparaison n'a pas de sens.

        `None` quand le poste n'existait pas avant : une dépense qui passe de 0 à 50 € n'a
        pas augmenté de « l'infini pour cent », elle est nouvelle. Afficher un pourcentage
        là où le mot juste est « nouveau » ferait passer un fait clair pour une aberration.
        """
        if self.montant_precedent is None or self.montant_precedent <= 0:
            return None
        return round(
            (int(self.montant) - int(self.montant_precedent)) * 100 / int(self.montant_precedent)
        )


class Motif(StrEnum):
    """Les constats que ce module sait faire. Chacun est chiffré et explicable."""

    GOUTTE_A_GOUTTE = "goutte_a_goutte"
    """Plusieurs petites dépenses au même endroit, dont le total surprend."""

    POSTE_EN_HAUSSE = "poste_en_hausse"
    """Une catégorie qui a nettement augmenté par rapport à la période précédente."""

    ABONNEMENTS = "abonnements"
    """Le coût ANNUEL des prélèvements récurrents, que les douzièmes rendent invisible."""


@dataclass(frozen=True)
class Constat:
    """Un fait chiffré, jamais un jugement.

    `sujet` est le libellé ou la catégorie concernée, `montant` la somme qui justifie le
    constat, et `detail` un nombre dont le sens dépend du motif — un compte d'occurrences
    pour le goutte-à-goutte, un pourcentage pour une hausse.
    """

    motif: Motif
    sujet: str
    montant: Cents
    detail: int


"""Seuils du goutte-à-goutte.

Choisis pour attraper ce que l'addition mentale rate, et RIEN d'autre. Trois occurrences
parce que deux est une coïncidence ; un total minimal parce qu'un constat sur 12 € ferait
du bruit et rien de plus. Ils sont ici, nommés, plutôt que dissimulés dans une condition :
c'est le genre de valeur qu'on veut relire et discuter.
"""
OCCURRENCES_MINIMALES: Final[int] = 3
TOTAL_MINIMAL: Final[Cents] = Cents(5_000)

"""Hausse à partir de laquelle un poste est signalé, et plancher qui évite le bruit.

30 % sur au moins 30 € : sans le plancher, passer de 4 € à 6 € produirait un « +50 % »
parfaitement exact et parfaitement inutile.
"""
HAUSSE_SIGNIFICATIVE: Final[int] = 30
HAUSSE_PLANCHER: Final[Cents] = Cents(3_000)


def normaliser_libelle(libelle: str) -> str:
    """Ramène un libellé à sa forme comparable : sans accents, sans casse, sans ponctuation.

    « Carrefour City », « CARREFOUR CITY » et « Carrefour-City » désignent le même endroit
    pour qui tient un budget. Sans cette normalisation, le goutte-à-goutte ne verrait que
    des dépenses isolées — c'est-à-dire précisément ce qu'il existe pour ne pas rater.

    Ce qu'elle ne fait PAS : rapprocher deux libellés DIFFÉRENTS. « Carrefour » et
    « Carrefour City » restent deux sujets. Une correspondance approximative ferait des
    regroupements que l'utilisateur n'a pas demandés et ne pourrait pas défaire.
    """
    sans_accent = "".join(
        lettre
        for lettre in unicodedata.normalize("NFD", libelle)
        if unicodedata.category(lettre) != "Mn"
    )
    return " ".join("".join(c if c.isalnum() else " " for c in sans_accent).lower().split())


def repartition(
    depenses: Iterable[DepenseCalcul],
    precedentes: Iterable[DepenseCalcul] = (),
) -> tuple[PosteDeDepense, ...]:
    """Les dépenses par catégorie, du plus gros poste au plus petit.

    TOUTES les catégories, y compris celles qui n'ont aucun plafond : l'accueil montre les
    budgets fixés, cette vue montre où l'argent va réellement. Et « sans catégorie » n'est
    jamais masqué — c'est souvent la plus grosse ligne, et la cacher donnerait une
    répartition fausse.
    """
    totaux: dict[str | None, int] = {}
    for depense in depenses:
        totaux[depense.categorie] = totaux.get(depense.categorie, 0) + int(depense.montant)

    avant: dict[str | None, int] = {}
    for depense in precedentes:
        avant[depense.categorie] = avant.get(depense.categorie, 0) + int(depense.montant)

    total = sum(totaux.values())
    postes = [
        PosteDeDepense(
            categorie=categorie,
            montant=Cents(montant),
            part=0 if total <= 0 else montant * 100 // total,
            montant_precedent=None if categorie not in avant else Cents(avant[categorie]),
        )
        for categorie, montant in totaux.items()
    ]
    # Le montant décroissant, puis le nom : à égalité, l'ordre d'un dictionnaire dépend de
    # l'ordre d'insertion, donc de l'ordre des lignes en base. Un classement qu'on ne peut
    # pas prévoir se relit différemment à chaque ouverture.
    return tuple(sorted(postes, key=lambda p: (-int(p.montant), p.categorie or "")))


def constats(
    depenses: Sequence[DepenseCalcul],
    postes: Sequence[PosteDeDepense] = (),
    cout_annuel_des_abonnements: Cents | None = None,
) -> tuple[Constat, ...]:
    """Les motifs repérés, du plus gros montant au plus petit.

    Aucun n'est un jugement : chacun est une somme que l'addition mentale rate, et chacun
    peut s'expliquer en une phrase à qui demande pourquoi il s'affiche.
    """
    trouves: list[Constat] = []

    # Goutte-à-goutte : plusieurs petites dépenses au même endroit.
    par_libelle: dict[str, list[DepenseCalcul]] = {}
    for depense in depenses:
        par_libelle.setdefault(normaliser_libelle(depense.libelle), []).append(depense)

    for lignes in par_libelle.values():
        total = Cents(sum(int(d.montant) for d in lignes))
        if len(lignes) >= OCCURRENCES_MINIMALES and total >= TOTAL_MINIMAL:
            trouves.append(
                Constat(
                    motif=Motif.GOUTTE_A_GOUTTE,
                    # Le libellé ORIGINAL du premier, pas sa forme normalisée : c'est
                    # celui que l'utilisateur reconnaîtra dans sa liste.
                    sujet=lignes[0].libelle,
                    montant=total,
                    detail=len(lignes),
                )
            )

    # Postes en hausse franche.
    for poste in postes:
        variation = poste.variation
        if (
            variation is not None
            and variation >= HAUSSE_SIGNIFICATIVE
            and poste.montant >= HAUSSE_PLANCHER
        ):
            trouves.append(
                Constat(
                    motif=Motif.POSTE_EN_HAUSSE,
                    sujet=poste.categorie or "Sans catégorie",
                    montant=poste.montant,
                    detail=variation,
                )
            )

    # Coût annuel des abonnements : douze fois trois euros ne se lit pas comme trente-six.
    if cout_annuel_des_abonnements is not None and cout_annuel_des_abonnements > 0:
        trouves.append(
            Constat(
                motif=Motif.ABONNEMENTS,
                sujet="Abonnements et prélèvements",
                montant=cout_annuel_des_abonnements,
                detail=0,
            )
        )

    return tuple(sorted(trouves, key=lambda c: (-int(c.montant), c.sujet)))
