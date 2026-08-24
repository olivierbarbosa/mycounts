"""Cycles budgétaires persistables, ouverts explicitement par une paie validée.

Ce module ne cherche jamais une paie dans l'historique pour redécouper les périodes. Il
décrit la petite machine d'états qui sera persistée : une paie de référence ouvre un cycle
et ferme le précédent dans la même transaction. Les bornes d'un cycle clos sont ensuite
immuables ; une correction ne fait qu'incrémenter sa version d'audit.

Les intervalles sont semi-ouverts, ``[debut, fin_exclusive)``. La paie qui ouvre le cycle
suivant est donc l'événement de clôture du précédent sans appartenir aux deux cycles.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, replace
from enum import StrEnum
from uuid import UUID


class CycleInvalide(ValueError):
    """Une transition produirait un cycle incohérent ou réécrirait une borne close."""


class EtatCycle(StrEnum):
    OUVERT = "ouvert"
    CLOS = "clos"


@dataclass(frozen=True)
class CycleBudgetaire:
    """État complet qu'un repository peut persister sans refaire de calcul implicite."""

    identifiant: UUID
    espace_id: UUID
    operation_ouverture_id: UUID
    debut: dt.date
    etat: EtatCycle = EtatCycle.OUVERT
    operation_cloture_id: UUID | None = None
    fin_exclusive: dt.date | None = None
    version_correction: int = 0

    def __post_init__(self) -> None:
        if self.version_correction < 0:
            raise CycleInvalide("La version de correction ne peut pas être négative.")
        if self.etat is EtatCycle.OUVERT:
            if self.operation_cloture_id is not None or self.fin_exclusive is not None:
                raise CycleInvalide("Un cycle ouvert ne possède aucune clôture.")
            return
        if self.operation_cloture_id is None or self.fin_exclusive is None:
            raise CycleInvalide("Un cycle clos exige son opération et sa date de clôture.")
        if self.fin_exclusive <= self.debut:
            raise CycleInvalide("Un cycle doit durer au moins un jour civil.")

    def contient(self, jour: dt.date) -> bool:
        """Dit si une opération datée peut appartenir à cet intervalle."""

        return jour >= self.debut and (self.fin_exclusive is None or jour < self.fin_exclusive)


@dataclass(frozen=True)
class OuvertureDeCycle:
    """Les deux écritures atomiques à persister lors d'une nouvelle paie."""

    cycle_precedent: CycleBudgetaire | None
    nouveau_cycle: CycleBudgetaire


def ouvrir_cycle(
    *,
    identifiant: UUID,
    espace_id: UUID,
    operation_ouverture_id: UUID,
    date_paie: dt.date,
    cycle_ouvert: CycleBudgetaire | None,
) -> OuvertureDeCycle:
    """Ouvre un cycle et ferme l'éventuel cycle courant à la date réelle de la paie.

    La fonction ne déduit rien de la catégorie ou du libellé de l'opération : l'appel
    constitue la confirmation explicite ``ouvre_cycle``. Elle rend les deux états afin que
    le repository les écrive dans une seule transaction SQL.
    """

    precedent: CycleBudgetaire | None = None
    if cycle_ouvert is not None:
        if cycle_ouvert.etat is not EtatCycle.OUVERT:
            raise CycleInvalide("Seul un cycle ouvert peut être clôturé par une paie.")
        if cycle_ouvert.espace_id != espace_id:
            raise CycleInvalide("Deux espaces financiers ne partagent jamais un cycle.")
        if date_paie <= cycle_ouvert.debut:
            raise CycleInvalide("La paie suivante doit être postérieure au début du cycle.")
        if cycle_ouvert.identifiant == identifiant:
            raise CycleInvalide("Le nouveau cycle doit avoir un identifiant distinct.")
        if cycle_ouvert.operation_ouverture_id == operation_ouverture_id:
            raise CycleInvalide("Une même opération ne peut pas ouvrir deux cycles.")
        precedent = replace(
            cycle_ouvert,
            etat=EtatCycle.CLOS,
            operation_cloture_id=operation_ouverture_id,
            fin_exclusive=date_paie,
        )

    nouveau = CycleBudgetaire(
        identifiant=identifiant,
        espace_id=espace_id,
        operation_ouverture_id=operation_ouverture_id,
        debut=date_paie,
    )
    return OuvertureDeCycle(cycle_precedent=precedent, nouveau_cycle=nouveau)


@dataclass(frozen=True)
class CorrectionCycle:
    """Événement d'audit ; il autorise un recalcul, jamais un changement de bornes."""

    cycle_id: UUID
    ancienne_version: int
    nouvelle_version: int
    auteur_id: UUID
    motif: str
    cree_le: dt.datetime


@dataclass(frozen=True)
class CycleCorrige:
    cycle: CycleBudgetaire
    evenement: CorrectionCycle


def ouvrir_correction(
    cycle: CycleBudgetaire,
    *,
    auteur_id: UUID,
    motif: str,
    cree_le: dt.datetime,
) -> CycleCorrige:
    """Incrémente la version d'un cycle clos et produit son événement d'audit."""

    if cycle.etat is not EtatCycle.CLOS:
        raise CycleInvalide("Un cycle ouvert se modifie normalement, sans correction close.")
    motif_normalise = motif.strip()
    if not motif_normalise:
        raise CycleInvalide("Une correction de cycle doit être expliquée.")
    if cree_le.tzinfo is None or cree_le.utcoffset() is None:
        raise CycleInvalide("La date d'audit doit inclure son fuseau horaire.")

    nouvelle_version = cycle.version_correction + 1
    corrige = replace(cycle, version_correction=nouvelle_version)
    return CycleCorrige(
        cycle=corrige,
        evenement=CorrectionCycle(
            cycle_id=cycle.identifiant,
            ancienne_version=cycle.version_correction,
            nouvelle_version=nouvelle_version,
            auteur_id=auteur_id,
            motif=motif_normalise,
            cree_le=cree_le,
        ),
    )


def valider_rattachement(
    cycle: CycleBudgetaire,
    *,
    espace_id: UUID,
    date_operation: dt.date,
    version_correction: int | None = None,
) -> None:
    """Valide le ``cycle_id`` explicite d'une nouvelle opération.

    Un cycle clos exige la version de correction courante. Cette preuve explicite évite
    qu'un ajout rétroactif ordinaire modifie silencieusement un agrégat déjà clos.
    """

    if cycle.espace_id != espace_id:
        raise CycleInvalide("L'opération et son cycle doivent appartenir au même espace.")
    if not cycle.contient(date_operation):
        raise CycleInvalide("La date de l'opération est hors des bornes du cycle.")
    if cycle.etat is EtatCycle.CLOS and (
        cycle.version_correction == 0 or version_correction != cycle.version_correction
    ):
        raise CycleInvalide(
            "Modifier un cycle clos exige une correction ouverte à sa version courante."
        )
