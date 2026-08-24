"""Recommandation mensuelle déterministe pour les enveloppes d'épargne.

Cette couche transforme l'état métier des enveloppes en souhaits pondérés, puis délègue
uniquement la division exacte des centimes à :mod:`repartition_epargne`. Elle tient compte
de ce qui est déjà affecté : une enveloppe suffisamment couverte reçoit toujours zéro.

La formule V1 est volontairement lisible :

* une contribution mensuelle explicite est le rythme retenu ;
* sinon, un objectif daté reçoit le manque divisé par les mois civils restants, arrondi au
  centime supérieur ;
* sinon, une prévention configurée peut recevoir tout son manque ;
* le poids est ce rythme multiplié par l'importance (1 à 5) ;
* le montant proposé ne dépasse ni ce rythme mensuel ni le manque total.

Si les rythmes du mois sont inférieurs au montant choisi, le reste demeure non affecté.
Il reste bien dans l'épargne réelle et pourra être distribué après une nouvelle décision ;
inventer une allocation au-delà d'un rythme validé serait modifier le plan à la place de
l'utilisateur.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID

from mycounts.domain.enveloppes import mois_restants
from mycounts.domain.montants import Cents
from mycounts.domain.repartition_epargne import (
    Affectation,
    SouhaitAffectation,
    repartir_exactement,
)


class RecommandationInvalide(ValueError):
    """Une enveloppe ne porte pas les données nécessaires à une recommandation sûre."""


class TypeEnveloppe(StrEnum):
    PREVENTION = "prevention"
    OBJECTIF = "objectif"


class OrigineRythme(StrEnum):
    COUVERTE = "couverte"
    A_CONFIGURER = "a_configurer"
    CONTRIBUTION = "contribution"
    ECHEANCE = "echeance"
    PREVENTION = "prevention"


@dataclass(frozen=True)
class EnveloppePourRecommandation:
    enveloppe_id: UUID
    type: TypeEnveloppe
    solde: Cents
    importance: int
    """De 1 (faible) à 5 (essentielle)."""

    cible: Cents | None = None
    date_cible: dt.date | None = None
    contribution_mensuelle: Cents | None = None

    def __post_init__(self) -> None:
        if self.solde < 0:
            raise RecommandationInvalide("Le solde d'une enveloppe ne peut pas être négatif.")
        if not 1 <= self.importance <= 5:
            raise RecommandationInvalide("L'importance doit être comprise entre 1 et 5.")
        if self.cible is not None and self.cible <= 0:
            raise RecommandationInvalide("Une cible doit être strictement positive.")
        if self.contribution_mensuelle is not None and self.contribution_mensuelle < 0:
            raise RecommandationInvalide("La contribution mensuelle ne peut pas être négative.")
        if self.type is TypeEnveloppe.OBJECTIF and (self.cible is None or self.date_cible is None):
            raise RecommandationInvalide("Un objectif exige un montant et une date cible.")
        if self.type is TypeEnveloppe.PREVENTION and self.date_cible is not None:
            raise RecommandationInvalide("Une enveloppe de prévention ne porte pas d'échéance.")


@dataclass(frozen=True)
class SouhaitMensuel:
    enveloppe_id: UUID
    manque: Cents
    rythme: Cents
    poids: int
    rang_priorite: int
    origine: OrigineRythme

    @property
    def souhait_affectation(self) -> SouhaitAffectation:
        return SouhaitAffectation(
            enveloppe_id=self.enveloppe_id,
            poids=self.poids,
            rang_priorite=self.rang_priorite,
            maximum=self.rythme,
        )


def _mois_de_contribution(aujourd_hui: dt.date, date_cible: dt.date) -> int:
    """Nombre de mois civils restant avant l'échéance, au minimum un.

    Une cible dans le mois courant ou dépassée doit être financée maintenant : le minimum
    reste donc un. Cette règle réutilise l'auteur historique du calcul des échéances et
    n'invente aucune date de paie fixe.
    """

    return mois_restants(date_cible, aujourd_hui)


def _division_superieure(numerateur: int, denominateur: int) -> int:
    return -(-numerateur // denominateur)


def calculer_souhaits_mensuels(
    enveloppes: tuple[EnveloppePourRecommandation, ...],
    *,
    aujourd_hui: dt.date,
) -> tuple[SouhaitMensuel, ...]:
    """Produit les poids explicables, sans encore déplacer ni affecter un centime."""

    ids = [enveloppe.enveloppe_id for enveloppe in enveloppes]
    if len(ids) != len(set(ids)):
        raise RecommandationInvalide("Une enveloppe ne peut apparaître qu'une fois.")

    resultat: list[SouhaitMensuel] = []
    for enveloppe in enveloppes:
        if enveloppe.cible is None:
            manque = Cents(0)
            rythme = Cents(0)
            origine = OrigineRythme.A_CONFIGURER
        else:
            manque = Cents(max(0, int(enveloppe.cible) - int(enveloppe.solde)))
            if manque == 0:
                rythme = Cents(0)
                origine = OrigineRythme.COUVERTE
            elif enveloppe.contribution_mensuelle is not None:
                rythme = Cents(min(int(manque), int(enveloppe.contribution_mensuelle)))
                origine = OrigineRythme.CONTRIBUTION
            elif enveloppe.type is TypeEnveloppe.OBJECTIF:
                if enveloppe.date_cible is None:  # garanti par __post_init__, aide mypy
                    raise AssertionError("Un objectif validé possède toujours une date.")
                mois = _mois_de_contribution(aujourd_hui, enveloppe.date_cible)
                rythme = Cents(_division_superieure(int(manque), mois))
                origine = OrigineRythme.ECHEANCE
            else:
                rythme = manque
                origine = OrigineRythme.PREVENTION

        # Le rang sert uniquement aux centimes de reste. L'importance la plus forte doit
        # passer en premier ; l'UUID tranche ensuite dans repartir_exactement.
        rang_priorite = 5 - enveloppe.importance
        poids = int(rythme) * enveloppe.importance
        resultat.append(
            SouhaitMensuel(
                enveloppe_id=enveloppe.enveloppe_id,
                manque=manque,
                rythme=rythme,
                poids=poids,
                rang_priorite=rang_priorite,
                origine=origine,
            )
        )
    return tuple(sorted(resultat, key=lambda ligne: (ligne.rang_priorite, str(ligne.enveloppe_id))))


@dataclass(frozen=True)
class LigneRecommandation:
    enveloppe_id: UUID
    montant: Cents
    manque_avant: Cents
    rythme: Cents
    poids: int
    origine: OrigineRythme


@dataclass(frozen=True)
class RecommandationMensuelle:
    montant_choisi: Cents
    montant_affecte: Cents
    montant_non_affecte: Cents
    lignes: tuple[LigneRecommandation, ...]

    @property
    def total_explique(self) -> Cents:
        return Cents(int(self.montant_affecte) + int(self.montant_non_affecte))


def recommander_repartition_mensuelle(
    montant_choisi: Cents,
    enveloppes: tuple[EnveloppePourRecommandation, ...],
    *,
    aujourd_hui: dt.date,
) -> RecommandationMensuelle:
    """Propose la ventilation du mois et explique l'éventuel montant laissé libre."""

    if montant_choisi < 0:
        raise RecommandationInvalide("Le montant choisi doit être positif ou nul.")
    souhaits = calculer_souhaits_mensuels(enveloppes, aujourd_hui=aujourd_hui)
    affectable = min(int(montant_choisi), sum(int(souhait.rythme) for souhait in souhaits))
    if affectable == 0:
        affectations = tuple(Affectation(s.enveloppe_id, Cents(0)) for s in souhaits)
    else:
        affectations = repartir_exactement(
            Cents(affectable),
            [souhait.souhait_affectation for souhait in souhaits],
        )
    montants = {affectation.enveloppe_id: affectation.montant for affectation in affectations}
    lignes = tuple(
        LigneRecommandation(
            enveloppe_id=souhait.enveloppe_id,
            montant=montants[souhait.enveloppe_id],
            manque_avant=souhait.manque,
            rythme=souhait.rythme,
            poids=souhait.poids,
            origine=souhait.origine,
        )
        for souhait in souhaits
    )
    montant_affecte = Cents(sum(int(ligne.montant) for ligne in lignes))
    recommandation = RecommandationMensuelle(
        montant_choisi=montant_choisi,
        montant_affecte=montant_affecte,
        montant_non_affecte=Cents(int(montant_choisi) - int(montant_affecte)),
        lignes=lignes,
    )
    if recommandation.total_explique != montant_choisi:
        raise AssertionError("La recommandation doit expliquer chaque centime choisi.")
    return recommandation
