"""Matérialisation des échéances récurrentes.

Transforme les échéances arrivées à terme en opérations réelles, à l'état
`a_confirmer` : l'application sait qu'elles auraient dû passer, mais personne ne les a
encore constatées. Sans import bancaire, c'est la seule chose qui distingue « le
prélèvement était prévu » de « le prélèvement a eu lieu, au montant prévu ».

**Idempotence.** Le job est rejouable sans effet. La clé est explicite et portée par la
base : `UNIQUE (recurrence_id, date_operation)` (index partiel `uq_operation_par_echeance`).
Ce n'est pas un contrôle applicatif — une seconde exécution concurrente ne pourrait pas
insérer de doublon même si les deux passaient le test « existe déjà ».
"""

from __future__ import annotations

import datetime as dt
import uuid
from dataclasses import dataclass

from sqlalchemy.orm import Session

from mycounts.domain.agregats import EtatOperation
from mycounts.domain.calendrier import aujourd_hui
from mycounts.domain.recurrence import Cadence, echeances
from mycounts.repository import recurrences as depot


@dataclass(frozen=True)
class Bilan:
    """Ce qu'une exécution a produit. Les deux compteurs doivent varier en sens
    opposés d'une exécution à l'autre : la seconde passe ne crée rien et ignore tout."""

    creees: int
    deja_presentes: int

    @property
    def total_examinees(self) -> int:
        return self.creees + self.deja_presentes


def materialiser(
    session: Session, *, a_la_date: dt.date | None = None, foyer_id: uuid.UUID | None = None
) -> Bilan:
    """Crée les opérations `a_confirmer` pour toute échéance échue et absente.

    Seules les échéances **passées ou du jour** sont matérialisées : une échéance future
    reste une prévision. La matérialiser en avance ferait entrer dans le solde réel de
    l'argent qui n'est pas encore parti.
    """
    jour = a_la_date or aujourd_hui()
    creees = 0
    deja = 0

    for recurrence in depot.recurrences_actives(session, foyer_id=foyer_id):
        cadence = Cadence(unite=recurrence.unite, intervalle=recurrence.intervalle)
        existantes = depot.dates_deja_materialisees(session, recurrence_id=recurrence.id)

        for echue in echeances(
            recurrence.ancre, cadence, jusqu_a=jour, fin=recurrence.fin
        ):
            if echue in existantes:
                deja += 1
                continue
            creee = depot.materialiser_echeance(
                session,
                recurrence=recurrence,
                date_echeance=echue,
                etat=EtatOperation.A_CONFIRMER,
            )
            # `None` : une requête concurrente a inséré la même échéance entre notre
            # lecture des dates déjà traitées et notre insertion. Elle est présente, ce
            # qui est le résultat attendu — elle compte donc comme déjà là, pas comme
            # créée par nous, sinon le bilan annoncerait deux créations pour une ligne.
            if creee is None:
                deja += 1
            else:
                creees += 1

    session.commit()
    return Bilan(creees=creees, deja_presentes=deja)
