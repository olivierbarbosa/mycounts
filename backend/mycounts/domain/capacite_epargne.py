"""Capacité d'épargne V1 : trois bornes déterministes et explicables.

Les dépenses variables observées et le budget restant décrivent deux estimations du même
train de vie ; elles ne sont donc jamais additionnées. La recommandation conserve la plus
protectrice, l'ambitieuse conserve la plus basse, et la prudente ajoute la marge de
variabilité calculée en amont. Charges fixes et dépenses exceptionnelles confirmées sont,
elles, des sorties distinctes et sont toujours déduites.

L'épargne déjà présente est conservée dans l'instantané pour rendre un plan reproductible,
mais ne gonfle jamais la capacité : celle-ci vient uniquement du quotidien projeté.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from enum import StrEnum
from typing import Final

from mycounts.domain.montants import Cents

VERSION_CALCUL: Final = "capacite-epargne-v1"


class CapaciteInvalide(ValueError):
    """Les entrées ne permettent pas un calcul financier cohérent."""


class ConfianceCapacite(StrEnum):
    FAIBLE = "faible"
    MOYENNE = "moyenne"
    HAUTE = "haute"


@dataclass(frozen=True)
class EntreesCapaciteEpargne:
    """Instantané persistable de toutes les entrées du calcul."""

    solde_actuel: Cents
    date_du_solde: dt.date
    prochaine_paie_estimee: dt.date
    revenus_avant_paie: Cents
    charges_recurrentes_avant_paie: Cents
    budget_variable_restant: Cents
    train_de_vie_habituel_restant: Cents
    depenses_exceptionnelles_confirmees: Cents
    solde_de_securite: Cents
    marge_de_prudence: Cents
    epargne_existante: Cents
    cycles_clos_observes: int

    def __post_init__(self) -> None:
        champs_positifs = {
            "revenus attendus": self.revenus_avant_paie,
            "charges récurrentes": self.charges_recurrentes_avant_paie,
            "budget restant": self.budget_variable_restant,
            "train de vie": self.train_de_vie_habituel_restant,
            "dépenses exceptionnelles": self.depenses_exceptionnelles_confirmees,
            "solde de sécurité": self.solde_de_securite,
            "marge de prudence": self.marge_de_prudence,
            "épargne existante": self.epargne_existante,
        }
        negatif = next((nom for nom, valeur in champs_positifs.items() if valeur < 0), None)
        if negatif is not None:
            raise CapaciteInvalide(f"{negatif.capitalize()} doit être positif ou nul.")
        if self.cycles_clos_observes < 0:
            raise CapaciteInvalide("Le nombre de cycles observés ne peut pas être négatif.")
        if self.prochaine_paie_estimee < self.date_du_solde:
            raise CapaciteInvalide("La prochaine paie ne peut pas précéder le solde observé.")


@dataclass(frozen=True)
class CapacitesEpargne:
    version_calcul: str
    prudente: Cents
    recommandee: Cents
    ambitieuse: Cents
    confiance: ConfianceCapacite


def _borne_train_de_vie(entrees: EntreesCapaciteEpargne) -> tuple[Cents, Cents]:
    budget = entrees.budget_variable_restant
    habitudes = entrees.train_de_vie_habituel_restant
    # Zéro signifie « mesure absente » quand l'autre source existe, pas « la personne ne
    # dépensera plus rien ». Avec une seule mesure, les deux scénarios la conservent.
    if budget == 0:
        return habitudes, habitudes
    if habitudes == 0:
        return budget, budget
    return Cents(min(int(budget), int(habitudes))), Cents(max(int(budget), int(habitudes)))


def _borner_a_zero(montant: int) -> Cents:
    return Cents(max(0, montant))


def _confiance(cycles_clos_observes: int) -> ConfianceCapacite:
    if cycles_clos_observes < 3:
        return ConfianceCapacite.FAIBLE
    if cycles_clos_observes < 6:
        return ConfianceCapacite.MOYENNE
    return ConfianceCapacite.HAUTE


def calculer_capacites(entrees: EntreesCapaciteEpargne) -> CapacitesEpargne:
    """Calcule prudent <= recommandé <= ambitieux, toujours en centimes et >= zéro."""

    train_bas, train_haut = _borne_train_de_vie(entrees)
    socle = (
        int(entrees.solde_actuel)
        + int(entrees.revenus_avant_paie)
        - int(entrees.charges_recurrentes_avant_paie)
        - int(entrees.depenses_exceptionnelles_confirmees)
        - int(entrees.solde_de_securite)
    )
    recommandee_brute = socle - int(train_haut)
    return CapacitesEpargne(
        version_calcul=VERSION_CALCUL,
        prudente=_borner_a_zero(recommandee_brute - int(entrees.marge_de_prudence)),
        recommandee=_borner_a_zero(recommandee_brute),
        ambitieuse=_borner_a_zero(socle - int(train_bas)),
        confiance=_confiance(entrees.cycles_clos_observes),
    )
